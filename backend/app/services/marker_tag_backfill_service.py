"""Backfill the tag system from historical ``entry_note_markers`` (#895).

Part of the #890 consolidation (Option 4 — one label system). After #893
removed the note-marker capture UI and migration 047 seeded ``achievement`` as
a curated default tag, existing markers still live only in
``entry_note_markers``. This one-off backfill converts them into tag links so
context lives in one place.

Why a service-layer backfill and not raw SQL
--------------------------------------------
An earlier raw-SQL Alembic draft (#899) reimplemented copy-on-write override
resolution, the per-entry tag cap, slug collisions and — critically — sync
revision logging by hand, and would have surfaced context from notes the user
explicitly hid. All of that is already handled correctly by the tag service
(:func:`assign_tags_to_entry`, :func:`create_custom_tag`), which also emits the
``sync_revision_log`` rows offline clients need. This module reuses those
tested paths instead of duplicating them in a migration.

What it does
------------
- **Predefined 1:1** markers (``conflict``, ``travel``, ``achievement``) link
  to the user's *visible* tag for that slug — their copy-on-write **override**
  if they have one, else the curated default. A hidden target is left alone.
- **Custom** markers (anything outside the predefined taxonomy) become per-user
  **custom tags** (category ``other``) via the tag service, then link. Slugs
  are derived to the strict tag-slug format; un-sluggable markers and any whose
  slug would shadow a curated default are skipped.
- **Generic / overlap** predefined markers (``work``, ``homeoffice``,
  ``social``, ``movement``, ``sleep_bad``, ``sleep_good``, ``stress``,
  ``symptom``) are intentionally **skipped** — they duplicate ``work_context``,
  the sliders, the SymptomChecker or whole tag *categories* (see #890 / #897).

Guarantees
----------
- **Hidden notes excluded.** Markers on ``note_visibility='hidden'`` entries are
  never converted (privacy: the user opted those notes out of display/analysis).
- **Assignment cap preserved.** An entry is never pushed past
  ``MAX_TAGS_PER_ENTRY``; excess markers are skipped and counted. A custom tag is
  created **only** when the entry has a free slot, so a marker seen only on
  already-full entries never leaves an orphan tag in the user's catalogue.
- **Idempotent & additive.** Re-runs are a no-op: existing links/tags are reused
  and :func:`assign_tags_to_entry` only writes (and only emits a revision) when
  the set actually changes. Source ``entry_note_markers`` rows are untouched.
- **Privacy-preserving logs.** Only counts and ``user_id`` are logged — never a
  marker's text or a tag slug/name (matching the tag service's log policy).

Slug collisions
---------------
Distinct markers that normalise to the same slug for one user deterministically
merge onto a single tag: markers are processed in sorted order and the first
occurrence wins the tag. This is by design (one label system) and stable across
runs.

Transactions
-----------
Enumeration covers **every** user that still has markers (regardless of active
state — account disabling is reversible). With ``commit_per_user=True`` (the
real run) each user is committed before the next is processed, so a
production-sized backfill never holds one user's ``sync_user_revisions`` lock
for the whole run, and a mid-user failure (e.g. a concurrent slug insert that
makes ``create_custom_tag`` roll back) is isolated: that user is rolled back and
skipped — re-running the idempotent backfill picks them up — while already
committed users stay converted. ``commit_per_user=False`` keeps a single
transaction the caller can roll back, for ``--dry-run``.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import bind_rls_current_user
from app.models.entry import Entry, NoteVisibility
from app.models.entry_note import EntryNoteMarker
from app.models.tag import Tag, TagCategory
from app.schemas.note import PREDEFINED_NOTE_MARKERS
from app.schemas.tag import MAX_TAGS_PER_ENTRY, TagCreate
from app.services.tag_service import (
    TagError,
    assign_tags_to_entry,
    create_custom_tag,
    list_tags_for_entry,
)

logger = logging.getLogger(__name__)

# Predefined markers with an unambiguous 1:1 curated default-tag target. Every
# other predefined key is dominated by a dedicated field/category and skipped.
_PREDEFINED_TAG_MAP: dict[str, str] = {
    "conflict": "conflict",
    "travel": "travel",
    "achievement": "achievement",
}

# Runs of characters outside the tag-slug alphabet collapse to a single dash.
_SLUG_INVALID = re.compile(r"[^a-z0-9]+")


def derive_custom_tag_slug(marker: str) -> str | None:
    """Derive a valid tag slug from a note marker, or ``None`` if impossible.

    Tag slugs are lowercase letters/digits/dashes/underscores, 2..64 chars, with
    no leading/trailing or repeated separators (schemas/tag.py). Note markers are
    already lowercased/whitespace-collapsed but may hold spaces or punctuation and
    can be a single character. Non-``[a-z0-9]`` runs collapse to one dash;
    truncation to 64 never leaves a trailing dash; returns ``None`` when fewer
    than 2 usable characters remain.
    """
    slug = _SLUG_INVALID.sub("-", marker.lower()).strip("-")
    if len(slug) > 64:
        slug = slug[:64].rstrip("-")
    if len(slug) < 2:
        return None
    return slug


@dataclass
class MarkerTagBackfillSummary:
    """Counters describing one backfill run."""

    users_processed: int = 0
    users_failed: int = 0
    entries_updated: int = 0
    predefined_links_added: int = 0
    custom_tags_created: int = 0
    custom_links_added: int = 0
    skipped_unsluggable: int = 0
    skipped_default_clash: int = 0
    skipped_hidden_target: int = 0
    skipped_over_cap: int = 0
    user_ids: list[uuid.UUID] = field(default_factory=list)

    def merge(self, other: MarkerTagBackfillSummary) -> None:
        """Fold a per-user summary into the run total (called after commit)."""
        self.users_processed += other.users_processed
        self.entries_updated += other.entries_updated
        self.predefined_links_added += other.predefined_links_added
        self.custom_tags_created += other.custom_tags_created
        self.custom_links_added += other.custom_links_added
        self.skipped_unsluggable += other.skipped_unsluggable
        self.skipped_default_clash += other.skipped_default_clash
        self.skipped_hidden_target += other.skipped_hidden_target
        self.skipped_over_cap += other.skipped_over_cap
        self.user_ids.extend(other.user_ids)


async def _list_backfill_user_ids(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
) -> list[uuid.UUID]:
    """Every user with retained markers (or just ``user_id`` when given).

    Enumerated from ``entry_note_markers`` rather than the user table: it skips
    users with nothing to convert, and includes reversibly disabled accounts
    (``is_active=false``) whose markers must still be converted in case they are
    re-enabled after this run-once operation.
    """
    if user_id is not None:
        return [user_id]
    result = await db.execute(select(EntryNoteMarker.user_id).distinct())
    return list(result.scalars().all())


async def _resolve_predefined_tag_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    slug: str,
) -> uuid.UUID | None:
    """Resolve the user's visible tag for a curated slug.

    Prefer the user's copy-on-write override over the curated default so
    historical markers land on the same row the user already sees and edits.
    A hidden target (default or override) returns ``None`` — the user opted out
    of that tag, and :func:`assign_tags_to_entry` would reject a hidden id anyway.
    """
    override = (
        await db.execute(
            select(Tag).where(
                Tag.user_id == user_id,
                Tag.slug == slug,
                Tag.is_default.is_(False),
            )
        )
    ).scalar_one_or_none()
    tag = override
    if tag is None:
        tag = (
            await db.execute(select(Tag).where(Tag.is_default.is_(True), Tag.slug == slug))
        ).scalar_one_or_none()
    if tag is None or tag.is_hidden:
        return None
    return tag.id


async def _resolve_existing_custom_tag(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    marker: str,
    slug_cache: dict[str, uuid.UUID],
    skip_slugs: set[str],
    summary: MarkerTagBackfillSummary,
) -> tuple[str, uuid.UUID | None, str | None]:
    """Classify a custom marker **without writing**.

    Returns one of:
    - ``("ok", tag_id, slug)`` — reuse the user's existing tag;
    - ``("needs_create", None, slug)`` — no tag yet, creation would be required
      (the caller decides based on remaining entry capacity so a full entry
      never spawns an orphan tag);
    - ``("skip", None, None)`` — un-sluggable, default-slug clash, or hidden own
      tag (counted on ``summary``; the slug is remembered so re-lookups are cheap
      and consistent).
    """
    slug = derive_custom_tag_slug(marker)
    if slug is None:
        summary.skipped_unsluggable += 1
        return ("skip", None, None)
    if slug in slug_cache:
        return ("ok", slug_cache[slug], slug)
    if slug in skip_slugs:
        return ("skip", None, None)

    own = (
        await db.execute(
            select(Tag).where(
                Tag.user_id == user_id,
                Tag.slug == slug,
                Tag.is_default.is_(False),
            )
        )
    ).scalar_one_or_none()
    if own is not None:
        if own.is_hidden:
            # The user hid this tag — leave it out of new assignments.
            summary.skipped_hidden_target += 1
            skip_slugs.add(slug)
            return ("skip", None, None)
        slug_cache[slug] = own.id
        return ("ok", own.id, slug)

    # No own tag yet — a custom tag must not shadow a curated default slug
    # (mirrors create_custom_tag, which forbids such customs).
    clashes_default = (
        await db.execute(select(Tag.id).where(Tag.is_default.is_(True), Tag.slug == slug))
    ).scalar_one_or_none()
    if clashes_default is not None:
        summary.skipped_default_clash += 1
        skip_slugs.add(slug)
        return ("skip", None, None)

    return ("needs_create", None, slug)


async def _create_custom_tag_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    marker: str,
    slug: str,
    slug_cache: dict[str, uuid.UUID],
    summary: MarkerTagBackfillSummary,
) -> uuid.UUID | None:
    """Create a custom tag for ``slug`` via the tag service; cache and count it.

    A :class:`TagConflictError` (concurrent same-slug insert) is **not** swallowed
    — ``create_custom_tag`` rolls the transaction back on the unique violation, so
    the current user is aborted and skipped by the caller rather than continuing
    on a rolled-back session with counters that describe lost writes.
    """
    try:
        payload = TagCreate(slug=slug, name=marker[:64], category=TagCategory.OTHER)
    except ValidationError:
        summary.skipped_unsluggable += 1
        return None
    created = await create_custom_tag(db, user_id=user_id, payload=payload)
    summary.custom_tags_created += 1
    slug_cache[slug] = created.id
    return created.id


async def _backfill_marker_tags_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> MarkerTagBackfillSummary:
    """Convert one user's markers; returns that user's counters."""
    summary = MarkerTagBackfillSummary()
    await bind_rls_current_user(db, user_id=user_id)

    # Markers on hidden-note entries are excluded: the user opted those notes
    # out of display/analysis, so their context must not become ordinary tags.
    rows = (
        await db.execute(
            select(EntryNoteMarker.entry_id, EntryNoteMarker.marker)
            .join(Entry, Entry.id == EntryNoteMarker.entry_id)
            .where(
                EntryNoteMarker.user_id == user_id,
                Entry.note_visibility != NoteVisibility.HIDDEN.value,
            )
        )
    ).all()
    if not rows:
        return summary

    markers_by_entry: dict[uuid.UUID, set[str]] = {}
    for entry_id, marker in rows:
        markers_by_entry.setdefault(entry_id, set()).add(marker)

    slug_cache: dict[str, uuid.UUID] = {}
    skip_slugs: set[str] = set()
    touched = False

    # Deterministic ordering keeps slug-collision merges and cap trimming stable.
    for entry_id in sorted(markers_by_entry, key=str):
        current = await list_tags_for_entry(db, user_id=user_id, entry_id=entry_id)
        current_ids = {tag.id for tag in current}
        final_ids = set(current_ids)
        added_predefined = 0
        added_custom = 0

        for marker in sorted(markers_by_entry[entry_id]):
            at_cap = len(final_ids) >= MAX_TAGS_PER_ENTRY

            if marker in _PREDEFINED_TAG_MAP:
                tag_id = await _resolve_predefined_tag_id(
                    db, user_id=user_id, slug=_PREDEFINED_TAG_MAP[marker]
                )
                if tag_id is None:
                    summary.skipped_hidden_target += 1
                    continue
                if tag_id in final_ids:
                    continue
                if at_cap:
                    summary.skipped_over_cap += 1
                    continue
                final_ids.add(tag_id)
                added_predefined += 1
                continue

            if marker in PREDEFINED_NOTE_MARKERS:
                # Generic/overlap predefined markers are intentionally skipped.
                continue

            status, tag_id, slug = await _resolve_existing_custom_tag(
                db,
                user_id=user_id,
                marker=marker,
                slug_cache=slug_cache,
                skip_slugs=skip_slugs,
                summary=summary,
            )
            if status == "skip":
                continue
            if status == "ok":
                assert tag_id is not None
                if tag_id in final_ids:
                    continue
                if at_cap:
                    summary.skipped_over_cap += 1
                    continue
                final_ids.add(tag_id)
                added_custom += 1
                continue

            # needs_create: only spend a slot — and create the tag — when the
            # entry has room, so a marker seen only on full entries never leaves
            # an orphan tag behind.
            if at_cap:
                summary.skipped_over_cap += 1
                continue
            assert slug is not None
            created_id = await _create_custom_tag_id(
                db,
                user_id=user_id,
                marker=marker,
                slug=slug,
                slug_cache=slug_cache,
                summary=summary,
            )
            if created_id is None:
                continue
            final_ids.add(created_id)
            added_custom += 1

        if final_ids == current_ids:
            continue

        # Reuse the tested assignment path: it validates visibility, honours
        # overrides and emits the entry sync revision offline clients need.
        await assign_tags_to_entry(
            db,
            user_id=user_id,
            entry_id=entry_id,
            tag_ids=list(final_ids),
            record_revision=True,
        )
        summary.entries_updated += 1
        summary.predefined_links_added += added_predefined
        summary.custom_links_added += added_custom
        touched = True

    if touched:
        summary.users_processed = 1
        summary.user_ids.append(user_id)
    return summary


async def backfill_marker_tags(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    commit_per_user: bool = False,
) -> MarkerTagBackfillSummary:
    """Convert historical note markers into tag links via the service layer.

    Iterates every user with retained markers (or just ``user_id``), binding RLS
    per user so the production ``correlcore_app`` role sees rows under FORCE RLS.

    With ``commit_per_user=True`` each user is committed before the next, bounding
    lock hold time and the blast radius of a failed user (rolled back and skipped;
    a re-run picks them up). With ``commit_per_user=False`` (``--dry-run``) nothing
    is committed and the caller owns the single transaction.
    """
    summary = MarkerTagBackfillSummary()
    for current_user_id in await _list_backfill_user_ids(db, user_id=user_id):
        try:
            user_summary = await _backfill_marker_tags_for_user(db, user_id=current_user_id)
            if commit_per_user:
                await db.commit()
        except (SQLAlchemyError, TagError):
            await db.rollback()
            summary.users_failed += 1
            logger.warning(
                "marker_tag_backfill.user_failed",
                extra={"user_id": str(current_user_id)},
            )
            continue
        summary.merge(user_summary)
    return summary

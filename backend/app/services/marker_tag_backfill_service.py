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
  ``MAX_TAGS_PER_ENTRY``; excess markers are skipped and counted so the entry
  form can still round-trip its tag set.
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

The backfill does not commit — the caller (``scripts/backfill_marker_tags.py``)
owns the transaction so a dry-run can roll back.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import bind_rls_current_user
from app.models.entry import Entry, NoteVisibility
from app.models.entry_note import EntryNoteMarker
from app.models.tag import Tag, TagCategory
from app.models.user import User
from app.schemas.note import PREDEFINED_NOTE_MARKERS
from app.schemas.tag import MAX_TAGS_PER_ENTRY, TagCreate
from app.services.tag_service import (
    TagConflictError,
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
    entries_updated: int = 0
    predefined_links_added: int = 0
    custom_tags_created: int = 0
    custom_links_added: int = 0
    skipped_unsluggable: int = 0
    skipped_default_clash: int = 0
    skipped_hidden_target: int = 0
    skipped_over_cap: int = 0
    user_ids: list[uuid.UUID] = field(default_factory=list)


async def _list_backfill_user_ids(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
) -> list[uuid.UUID]:
    if user_id is not None:
        return [user_id]
    result = await db.execute(
        select(User.id).where(User.is_active.is_(True), User.is_verified.is_(True))
    )
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


async def _resolve_or_create_custom_tag_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    marker: str,
    slug_cache: dict[str, uuid.UUID | None],
    summary: MarkerTagBackfillSummary,
) -> uuid.UUID | None:
    """Return the tag id for a custom marker, creating a custom tag if needed.

    Reuses the user's own tag with the derived slug; otherwise creates one via
    the tag service (which records a tag revision). Returns ``None`` when the
    marker is un-sluggable or its slug would shadow a curated default — both
    tracked on ``summary``. Never logs the marker text or slug.
    """
    slug = derive_custom_tag_slug(marker)
    if slug is None:
        summary.skipped_unsluggable += 1
        return None

    if slug in slug_cache:
        return slug_cache[slug]

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
        # A tag the user later hid is left out of new assignments (respect the
        # opt-out); it stays cached as None so we skip it consistently.
        tag_id = None if own.is_hidden else own.id
        if own.is_hidden:
            summary.skipped_hidden_target += 1
        slug_cache[slug] = tag_id
        return tag_id

    # No own tag yet — a custom tag must not shadow a curated default slug
    # (mirrors create_custom_tag, which forbids such customs).
    clashes_default = (
        await db.execute(select(Tag.id).where(Tag.is_default.is_(True), Tag.slug == slug))
    ).scalar_one_or_none()
    if clashes_default is not None:
        summary.skipped_default_clash += 1
        slug_cache[slug] = None
        return None

    try:
        payload = TagCreate(slug=slug, name=marker[:64], category=TagCategory.OTHER)
    except ValidationError:
        summary.skipped_unsluggable += 1
        slug_cache[slug] = None
        return None

    try:
        created = await create_custom_tag(db, user_id=user_id, payload=payload)
    except TagConflictError:
        # Race or a slug we did not classify as a default clash — re-resolve the
        # user's own tag rather than fabricating a duplicate.
        existing = (
            await db.execute(
                select(Tag).where(
                    Tag.user_id == user_id,
                    Tag.slug == slug,
                    Tag.is_default.is_(False),
                )
            )
        ).scalar_one_or_none()
        tag_id = existing.id if existing is not None and not existing.is_hidden else None
        slug_cache[slug] = tag_id
        return tag_id

    summary.custom_tags_created += 1
    slug_cache[slug] = created.id
    return created.id


async def _backfill_marker_tags_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    summary: MarkerTagBackfillSummary,
) -> None:
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
        return

    # Group markers per entry; deterministic ordering keeps slug-collision
    # merges and cap trimming stable across runs.
    markers_by_entry: dict[uuid.UUID, set[str]] = {}
    for entry_id, marker in rows:
        markers_by_entry.setdefault(entry_id, set()).add(marker)

    slug_cache: dict[str, uuid.UUID | None] = {}
    touched_user = False

    for entry_id in sorted(markers_by_entry, key=str):
        # tag id -> "predefined" | "custom" (dedups markers that resolve alike).
        desired: dict[uuid.UUID, str] = {}
        for marker in sorted(markers_by_entry[entry_id]):
            if marker in _PREDEFINED_TAG_MAP:
                tag_id = await _resolve_predefined_tag_id(
                    db, user_id=user_id, slug=_PREDEFINED_TAG_MAP[marker]
                )
                if tag_id is None:
                    summary.skipped_hidden_target += 1
                    continue
                desired.setdefault(tag_id, "predefined")
            elif marker in PREDEFINED_NOTE_MARKERS:
                # Generic/overlap predefined markers are intentionally skipped.
                continue
            else:
                tag_id = await _resolve_or_create_custom_tag_id(
                    db,
                    user_id=user_id,
                    marker=marker,
                    slug_cache=slug_cache,
                    summary=summary,
                )
                if tag_id is None:
                    continue
                desired.setdefault(tag_id, "custom")

        if not desired:
            continue

        current = await list_tags_for_entry(db, user_id=user_id, entry_id=entry_id)
        current_ids = {tag.id for tag in current}

        # Preserve the assignment cap: keep every current tag, then add new ones
        # deterministically until the entry hits MAX_TAGS_PER_ENTRY.
        final_ids = set(current_ids)
        added_predefined = 0
        added_custom = 0
        for tag_id in sorted(desired, key=str):
            if tag_id in final_ids:
                continue
            if len(final_ids) >= MAX_TAGS_PER_ENTRY:
                summary.skipped_over_cap += 1
                continue
            final_ids.add(tag_id)
            if desired[tag_id] == "predefined":
                added_predefined += 1
            else:
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
        touched_user = True

    if touched_user:
        summary.users_processed += 1
        summary.user_ids.append(user_id)
        logger.info(
            "marker_tag_backfill.user_done",
            extra={"user_id": str(user_id)},
        )


async def backfill_marker_tags(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
) -> MarkerTagBackfillSummary:
    """Convert historical note markers into tag links via the service layer.

    When ``user_id`` is omitted, iterates active verified users and binds RLS
    per user so the production ``correlcore_app`` role sees rows under FORCE RLS.
    Does not commit — the caller owns the transaction (enables ``--dry-run``).
    """
    summary = MarkerTagBackfillSummary()
    for current_user_id in await _list_backfill_user_ids(db, user_id=user_id):
        await _backfill_marker_tags_for_user(db, user_id=current_user_id, summary=summary)
    return summary

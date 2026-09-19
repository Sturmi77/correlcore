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
explicitly hid. This module reuses the tested tag service instead:
``create_custom_tag`` for tag creation (and its ``sync_revision_log`` entry),
and ``record_entry_upsert_revision`` for the entry revision offline clients need.

What it does
------------
- **Predefined 1:1** markers (``conflict``, ``travel``, ``achievement``) link
  to the user's *visible* tag for that slug — their copy-on-write **override**
  if they have one, else the curated default. A hidden target is left alone.
- **Custom** markers (anything outside the predefined taxonomy) become per-user
  **custom tags** (category ``other``), then link.
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
- **Add-only, never destructive.** Links are inserted with ``ON CONFLICT DO
  NOTHING``; the backfill never rewrites an entry's tag set, so it cannot
  overwrite a tag a user removed concurrently (the replace-set race a
  ``PUT /entries/{id}/tags`` style path would expose). It only ever *adds* the
  marker-derived links that are missing.
- **Idempotent.** Re-runs are a no-op: existing links are skipped, existing tags
  reused, and per-marker slug assignment is deterministic across runs. Source
  ``entry_note_markers`` rows are untouched.
- **Privacy-preserving logs.** Only counts and ``user_id`` are logged — never a
  marker's text or a tag slug/name (matching the tag service's log policy).

Slug collisions
---------------
Distinct markers that normalise to the same base slug for one user get
**distinct, deterministic** slugs rather than being merged: markers are
resolved in sorted order, the first keeps the base slug and each later collider
gets a ``-2``/``-3`` suffix (never shadowing a curated default). The order is
stable and the source markers are frozen, so a re-run reproduces the same
assignment and reuses the tags created before.

Transactions
-----------
Enumeration covers **every** user that still has markers (regardless of active
state — account disabling is reversible). With ``commit_per_user=True`` (the
real run) each user is committed before the next, so a production-sized backfill
never holds one user's ``sync_user_revisions`` lock for the whole run, and a
mid-user failure (e.g. a concurrent slug insert that makes ``create_custom_tag``
roll back) is isolated: that user is rolled back and skipped — re-running the
idempotent backfill picks them up — while already committed users stay
converted. ``commit_per_user=False`` keeps a single transaction the caller can
roll back, for ``--dry-run``.

DEK
---
``list_tags_for_entry`` and ``record_entry_upsert_revision`` load the full
``Entry`` ORM row, and ``EncryptedString`` decrypts ``note_enc`` on load. The
CLI has no request-scoped DEK, so a real note (the expected case for markers)
would raise ``DekUnavailableError`` and abort the run. Bind the user's wrapped
DEK for the duration of their conversion, matching ``lag_profile_backfill``.
"""

from __future__ import annotations

import contextvars
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.core.crypto import (
    CryptoError,
    reset_current_user_dek,
    set_current_user_dek,
    unwrap_dek,
)
from app.db.session import bind_rls_current_user
from app.models.entry import Entry, NoteVisibility
from app.models.entry_note import EntryNoteMarker
from app.models.tag import EntryTag, Tag, TagCategory
from app.models.user_encryption_key import UserEncryptionKey
from app.schemas.tag import MAX_TAGS_PER_ENTRY, TagCreate
from app.services.tag_service import TagError, create_custom_tag, list_tags_for_entry

logger = logging.getLogger(__name__)

# Former note-marker taxonomy (API removed in #903 C). Kept here so the
# one-off backfill can classify predefined vs custom markers.
PREDEFINED_NOTE_MARKERS: frozenset[str] = frozenset(
    {
        "work",
        "homeoffice",
        "social",
        "movement",
        "sleep_bad",
        "sleep_good",
        "stress",
        "conflict",
        "symptom",
        "travel",
        "achievement",
    }
)
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
    """Derive a valid base tag slug from a note marker, or ``None`` if impossible.

    Tag slugs are lowercase letters/digits/dashes/underscores, 2..64 chars, with
    no leading/trailing or repeated separators (schemas/tag.py). Note markers are
    already lowercased/whitespace-collapsed but may hold spaces or punctuation and
    can be a single character. Non-``[a-z0-9]`` runs collapse to one dash;
    truncation to 64 never leaves a trailing dash; returns ``None`` when fewer
    than 2 usable characters remain. Disambiguation suffixes are added later by
    :func:`_disambiguated_slug`.
    """
    slug = _SLUG_INVALID.sub("-", marker.lower()).strip("-")
    if len(slug) > 64:
        slug = slug[:64].rstrip("-")
    if len(slug) < 2:
        return None
    return slug


def _disambiguated_slug(
    base: str,
    *,
    marker: str,
    default_slugs: set[str],
    claimed_slugs: dict[str, str],
) -> str:
    """Return a unique slug for ``marker``, registering it in ``claimed_slugs``.

    The first marker to reach a base slug keeps it; later distinct markers that
    derive the same base get ``-2``, ``-3``, … A candidate that would shadow a
    curated default is skipped too. Deterministic given the marker processing
    order, so re-runs reproduce the assignment.
    """
    n = 1
    while True:
        if n == 1:
            candidate = base
        else:
            candidate = f"{base[:61].rstrip('-')}-{n}"
        owner = claimed_slugs.get(candidate)
        if len(candidate) < 2 or candidate in default_slugs or (owner not in (None, marker)):
            n += 1
            continue
        claimed_slugs[candidate] = marker
        return candidate


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


async def _default_slugs(db: AsyncSession) -> set[str]:
    result = await db.execute(select(Tag.slug).where(Tag.is_default.is_(True)))
    return set(result.scalars().all())


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
    of that tag.
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


# Per-marker resolution decision, memoised for a user across all their entries.
# ("skip", None) — un-sluggable or hidden own tag.
# ("existing", tag_id) — reuse this tag id.
# ("create", None) — no tag yet; create at ``slug`` when an entry has capacity.
_Decision = tuple[str, uuid.UUID | None]


async def _resolve_custom_marker(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    marker: str,
    default_slugs: set[str],
    claimed_slugs: dict[str, str],
    marker_slug: dict[str, str],
    summary: MarkerTagBackfillSummary,
) -> tuple[_Decision, str | None]:
    """Classify a custom marker **without writing**; returns (decision, slug).

    Assigns the marker a stable, disambiguated slug and reports whether an
    existing tag can be reused or a new one must be created (deferred to the
    caller so a full entry never triggers creation).
    """
    base = derive_custom_tag_slug(marker)
    if base is None:
        summary.skipped_unsluggable += 1
        return (("skip", None), None)

    slug = marker_slug.get(marker)
    if slug is None:
        slug = _disambiguated_slug(
            base, marker=marker, default_slugs=default_slugs, claimed_slugs=claimed_slugs
        )
        marker_slug[marker] = slug

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
            summary.skipped_hidden_target += 1
            return (("skip", None), slug)
        return (("existing", own.id), slug)
    return (("create", None), slug)


async def _create_custom_tag_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    marker: str,
    slug: str,
    summary: MarkerTagBackfillSummary,
) -> uuid.UUID | None:
    """Create a custom tag at ``slug`` via the tag service; count it.

    ``slug`` is already disambiguated away from curated defaults, so
    ``create_custom_tag`` will not reject it as a default clash. A
    :class:`TagError` (e.g. a concurrent same-slug insert, after which
    ``create_custom_tag`` has rolled the session back) is **not** swallowed — it
    propagates so the current user is rolled back and skipped rather than
    continuing on a rolled-back session with counters describing lost writes.
    """
    try:
        payload = TagCreate(slug=slug, name=marker[:64], category=TagCategory.OTHER)
    except ValidationError:
        summary.skipped_unsluggable += 1
        return None
    created = await create_custom_tag(db, user_id=user_id, payload=payload)
    summary.custom_tags_created += 1
    return created.id


async def _link_additively(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    tag_ids: list[uuid.UUID],
) -> int:
    """Insert missing ``entry_tags`` links only; returns the number inserted.

    ``ON CONFLICT DO NOTHING`` makes this add-only and idempotent: it never
    deletes or overwrites, so it cannot clobber a tag set a user edits
    concurrently.
    """
    stmt = (
        pg_insert(EntryTag)
        .values([{"entry_id": entry_id, "tag_id": tid, "user_id": user_id} for tid in tag_ids])
        .on_conflict_do_nothing(index_elements=["entry_id", "tag_id"])
    )
    result = await db.execute(stmt)
    return int(getattr(result, "rowcount", 0) or 0)


async def _bind_user_dek(
    db: AsyncSession, *, user_id: uuid.UUID
) -> contextvars.Token[tuple[uuid.UUID, bytes] | None] | None:
    """Unwrap and bind the user's DEK so ``Entry.note_enc`` can be loaded.

    Returns the contextvar token for :func:`reset_current_user_dek`, or ``None``
    when the user has no key row (legacy / test fixtures whose entries have
    ``note_enc IS NULL`` and therefore never hit ``EncryptedString``).
    """
    key_result = await db.execute(
        select(UserEncryptionKey.wrapped_dek).where(UserEncryptionKey.user_id == user_id)
    )
    wrapped_dek = key_result.scalar_one_or_none()
    if wrapped_dek is None:
        return None
    return set_current_user_dek(user_id, unwrap_dek(wrapped_dek))


async def _backfill_marker_tags_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> MarkerTagBackfillSummary:
    """Convert one user's markers; returns that user's counters."""
    summary = MarkerTagBackfillSummary()
    await bind_rls_current_user(db, user_id=user_id)
    dek_token = await _bind_user_dek(db, user_id=user_id)
    try:
        return await _convert_marker_tags_for_user(db, user_id=user_id, summary=summary)
    finally:
        if dek_token is not None:
            reset_current_user_dek(dek_token)


async def _convert_marker_tags_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    summary: MarkerTagBackfillSummary,
) -> MarkerTagBackfillSummary:
    """Convert one already-bound user's markers (RLS + DEK set by caller)."""
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

    default_slugs = await _default_slugs(db)
    claimed_slugs: dict[str, str] = {}  # slug -> owning marker (disambiguation)
    marker_slug: dict[str, str] = {}  # marker -> its assigned slug
    marker_decision: dict[str, _Decision] = {}  # memoised per-marker resolution
    touched = False

    # Deterministic ordering keeps slug disambiguation and cap trimming stable.
    for entry_id in sorted(markers_by_entry, key=str):
        current = await list_tags_for_entry(db, user_id=user_id, entry_id=entry_id)
        planned: set[uuid.UUID] = {tag.id for tag in current}
        to_add: list[uuid.UUID] = []
        added_predefined = 0
        added_custom = 0

        for marker in sorted(markers_by_entry[entry_id]):
            at_cap = len(planned) >= MAX_TAGS_PER_ENTRY

            if marker in _PREDEFINED_TAG_MAP:
                tag_id = await _resolve_predefined_tag_id(
                    db, user_id=user_id, slug=_PREDEFINED_TAG_MAP[marker]
                )
                if tag_id is None:
                    summary.skipped_hidden_target += 1
                    continue
                if tag_id in planned:
                    continue
                if at_cap:
                    summary.skipped_over_cap += 1
                    continue
                planned.add(tag_id)
                to_add.append(tag_id)
                added_predefined += 1
                continue

            if marker in PREDEFINED_NOTE_MARKERS:
                # Generic/overlap predefined markers are intentionally skipped.
                continue

            decision = marker_decision.get(marker)
            if decision is None:
                decision, _slug = await _resolve_custom_marker(
                    db,
                    user_id=user_id,
                    marker=marker,
                    default_slugs=default_slugs,
                    claimed_slugs=claimed_slugs,
                    marker_slug=marker_slug,
                    summary=summary,
                )
                # "create" is provisional — only memoise stable outcomes now.
                if decision[0] != "create":
                    marker_decision[marker] = decision

            kind, tag_id = decision
            if kind == "skip":
                continue
            if kind == "existing":
                assert tag_id is not None
                if tag_id in planned:
                    continue
                if at_cap:
                    summary.skipped_over_cap += 1
                    continue
                planned.add(tag_id)
                to_add.append(tag_id)
                added_custom += 1
                continue

            # kind == "create": only create when the entry has a free slot, so a
            # marker seen only on full entries never leaves an orphan tag.
            if at_cap:
                summary.skipped_over_cap += 1
                continue
            created_id = await _create_custom_tag_id(
                db, user_id=user_id, marker=marker, slug=marker_slug[marker], summary=summary
            )
            if created_id is None:
                marker_decision[marker] = ("skip", None)
                continue
            # Reuse this tag for the marker's later entries.
            marker_decision[marker] = ("existing", created_id)
            planned.add(created_id)
            to_add.append(created_id)
            added_custom += 1

        if not to_add:
            continue

        inserted = await _link_additively(db, user_id=user_id, entry_id=entry_id, tag_ids=to_add)
        if inserted <= 0:
            continue

        # Bump updated_at + emit the entry revision so offline clients pull the
        # new links (link inserts alone don't fire the entries updated_at trigger).
        # Migration 049 calls this against revision 049's schema, so the SELECT
        # must not emit columns a later revision adds (#892's logged_local_hour
        # / inferred_period were the first to strand installs still on 048).
        # load_only is a whitelist, so future entries columns stay out by
        # construction — list exactly what the updated_at touch and the
        # revision-log payload read.
        entry = (
            await db.execute(
                select(Entry)
                .where(Entry.id == entry_id, Entry.user_id == user_id)
                .options(
                    load_only(
                        Entry.user_id,
                        Entry.entry_date,
                        Entry.slot,
                        Entry.mood_score,
                        Entry.energy,
                        Entry.stress,
                        Entry.cycle_day,
                        Entry.cycle_bleeding_level,
                        Entry.sleep_minutes,
                        Entry.sleep_quality,
                        Entry.work_context,
                        Entry.note_visibility,
                        Entry.updated_at,
                    )
                )
            )
        ).scalar_one()
        entry.updated_at = datetime.now(UTC)
        await db.flush()

        from app.services.sync_service import record_entry_upsert_revision

        await record_entry_upsert_revision(db, user_id=user_id, entry=entry)

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
    and the user's DEK so ``Entry.note_enc`` decrypts and the production
    ``correlcore_app`` role sees rows under FORCE RLS.

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
        except (SQLAlchemyError, TagError, CryptoError):
            await db.rollback()
            summary.users_failed += 1
            logger.warning(
                "marker_tag_backfill.user_failed",
                extra={"user_id": str(current_user_id)},
            )
            continue
        summary.merge(user_summary)
    return summary

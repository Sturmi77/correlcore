"""Entry service — business logic for daily entries (M1, Issue #7).

Layering
--------
- Endpoints validate HTTP and shape responses.
- This module owns the business rules:
    * 7-day backdate window (DESIGN_DOCUMENT.md §2.1).
    * One entry per (user, date, slot) — duplicate creates raise
      :class:`EntryConflictError` so the endpoint can map it to 409.
    * Older entries are read-only — updates outside the window raise
      :class:`EntryReadOnlyError` (mapped to 409 with a clear detail).
- Schemas separate request from response. We never echo a stored row
  back without going through ``EntryResponse``.

Privacy
-------
This module never logs ``mood_score``, ``energy``, ``stress`` or the
``note``. Only ``user_id`` and ``entry_id`` go to the structured log.
The log-scrubber test ensures any future regression is caught.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntrySlot, EntrySource, NoteVisibility
from app.models.tag import EntryTag, Tag
from app.schemas.entry import (
    BACKDATE_DAYS_LIMIT,
    CLIENT_TZ_AHEAD_SLACK_DAYS,
    EntryBatchCreate,
    EntryCreate,
    EntryDeltaResponse,
    EntryMetricDelta,
    EntryMetrics,
    EntryResponse,
    EntryUpdate,
)
from app.schemas.note import EntryNoteMarkerResponse, EntryNoteSignalResponse
from app.schemas.tag import TagResponse
from app.services.note_markers import entry_has_note, list_markers_for_entries
from app.services.note_signal_extractor import list_signals_for_entries
from app.services.note_summary import compute_note_summary_short

logger = logging.getLogger(__name__)

# Cap list responses to avoid accidentally pulling thousands of rows.
# The frontend pages the timeline, so this is a guard rail, not a UX limit.
DEFAULT_LIST_LIMIT = 100
MAX_LIST_LIMIT = 365


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class EntryError(Exception):
    """Base class for entry-service errors."""


class EntryNotFoundError(EntryError):
    """Entry does not exist or does not belong to the user."""


class EntryConflictError(EntryError):
    """An entry already exists for this (user, date, slot)."""


class EntryReadOnlyError(EntryError):
    """Entry is older than the backdate window and may not be modified."""


class EntryDateOutOfRangeError(EntryError):
    """The requested date is older than the backdate window for create."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _today() -> date_type:
    """Indirection so tests can monkeypatch the clock.

    Uses UTC explicitly: production images set no ``TZ``, so naive
    ``datetime.now().date()`` was already UTC, but the entry client keys
    rows by device-local day. Keep the server clock unambiguous.
    """
    return datetime.now(UTC).date()


def _within_backdate_window(
    entry_date: date_type,
    *,
    as_of: date_type | None = None,
) -> bool:
    """Return True if ``entry_date`` is within the editable local-day window.

    The nominal window is ``as_of`` (default: server UTC today) and the previous
    :data:`BACKDATE_DAYS_LIMIT` days. Clients use the device-local calendar day
    while this clock is UTC, so allow one day of slack on each edge: local
    "today" east of UTC can be UTC tomorrow, and local "7 days ago" west of UTC
    can be UTC today−8.

    Offline sync passes the client edit day as ``as_of`` so a once-valid write
    is not rejected after the wall-clock window rolls forward (which would
    otherwise 400 the entire push batch and leave the outbox wedged).
    """
    today = as_of if as_of is not None else _today()
    earliest = today - timedelta(days=BACKDATE_DAYS_LIMIT + CLIENT_TZ_AHEAD_SLACK_DAYS)
    latest = today + timedelta(days=CLIENT_TZ_AHEAD_SLACK_DAYS)
    return earliest <= entry_date <= latest


async def _get_owned_entry(db: AsyncSession, *, entry_id: uuid.UUID, user_id: uuid.UUID) -> Entry:
    """Fetch an entry that belongs to ``user_id`` or raise NotFound.

    The user_id filter is the second line of defence after RLS — keeping
    it in the query means tests without active RLS still enforce
    ownership.
    """
    result = await db.execute(select(Entry).where(Entry.id == entry_id, Entry.user_id == user_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundError("entry not found")
    return entry


async def _get_entry_for_day(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_date: date_type,
    slot: EntrySlot,
) -> Entry | None:
    result = await db.execute(
        select(Entry).where(
            Entry.user_id == user_id,
            Entry.entry_date == entry_date,
            Entry.slot == slot,
        )
    )
    return result.scalar_one_or_none()


async def _shared_tags_for_entries(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    today_entry_id: uuid.UUID,
    previous_entry_id: uuid.UUID,
) -> list[Tag]:
    previous_tag_ids = select(EntryTag.tag_id).where(
        EntryTag.user_id == user_id,
        EntryTag.entry_id == previous_entry_id,
    )
    result = await db.execute(
        select(Tag)
        .join(EntryTag, EntryTag.tag_id == Tag.id)
        .where(
            EntryTag.user_id == user_id,
            EntryTag.entry_id == today_entry_id,
            Tag.id.in_(previous_tag_ids),
        )
        .order_by(Tag.category.asc(), Tag.slug.asc())
    )
    return list(result.scalars().all())


def _apply_note_payload(entry: Entry, data: dict[str, object]) -> None:
    """Apply note-related fields and maintain summary / updated_at (ADR-N-01)."""

    note_changed = False
    if "note" in data:
        new_note = data.pop("note")
        note_text = new_note if new_note is None else str(new_note)
        if note_text != entry.note_enc:
            entry.note_enc = note_text
            note_changed = True

    if "note_visibility" in data:
        visibility = data.pop("note_visibility")
        if visibility is None:
            # EntryUpdate allows null; treat as no-op rather than 500.
            pass
        else:
            entry.note_visibility = NoteVisibility(str(visibility))

    if "note_summary_short" in data:
        entry.note_summary_short = data.pop("note_summary_short")  # type: ignore[assignment]
    elif note_changed:
        entry.note_summary_short = compute_note_summary_short(entry.note_enc)

    if note_changed:
        entry.note_updated_at = datetime.now(UTC)


async def build_entry_responses(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entries: list[Entry],
) -> list[EntryResponse]:
    if not entries:
        return []
    markers_by_entry = await list_markers_for_entries(
        db,
        user_id=user_id,
        entry_ids=[entry.id for entry in entries],
    )
    signals_by_entry = await list_signals_for_entries(
        db,
        user_id=user_id,
        entry_ids=[entry.id for entry in entries],
    )
    return [
        EntryResponse.model_validate(entry).model_copy(
            update={
                "note_markers": [
                    EntryNoteMarkerResponse.model_validate(marker)
                    for marker in markers_by_entry.get(entry.id, [])
                ],
                "note_signals": [
                    EntryNoteSignalResponse.model_validate(signal)
                    for signal in signals_by_entry.get(entry.id, [])
                ],
            }
        )
        for entry in entries
    ]


async def build_entry_response(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry: Entry,
) -> EntryResponse:
    responses = await build_entry_responses(db, user_id=user_id, entries=[entry])
    return responses[0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: EntryCreate,
) -> Entry:
    """Create a new entry for ``user_id``.

    Raises:
        EntryDateOutOfRangeError: ``entry_date`` is older than 7 days
            (or in the future — but Pydantic already rejects future dates).
        EntryConflictError: an entry already exists for
            ``(user_id, entry_date, slot)``.
    """
    if not _within_backdate_window(payload.entry_date):
        raise EntryDateOutOfRangeError(
            f"entry_date must be within the last {BACKDATE_DAYS_LIMIT} days"
        )

    entry = Entry(
        user_id=user_id,
        entry_date=payload.entry_date,
        slot=payload.slot,
        mood_score=payload.mood_score,
        energy=payload.energy,
        stress=payload.stress,
        cycle_day=payload.cycle_day,
        source=payload.source,
        work_context=payload.work_context,
        note_enc=payload.note,
        note_visibility=NoteVisibility(payload.note_visibility.value),
    )
    if payload.note:
        entry.note_summary_short = payload.note_summary_short or compute_note_summary_short(
            payload.note
        )
        entry.note_updated_at = datetime.now(UTC)
    elif payload.note_summary_short:
        entry.note_summary_short = payload.note_summary_short
    db.add(entry)
    try:
        await db.flush()
    except IntegrityError as exc:
        # Unique-constraint breach — entry already exists for that day/slot.
        await db.rollback()
        raise EntryConflictError("entry already exists for this date and slot") from exc

    # REST creates must appear in incremental pull after the client's cursor
    # advances; initial backfill only runs when since is None.
    from app.services.sync_service import record_entry_upsert_revision

    await record_entry_upsert_revision(db, user_id=user_id, entry=entry)

    logger.info(
        "entry.created",
        extra={"user_id": str(user_id), "entry_id": str(entry.id)},
    )
    return entry


async def create_entry_batch(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: EntryBatchCreate,
) -> list[Entry]:
    """Create up to seven onboarding retrospective entries atomically."""

    created: list[Entry] = []
    for item in payload.entries:
        if item.source is not EntrySource.RETROSPECTIVE:
            item = item.model_copy(update={"source": EntrySource.RETROSPECTIVE})
        created.append(await create_entry(db, user_id=user_id, payload=item))
    return created


async def get_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> Entry:
    """Return a single entry. Raises :class:`EntryNotFoundError`."""
    return await _get_owned_entry(db, entry_id=entry_id, user_id=user_id)


async def list_entries(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    start_date: date_type | None = None,
    end_date: date_type | None = None,
    limit: int = DEFAULT_LIST_LIMIT,
    has_note: bool | None = None,
) -> list[Entry]:
    """Return entries for ``user_id`` ordered by date desc.

    Bounds are inclusive. ``limit`` is clamped to ``MAX_LIST_LIMIT``.
    When ``has_note`` is set, the SQL predicate filters on stored note/summary
    presence *before* ``LIMIT`` so pages are not emptied by post-filtering.
    """
    from sqlalchemy import or_

    limit = max(1, min(limit, MAX_LIST_LIMIT))

    stmt = select(Entry).where(Entry.user_id == user_id)
    if start_date is not None:
        stmt = stmt.where(Entry.entry_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Entry.entry_date <= end_date)
    if has_note is True:
        stmt = stmt.where(or_(Entry.note_enc.isnot(None), Entry.note_summary_short.isnot(None)))
    elif has_note is False:
        stmt = stmt.where(Entry.note_enc.is_(None), Entry.note_summary_short.is_(None))
    stmt = stmt.order_by(Entry.entry_date.desc(), Entry.slot.asc()).limit(limit)

    result = await db.execute(stmt)
    entries = list(result.scalars().all())
    if has_note is None:
        return entries
    # Decryptable emptiness edge cases (whitespace-only summaries).
    return [entry for entry in entries if entry_has_note(entry) == has_note]


async def get_entry_delta(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_date: date_type,
    slot: EntrySlot = EntrySlot.DAY,
) -> EntryDeltaResponse:
    """Return a neutral day-over-day comparison for one entry date and slot."""

    today = await _get_entry_for_day(db, user_id=user_id, entry_date=entry_date, slot=slot)
    previous_date = entry_date - timedelta(days=1)
    previous = await _get_entry_for_day(
        db,
        user_id=user_id,
        entry_date=previous_date,
        slot=slot,
    )

    if today is None or previous is None:
        return EntryDeltaResponse(
            today=EntryMetrics.model_validate(today) if today is not None else None,
            previous=EntryMetrics.model_validate(previous) if previous is not None else None,
        )

    shared_tags = await _shared_tags_for_entries(
        db,
        user_id=user_id,
        today_entry_id=today.id,
        previous_entry_id=previous.id,
    )
    return EntryDeltaResponse(
        today=EntryMetrics.model_validate(today),
        previous=EntryMetrics.model_validate(previous),
        delta=EntryMetricDelta(
            mood=today.mood_score - previous.mood_score,
            energy=today.energy - previous.energy,
            stress=today.stress - previous.stress,
        ),
        shared_tags=[TagResponse.model_validate(tag) for tag in shared_tags],
    )


async def update_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    payload: EntryUpdate,
) -> Entry:
    """Update a non-stale entry.

    Raises:
        EntryNotFoundError: entry does not exist or belongs to a
            different user.
        EntryReadOnlyError: entry is older than the backdate window.
    """
    entry = await _get_owned_entry(db, entry_id=entry_id, user_id=user_id)

    if not _within_backdate_window(entry.entry_date):
        raise EntryReadOnlyError(f"entries older than {BACKDATE_DAYS_LIMIT} days are read-only")

    data = payload.model_dump(exclude_unset=True, by_alias=False)
    _apply_note_payload(entry, data)
    for field, value in data.items():
        setattr(entry, field, value)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise EntryConflictError("entry already exists for this date and slot") from exc

    from app.services.sync_service import record_entry_upsert_revision

    await record_entry_upsert_revision(db, user_id=user_id, entry=entry)

    logger.info(
        "entry.updated",
        extra={"user_id": str(user_id), "entry_id": str(entry.id)},
    )
    return entry


# Re-export the slot enum for endpoint-layer convenience.
__all__ = [
    "DEFAULT_LIST_LIMIT",
    "EntryConflictError",
    "EntryDateOutOfRangeError",
    "EntryError",
    "EntryNotFoundError",
    "EntryReadOnlyError",
    "EntrySlot",
    "MAX_LIST_LIMIT",
    "build_entry_response",
    "build_entry_responses",
    "create_entry",
    "create_entry_batch",
    "get_entry_delta",
    "get_entry",
    "list_entries",
    "update_entry",
]

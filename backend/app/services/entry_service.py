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

from app.models.entry import Entry, EntrySlot
from app.schemas.entry import BACKDATE_DAYS_LIMIT, EntryCreate, EntryUpdate

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
    """Indirection so tests can monkeypatch the clock."""
    return datetime.now(UTC).date()


def _within_backdate_window(entry_date: date_type) -> bool:
    """Return True if ``entry_date`` is within the 7-day backdate window."""
    delta = _today() - entry_date
    return timedelta(days=0) <= delta <= timedelta(days=BACKDATE_DAYS_LIMIT)


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
        work_context=payload.work_context,
        note_enc=payload.note,
    )
    db.add(entry)
    try:
        await db.flush()
    except IntegrityError as exc:
        # Unique-constraint breach — entry already exists for that day/slot.
        await db.rollback()
        raise EntryConflictError("entry already exists for this date and slot") from exc

    logger.info(
        "entry.created",
        extra={"user_id": str(user_id), "entry_id": str(entry.id)},
    )
    return entry


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
) -> list[Entry]:
    """Return entries for ``user_id`` ordered by date desc.

    Bounds are inclusive. ``limit`` is clamped to ``MAX_LIST_LIMIT``.
    """
    limit = max(1, min(limit, MAX_LIST_LIMIT))

    stmt = select(Entry).where(Entry.user_id == user_id)
    if start_date is not None:
        stmt = stmt.where(Entry.entry_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Entry.entry_date <= end_date)
    stmt = stmt.order_by(Entry.entry_date.desc(), Entry.slot.asc()).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


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

    data = payload.model_dump(exclude_unset=True)
    if "note" in data:
        entry.note_enc = data.pop("note")
    for field, value in data.items():
        setattr(entry, field, value)

    await db.flush()

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
    "create_entry",
    "get_entry",
    "list_entries",
    "update_entry",
]

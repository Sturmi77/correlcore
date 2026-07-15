"""Note marker normalisation, CRUD, suggestions, and marker-summary aggregation."""

from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, NoteVisibility
from app.models.entry_note import EntryNoteMarker, NoteMarkerSource
from app.schemas.note import (
    MAX_CUSTOM_MARKER_LENGTH,
    PREDEFINED_NOTE_MARKERS,
    EntryNoteMarkerCreate,
    MarkerSummaryItem,
)

logger = logging.getLogger(__name__)

_WHITESPACE = re.compile(r"\s+")


class NoteMarkerError(Exception):
    """Base class for note-marker service errors."""


class NoteMarkerValidationError(NoteMarkerError):
    """Marker text failed normalisation or length rules."""


class NoteMarkerNotFoundError(NoteMarkerError):
    """Marker row does not exist for the entry/user."""


class NoteMarkerConflictError(NoteMarkerError):
    """Marker already exists on the entry."""


def normalise_marker(raw: str) -> str:
    """Normalise a marker key on write (ADR-N-03)."""

    text = unicodedata.normalize("NFKC", raw)
    text = _WHITESPACE.sub(" ", text.strip())
    text = text.lower()
    if not text:
        raise NoteMarkerValidationError("marker must not be empty")
    if len(text) > MAX_CUSTOM_MARKER_LENGTH:
        raise NoteMarkerValidationError(
            f"marker must be at most {MAX_CUSTOM_MARKER_LENGTH} characters after normalisation"
        )
    return text


def is_predefined_marker(marker: str) -> bool:
    return marker in PREDEFINED_NOTE_MARKERS


async def _get_owned_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> Entry:
    result = await db.execute(select(Entry).where(Entry.id == entry_id, Entry.user_id == user_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise NoteMarkerNotFoundError("entry not found")
    return entry


async def list_markers_for_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> list[EntryNoteMarker]:
    await _get_owned_entry(db, user_id=user_id, entry_id=entry_id)
    result = await db.execute(
        select(EntryNoteMarker)
        .where(EntryNoteMarker.entry_id == entry_id, EntryNoteMarker.user_id == user_id)
        .order_by(EntryNoteMarker.created_at.asc())
    )
    return list(result.scalars().all())


async def list_markers_for_entries(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, list[EntryNoteMarker]]:
    if not entry_ids:
        return {}
    result = await db.execute(
        select(EntryNoteMarker)
        .where(
            EntryNoteMarker.user_id == user_id,
            EntryNoteMarker.entry_id.in_(entry_ids),
        )
        .order_by(EntryNoteMarker.created_at.asc())
    )
    grouped: dict[uuid.UUID, list[EntryNoteMarker]] = defaultdict(list)
    for marker in result.scalars().all():
        grouped[marker.entry_id].append(marker)
    return dict(grouped)


async def add_marker_to_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    payload: EntryNoteMarkerCreate,
) -> EntryNoteMarker:
    await _get_owned_entry(db, user_id=user_id, entry_id=entry_id)
    marker_key = normalise_marker(payload.marker)
    row = EntryNoteMarker(
        entry_id=entry_id,
        user_id=user_id,
        marker=marker_key,
        source=payload.source,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise NoteMarkerConflictError("marker already exists on this entry") from exc
    logger.info(
        "note_marker.created",
        extra={"user_id": str(user_id), "entry_id": str(entry_id), "marker": marker_key},
    )
    return row


async def delete_marker_from_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    marker_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(EntryNoteMarker).where(
            EntryNoteMarker.id == marker_id,
            EntryNoteMarker.entry_id == entry_id,
            EntryNoteMarker.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NoteMarkerNotFoundError("marker not found")
    await db.execute(delete(EntryNoteMarker).where(EntryNoteMarker.id == marker_id))
    await db.flush()
    logger.info(
        "note_marker.deleted",
        extra={"user_id": str(user_id), "entry_id": str(entry_id), "marker_id": str(marker_id)},
    )


async def list_user_marker_suggestions(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list[str]:
    """Return custom user markers ordered by frequency (excludes predefined taxonomy)."""

    result = await db.execute(
        select(EntryNoteMarker.marker, func.count())
        .where(
            EntryNoteMarker.user_id == user_id,
            EntryNoteMarker.source == NoteMarkerSource.USER.value,
        )
        .group_by(EntryNoteMarker.marker)
        .order_by(func.count().desc(), EntryNoteMarker.marker.asc())
        .limit(limit * 2)
    )
    suggestions: list[str] = []
    for marker, _count in result.all():
        if marker in PREDEFINED_NOTE_MARKERS:
            continue
        suggestions.append(marker)
        if len(suggestions) >= limit:
            break
    return suggestions


async def aggregate_marker_summary(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    from_date: date_type,
    to_date: date_type,
    markers: Sequence[str] | None = None,
) -> list[MarkerSummaryItem]:
    """Aggregate mood averages per marker in the inclusive date window."""

    if from_date > to_date:
        raise NoteMarkerValidationError("from must be on or before to")

    marker_filter: set[str] | None = None
    if markers:
        marker_filter = {normalise_marker(marker) for marker in markers}

    stmt = (
        select(
            EntryNoteMarker.marker,
            Entry.id,
            Entry.mood_score,
        )
        .join(Entry, Entry.id == EntryNoteMarker.entry_id)
        .where(
            EntryNoteMarker.user_id == user_id,
            Entry.user_id == user_id,
            Entry.entry_date >= from_date,
            Entry.entry_date <= to_date,
            Entry.note_visibility != NoteVisibility.HIDDEN.value,
        )
    )
    if marker_filter is not None:
        stmt = stmt.where(EntryNoteMarker.marker.in_(marker_filter))

    rows = (await db.execute(stmt)).all()
    by_marker: dict[str, list[tuple[uuid.UUID, int]]] = defaultdict(list)
    for marker_key, entry_id, mood_score in rows:
        by_marker[marker_key].append((entry_id, mood_score))

    items: list[MarkerSummaryItem] = []
    for marker_key, entries in sorted(by_marker.items(), key=lambda item: item[0]):
        moods = [mood for _entry_id, mood in entries]
        items.append(
            MarkerSummaryItem(
                marker=marker_key,
                count=len(entries),
                avg_mood=round(sum(moods) / len(moods), 2),
                entries=[entry_id for entry_id, _mood in entries],
            )
        )
    return items


def entry_has_note(entry: Entry) -> bool:
    return bool(entry.note_enc and str(entry.note_enc).strip()) or bool(
        entry.note_summary_short and entry.note_summary_short.strip()
    )

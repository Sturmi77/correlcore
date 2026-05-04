"""Symptom service — business logic for entry symptoms (M1, Issue #9).

Layering
--------
- Endpoints validate HTTP and shape responses.
- This module owns the business rules:
    * The user can only read or write symptoms attached to *their own*
      entries. Cross-user access surfaces as
      :class:`EntryNotFoundForSymptomError` (mapped to 404 by the
      endpoint).
    * Assigning symptoms to an entry replaces the current set — the
      service computes a key-level diff (add / update intensity /
      remove) so the table never accumulates stale rows.

Privacy
-------
Symptoms are health data under DSGVO Art. 9. This service therefore
**never logs** ``symptom_key`` or ``intensity`` — only ``user_id``,
``entry_id`` and aggregate counters appear in structured logs. The
log-scrubber test in ``test_symptoms.py`` enforces this.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.symptom import EntrySymptom
from app.schemas.symptom import SymptomEntry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SymptomError(Exception):
    """Base class for symptom-service errors."""


class EntryNotFoundForSymptomError(SymptomError):
    """The target entry does not exist or belongs to a different user."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_owned_entry(db: AsyncSession, *, entry_id: uuid.UUID, user_id: uuid.UUID) -> Entry:
    """Fetch an entry the user owns or raise :class:`EntryNotFoundForSymptomError`."""
    result = await db.execute(select(Entry).where(Entry.id == entry_id, Entry.user_id == user_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundForSymptomError("entry not found")
    return entry


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def list_symptoms_for_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> list[EntrySymptom]:
    """Return symptoms currently logged on ``entry_id`` (owner-scoped)."""
    await _get_owned_entry(db, entry_id=entry_id, user_id=user_id)

    stmt = (
        select(EntrySymptom)
        .where(EntrySymptom.entry_id == entry_id, EntrySymptom.user_id == user_id)
        .order_by(EntrySymptom.symptom_key.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def assign_symptoms_to_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    symptoms: Sequence[SymptomEntry],
) -> list[EntrySymptom]:
    """Replace the entry's symptom set with ``symptoms``.

    Replace-set semantics with key-level granularity:
      * Symptoms whose ``symptom_key`` is in the new list but not in
        the current set are inserted.
      * Symptoms whose key is in both have their ``intensity``
        overwritten if it changed.
      * Symptoms whose key is missing from the new list are deleted.

    Raises:
        EntryNotFoundForSymptomError: entry not visible to the user.
    """
    await _get_owned_entry(db, entry_id=entry_id, user_id=user_id)

    target = {s.symptom_key: s.intensity for s in symptoms}

    current_rows_result = await db.execute(
        select(EntrySymptom).where(
            EntrySymptom.entry_id == entry_id,
            EntrySymptom.user_id == user_id,
        )
    )
    current_rows = list(current_rows_result.scalars().all())
    current_map = {row.symptom_key: row for row in current_rows}

    target_keys = set(target)
    current_keys = set(current_map)
    to_remove = current_keys - target_keys
    to_add = target_keys - current_keys
    to_update = target_keys & current_keys

    if to_remove:
        await db.execute(
            delete(EntrySymptom).where(
                EntrySymptom.entry_id == entry_id,
                EntrySymptom.user_id == user_id,
                EntrySymptom.symptom_key.in_(to_remove),
            )
        )

    intensity_updates = 0
    for key in to_update:
        row = current_map[key]
        if row.intensity != target[key]:
            row.intensity = target[key]
            intensity_updates += 1

    for key in to_add:
        db.add(
            EntrySymptom(
                entry_id=entry_id,
                user_id=user_id,
                symptom_key=key,
                intensity=target[key],
            )
        )

    await db.flush()

    logger.info(
        "entry.symptoms.assigned",
        extra={
            "user_id": str(user_id),
            "entry_id": str(entry_id),
            "added_count": len(to_add),
            "removed_count": len(to_remove),
            "updated_count": intensity_updates,
        },
    )

    # Return the fresh set so the endpoint can shape the response.
    refreshed = await db.execute(
        select(EntrySymptom)
        .where(EntrySymptom.entry_id == entry_id, EntrySymptom.user_id == user_id)
        .order_by(EntrySymptom.symptom_key.asc())
    )
    return list(refreshed.scalars().all())


__all__ = [
    "EntryNotFoundForSymptomError",
    "SymptomError",
    "assign_symptoms_to_entry",
    "list_symptoms_for_entry",
]

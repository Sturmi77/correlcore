"""Symptom service — business logic for symptom CRUD and entry assignment.

Layering
--------
- Endpoints validate HTTP and shape responses.
- This module owns the business rules:
    * The user can only mutate *their own* custom symptoms. Default
      symptoms are read-only.
    * Slug uniqueness conflicts surface as
      :class:`SymptomConflictError` so the endpoint can map them to 409.
    * Assigning symptoms to an entry replaces the current set with
      key-level granularity (add / update intensity / remove) so the
      table never accumulates stale rows on intensity edits.
    * Cross-user access surfaces as
      :class:`EntryNotFoundForSymptomError` (mapped to 404 by the
      endpoint).

Privacy
-------
Symptoms are health data under DSGVO Art. 9. This service therefore
**never logs** ``symptom_id``, slug, name, or ``intensity`` — only
``user_id``, ``entry_id`` and aggregate counters appear in structured
logs. The static log-scrubbing test (``test_log_scrubbing.py``) and the
service-local log-scrubber test in ``test_symptoms.py`` enforce this.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.symptom import EntrySymptom, Symptom
from app.schemas.symptom import SymptomCreate, SymptomEntry, SymptomUpdate

logger = logging.getLogger(__name__)

# Cap list responses for safety. Defaults will always fit (~5); custom
# symptoms rarely exceed 50 per user. The cap is a guard rail.
DEFAULT_SYMPTOM_LIST_LIMIT = 200
MAX_SYMPTOM_LIST_LIMIT = 1000


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SymptomError(Exception):
    """Base class for symptom-service errors."""


class SymptomNotFoundError(SymptomError):
    """Symptom does not exist or does not belong to the user."""


class SymptomConflictError(SymptomError):
    """Slug already exists for this user (or clashes with a default)."""


class SymptomOperationDeniedError(SymptomError):
    """Operation is not allowed (e.g. mutating a default symptom)."""


class EntryNotFoundForSymptomError(SymptomError):
    """The target entry does not exist or belongs to a different user."""


class SymptomsNotFoundError(SymptomError):
    """One or more symptom IDs in the assignment payload are not visible."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_owned_custom_symptom(
    db: AsyncSession,
    *,
    symptom_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Symptom:
    """Fetch a custom symptom the user owns or raise :class:`SymptomNotFoundError`.

    Default symptoms (``user_id IS NULL``) are excluded — this helper is
    used for write paths where defaults are not editable.
    """
    result = await db.execute(
        select(Symptom).where(
            Symptom.id == symptom_id,
            Symptom.user_id == user_id,
            Symptom.is_default.is_(False),
        )
    )
    symptom = result.scalar_one_or_none()
    if symptom is None:
        raise SymptomNotFoundError("symptom not found")
    return symptom


async def _get_owned_entry(db: AsyncSession, *, entry_id: uuid.UUID, user_id: uuid.UUID) -> Entry:
    """Fetch an entry the user owns or raise :class:`EntryNotFoundForSymptomError`."""
    result = await db.execute(select(Entry).where(Entry.id == entry_id, Entry.user_id == user_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundForSymptomError("entry not found")
    return entry


# ---------------------------------------------------------------------------
# Public API — Symptom CRUD
# ---------------------------------------------------------------------------


async def list_default_symptoms(db: AsyncSession) -> list[Symptom]:
    """Return all curated default symptoms ordered by slug."""
    result = await db.execute(
        select(Symptom).where(Symptom.is_default.is_(True)).order_by(Symptom.slug.asc())
    )
    return list(result.scalars().all())


async def list_visible_symptoms(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = DEFAULT_SYMPTOM_LIST_LIMIT,
) -> list[Symptom]:
    """Return defaults *plus* the user's own custom symptoms, ordered by slug."""
    limit = max(1, min(limit, MAX_SYMPTOM_LIST_LIMIT))
    stmt = (
        select(Symptom)
        .where((Symptom.is_default.is_(True)) | (Symptom.user_id == user_id))
        .order_by(Symptom.slug.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_custom_symptom(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: SymptomCreate,
) -> Symptom:
    """Create a custom symptom for ``user_id``.

    Raises:
        SymptomConflictError: the user already owns a symptom with this
            slug, *or* the slug clashes with a curated default.
    """
    # Pre-check against defaults: a custom symptom must not shadow a
    # curated slug (frontend disambiguates by slug).
    default_clash = await db.execute(
        select(Symptom).where(Symptom.is_default.is_(True), Symptom.slug == payload.slug)
    )
    if default_clash.scalar_one_or_none() is not None:
        raise SymptomConflictError("slug clashes with a default symptom")

    # Issue #26: custom symptom names are Art.-9-relevant. Store the
    # ciphertext under the user's DEK in ``name_enc`` and leave ``name``
    # NULL (the CHECK constraint enforces the polymorphism).
    symptom = Symptom(
        user_id=user_id,
        slug=payload.slug,
        icon=payload.icon,
        is_default=False,
    )
    symptom.set_custom_name(payload.name)
    db.add(symptom)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise SymptomConflictError("symptom with this slug already exists") from exc

    logger.info(
        "symptom.created",
        extra={"user_id": str(user_id), "symptom_id": str(symptom.id)},
    )
    return symptom


async def update_custom_symptom(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    symptom_id: uuid.UUID,
    payload: SymptomUpdate,
) -> Symptom:
    """Update a custom symptom the user owns.

    Raises:
        SymptomNotFoundError: symptom does not exist, belongs to another
            user, or is a curated default (defaults are read-only).
    """
    symptom = await _get_owned_custom_symptom(db, symptom_id=symptom_id, user_id=user_id)

    data = payload.model_dump(exclude_unset=True)
    # ``name`` is encrypted; route it through the model helper so the
    # ciphertext is written to ``name_enc`` and ``name`` stays NULL.
    if "name" in data:
        new_name = data.pop("name")
        if new_name is not None:
            symptom.set_custom_name(new_name)
    for field, value in data.items():
        setattr(symptom, field, value)

    await db.flush()

    logger.info(
        "symptom.updated",
        extra={"user_id": str(user_id), "symptom_id": str(symptom.id)},
    )
    return symptom


async def delete_custom_symptom(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    symptom_id: uuid.UUID,
) -> None:
    """Delete a custom symptom the user owns.

    The DB cascades to ``entry_symptoms`` so historical entries lose the
    reference cleanly.
    """
    symptom = await _get_owned_custom_symptom(db, symptom_id=symptom_id, user_id=user_id)
    await db.delete(symptom)
    await db.flush()

    logger.info(
        "symptom.deleted",
        extra={"user_id": str(user_id), "symptom_id": str(symptom_id)},
    )


# ---------------------------------------------------------------------------
# Public API — Entry-symptom assignment
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
        .order_by(EntrySymptom.symptom_id.asc())
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

    Replace-set semantics with ID-level granularity:
      * Symptoms whose ``symptom_id`` is in the new list but not the
        current set are inserted.
      * Symptoms whose ID is in both have their ``intensity`` overwritten
        if it changed.
      * Symptoms whose ID is missing from the new list are deleted.

    Raises:
        EntryNotFoundForSymptomError: entry not visible to the user.
        SymptomsNotFoundError: at least one ``symptom_id`` is not visible
            (neither a default nor one of the user's custom symptoms).
    """
    await _get_owned_entry(db, entry_id=entry_id, user_id=user_id)

    target = {s.symptom_id: s.intensity for s in symptoms}

    # Validate all symptom IDs are visible to the user.
    if target:
        visible = await db.execute(
            select(Symptom.id).where(
                Symptom.id.in_(target.keys()),
                (Symptom.is_default.is_(True)) | (Symptom.user_id == user_id),
            )
        )
        visible_ids = {row[0] for row in visible.all()}
        missing = set(target.keys()) - visible_ids
        if missing:
            raise SymptomsNotFoundError(
                f"unknown or inaccessible symptom ids: {sorted(map(str, missing))}"
            )

    current_rows_result = await db.execute(
        select(EntrySymptom).where(
            EntrySymptom.entry_id == entry_id,
            EntrySymptom.user_id == user_id,
        )
    )
    current_rows = list(current_rows_result.scalars().all())
    current_map = {row.symptom_id: row for row in current_rows}

    target_ids = set(target)
    current_ids = set(current_map)
    to_remove = current_ids - target_ids
    to_add = target_ids - current_ids
    to_update = target_ids & current_ids

    if to_remove:
        await db.execute(
            delete(EntrySymptom).where(
                EntrySymptom.entry_id == entry_id,
                EntrySymptom.user_id == user_id,
                EntrySymptom.symptom_id.in_(to_remove),
            )
        )

    intensity_updates = 0
    for sid in to_update:
        row = current_map[sid]
        if row.intensity != target[sid]:
            row.intensity = target[sid]
            intensity_updates += 1

    for sid in to_add:
        db.add(
            EntrySymptom(
                entry_id=entry_id,
                user_id=user_id,
                symptom_id=sid,
                intensity=target[sid],
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

    refreshed = await db.execute(
        select(EntrySymptom)
        .where(EntrySymptom.entry_id == entry_id, EntrySymptom.user_id == user_id)
        .order_by(EntrySymptom.symptom_id.asc())
    )
    return list(refreshed.scalars().all())


__all__ = [
    "DEFAULT_SYMPTOM_LIST_LIMIT",
    "MAX_SYMPTOM_LIST_LIMIT",
    "EntryNotFoundForSymptomError",
    "SymptomConflictError",
    "SymptomError",
    "SymptomNotFoundError",
    "SymptomOperationDeniedError",
    "SymptomsNotFoundError",
    "assign_symptoms_to_entry",
    "create_custom_symptom",
    "delete_custom_symptom",
    "list_default_symptoms",
    "list_symptoms_for_entry",
    "list_visible_symptoms",
    "update_custom_symptom",
]

"""Symptom and entry-symptom-assignment endpoints (M1, Issue #9).

Mounted under two prefixes:

- ``/api/v1/symptoms`` — read-only catalogue of standard symptom keys.
- ``/api/v1/entries/{entry_id}/symptoms`` — per-entry assignment, kept
  alongside the entry hierarchy for REST symmetry with tags.

All write endpoints require an active *and verified* user. Rate-limits
match the entry-endpoint policy (60/min for write, 120/min for read).

Privacy
-------
Symptom payloads are health data under DSGVO Art. 9. The service layer
is responsible for not logging ``symptom_key`` or ``intensity``; the
endpoints here only relay validated wire data and shape responses.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.symptom import STANDARD_SYMPTOM_KEYS
from app.models.user import User
from app.schemas.symptom import (
    EntrySymptomAssignment,
    StandardSymptomKey,
    StandardSymptomKeyList,
    SymptomResponse,
)
from app.services.symptom_service import (
    EntryNotFoundForSymptomError,
    assign_symptoms_to_entry,
    list_symptoms_for_entry,
)

logger = logging.getLogger(__name__)

# Two routers — ``/symptoms`` for the catalogue, ``/entries`` for the
# per-entry assignment surface. router.py wires them with the right
# prefixes so the URL hierarchy stays REST-idiomatic.
symptoms_router = APIRouter()
entry_symptoms_router = APIRouter()


# ---------------------------------------------------------------------------
# /symptoms
# ---------------------------------------------------------------------------


@symptoms_router.get(
    "/standard",
    response_model=StandardSymptomKeyList,
    summary="List the curated standard symptom keys (no auth required)",
)
@limiter.limit("120/minute")
async def list_standard_symptom_keys_endpoint(
    request: Request,
) -> StandardSymptomKeyList:
    """Return the closed set of standard symptom keys.

    The list is non-personal (it's a build-time constant, not user data),
    so we expose it without auth — the picker can render before login
    completes. The frontend pairs each key with a translated label and
    icon at render time.
    """
    keys = sorted(STANDARD_SYMPTOM_KEYS)
    return StandardSymptomKeyList(
        keys=[StandardSymptomKey(symptom_key=k) for k in keys],
    )


# ---------------------------------------------------------------------------
# /entries/{entry_id}/symptoms
# ---------------------------------------------------------------------------


@entry_symptoms_router.get(
    "/{entry_id}/symptoms",
    response_model=list[SymptomResponse],
    summary="List symptoms logged on an entry",
)
@limiter.limit("120/minute")
async def list_entry_symptoms_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[SymptomResponse]:
    try:
        rows = await list_symptoms_for_entry(db, user_id=user.id, entry_id=entry_id)
    except EntryNotFoundForSymptomError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entry not found",
        ) from exc
    return [SymptomResponse.model_validate(r) for r in rows]


@entry_symptoms_router.put(
    "/{entry_id}/symptoms",
    response_model=list[SymptomResponse],
    summary="Replace the symptom set for an entry",
)
@limiter.limit("60/minute")
async def assign_entry_symptoms_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    payload: EntrySymptomAssignment,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[SymptomResponse]:
    try:
        rows = await assign_symptoms_to_entry(
            db,
            user_id=user.id,
            entry_id=entry_id,
            symptoms=payload.symptoms,
        )
    except EntryNotFoundForSymptomError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entry not found",
        ) from exc
    return [SymptomResponse.model_validate(r) for r in rows]

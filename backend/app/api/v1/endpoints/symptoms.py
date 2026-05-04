"""Symptom and entry-symptom-assignment endpoints (Issue #57, ADR-0008).

Mounted under two prefixes:

- ``/api/v1/symptoms`` — symptom CRUD (defaults + custom).
- ``/api/v1/entries/{entry_id}/symptoms`` — per-entry assignment, kept
  alongside the entry hierarchy for REST symmetry with tags.

All write endpoints require an active *and verified* user. Rate-limits
match the entry-endpoint policy (60/min for write, 120/min for read).

Privacy
-------
Symptom payloads are health data under DSGVO Art. 9. The service layer
is responsible for not logging slug, name, ``symptom_id`` or ``intensity``;
the endpoints here only relay validated wire data and shape responses.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.symptom import (
    EntrySymptomAssignment,
    EntrySymptomResponse,
    SymptomCreate,
    SymptomResponse,
    SymptomUpdate,
)
from app.services.symptom_service import (
    DEFAULT_SYMPTOM_LIST_LIMIT,
    MAX_SYMPTOM_LIST_LIMIT,
    EntryNotFoundForSymptomError,
    SymptomConflictError,
    SymptomNotFoundError,
    SymptomsNotFoundError,
    assign_symptoms_to_entry,
    create_custom_symptom,
    delete_custom_symptom,
    list_default_symptoms,
    list_symptoms_for_entry,
    list_visible_symptoms,
    update_custom_symptom,
)

logger = logging.getLogger(__name__)

# Two routers — ``/symptoms`` for CRUD on the master catalogue,
# ``/entries`` for the per-entry assignment surface. router.py wires
# them with the right prefixes so the URL hierarchy stays REST-idiomatic.
symptoms_router = APIRouter()
entry_symptoms_router = APIRouter()


# ---------------------------------------------------------------------------
# /symptoms
# ---------------------------------------------------------------------------


@symptoms_router.get(
    "/default",
    response_model=list[SymptomResponse],
    summary="List curated default symptoms (no auth required)",
)
@limiter.limit("120/minute")
async def list_default_symptoms_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> list[SymptomResponse]:
    """Return the curated default symptoms.

    Default symptoms are not user-specific and the list is small (~5),
    so we expose this without an auth requirement to keep the registration
    UX snappy (the picker can render before login completes). The data
    is non-personal.
    """
    symptoms = await list_default_symptoms(db)
    return [SymptomResponse.model_validate(s) for s in symptoms]


@symptoms_router.get(
    "",
    response_model=list[SymptomResponse],
    summary="List all symptoms visible to the user (defaults + own customs)",
)
@limiter.limit("120/minute")
async def list_symptoms_endpoint(
    request: Request,
    limit: int = Query(default=DEFAULT_SYMPTOM_LIST_LIMIT, ge=1, le=MAX_SYMPTOM_LIST_LIMIT),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[SymptomResponse]:
    symptoms = await list_visible_symptoms(db, user_id=user.id, limit=limit)
    return [SymptomResponse.model_validate(s) for s in symptoms]


@symptoms_router.post(
    "",
    response_model=SymptomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom symptom",
)
@limiter.limit("60/minute")
async def create_symptom_endpoint(
    request: Request,
    payload: SymptomCreate,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> SymptomResponse:
    try:
        symptom = await create_custom_symptom(db, user_id=user.id, payload=payload)
    except SymptomConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return SymptomResponse.model_validate(symptom)


@symptoms_router.patch(
    "/{symptom_id}",
    response_model=SymptomResponse,
    summary="Update a custom symptom (defaults are read-only)",
)
@limiter.limit("60/minute")
async def update_symptom_endpoint(
    request: Request,
    symptom_id: uuid.UUID,
    payload: SymptomUpdate,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> SymptomResponse:
    try:
        symptom = await update_custom_symptom(
            db, user_id=user.id, symptom_id=symptom_id, payload=payload
        )
    except SymptomNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="symptom not found",
        ) from exc
    return SymptomResponse.model_validate(symptom)


@symptoms_router.delete(
    "/{symptom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom symptom (defaults are read-only)",
)
@limiter.limit("60/minute")
async def delete_symptom_endpoint(
    request: Request,
    symptom_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await delete_custom_symptom(db, user_id=user.id, symptom_id=symptom_id)
    except SymptomNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="symptom not found",
        ) from exc


# ---------------------------------------------------------------------------
# /entries/{entry_id}/symptoms
# ---------------------------------------------------------------------------


@entry_symptoms_router.get(
    "/{entry_id}/symptoms",
    response_model=list[EntrySymptomResponse],
    summary="List symptoms logged on an entry",
)
@limiter.limit("120/minute")
async def list_entry_symptoms_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[EntrySymptomResponse]:
    try:
        rows = await list_symptoms_for_entry(db, user_id=user.id, entry_id=entry_id)
    except EntryNotFoundForSymptomError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entry not found",
        ) from exc
    return [EntrySymptomResponse.model_validate(r) for r in rows]


@entry_symptoms_router.put(
    "/{entry_id}/symptoms",
    response_model=list[EntrySymptomResponse],
    summary="Replace the symptom set for an entry",
)
@limiter.limit("60/minute")
async def assign_entry_symptoms_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    payload: EntrySymptomAssignment,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[EntrySymptomResponse]:
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
    except SymptomsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return [EntrySymptomResponse.model_validate(r) for r in rows]

"""Entry endpoints — daily mood/energy/stress log (M1, Issue #7).

All endpoints require an active *and verified* user
(``get_current_verified_user``). Unverified accounts cannot create
sensitive content (DSGVO-relevant data) — this matches the auth
middleware acceptance criterion in M1.

Rate-limiting
-------------
``POST /entries`` is limited to 60/min per IP. The 60-second-rule
(DESIGN_DOCUMENT.md §6) targets a single happy-path submit per minute;
the limit is generous enough to allow retries on flaky networks but
tight enough to make brute-force enumeration of valid IDs uneconomical.
``GET`` endpoints are limited to 120/min per IP — generous, since list
fetches are normal user behaviour.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.entry import EntrySlot
from app.models.user import User
from app.schemas.entry import (
    EntryBatchCreate,
    EntryCreate,
    EntryDeltaResponse,
    EntryResponse,
    EntryUpdate,
)
from app.schemas.stats import (
    EntryStreakResponse,
    TagHeatmapResponse,
    TimeseriesRange,
    TimeseriesResponse,
)
from app.services.entry_service import (
    DEFAULT_LIST_LIMIT,
    MAX_LIST_LIMIT,
    EntryConflictError,
    EntryDateOutOfRangeError,
    EntryNotFoundError,
    EntryReadOnlyError,
    create_entry,
    create_entry_batch,
    get_entry,
    get_entry_delta,
    list_entries,
    update_entry,
)
from app.services.stats_service import get_entry_streak, get_tag_heatmap, get_timeseries

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=EntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a daily entry",
)
@limiter.limit("60/minute")
async def create_entry_endpoint(
    request: Request,
    payload: EntryCreate,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> EntryResponse:
    try:
        entry = await create_entry(db, user_id=user.id, payload=payload)
    except EntryDateOutOfRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except EntryConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return EntryResponse.model_validate(entry)


@router.post(
    "/batch",
    response_model=list[EntryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a small retrospective entry batch",
)
@limiter.limit("20/minute")
async def create_entry_batch_endpoint(
    request: Request,
    payload: EntryBatchCreate,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[EntryResponse]:
    try:
        entries = await create_entry_batch(db, user_id=user.id, payload=payload)
    except EntryDateOutOfRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except EntryConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return [EntryResponse.model_validate(entry) for entry in entries]


# ---------------------------------------------------------------------------
# M2 statistics
# ---------------------------------------------------------------------------


@router.get(
    "/stats/timeseries",
    response_model=TimeseriesResponse,
    summary="Return mood, energy and stress time-series aggregates",
)
@limiter.limit("120/minute")
async def get_timeseries_endpoint(
    request: Request,
    range: TimeseriesRange = Query(default="week"),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> TimeseriesResponse:
    return await get_timeseries(db, user_id=user.id, range_=range)


@router.get(
    "/stats/tags",
    response_model=TagHeatmapResponse,
    summary="Return tag frequency heatmap data",
)
@limiter.limit("120/minute")
async def get_tag_heatmap_endpoint(
    request: Request,
    start_date: date_type | None = Query(default=None, alias="start_date"),
    end_date: date_type | None = Query(default=None, alias="end_date"),
    category: str | None = Query(default=None),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> TagHeatmapResponse:
    from app.models.tag import TagCategory

    parsed_category = None
    if category is not None:
        try:
            parsed_category = TagCategory(category)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="unknown tag category",
            ) from exc
    return await get_tag_heatmap(
        db,
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
        category=parsed_category,
    )


@router.get(
    "/stats/streak",
    response_model=EntryStreakResponse,
    summary="Return entry-streak metrics",
)
@limiter.limit("120/minute")
async def get_entry_streak_endpoint(
    request: Request,
    as_of: date_type | None = Query(default=None, alias="as_of"),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> EntryStreakResponse:
    return await get_entry_streak(db, user_id=user.id, as_of=as_of)


@router.get(
    "/delta",
    response_model=EntryDeltaResponse,
    summary="Return a neutral day-over-day entry comparison",
)
@limiter.limit("120/minute")
async def get_entry_delta_endpoint(
    request: Request,
    entry_date: date_type = Query(..., alias="entry_date"),
    slot: EntrySlot = Query(default=EntrySlot.DAY),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> EntryDeltaResponse:
    return await get_entry_delta(db, user_id=user.id, entry_date=entry_date, slot=slot)


# ---------------------------------------------------------------------------
# Read — single
# ---------------------------------------------------------------------------


@router.get(
    "/{entry_id}",
    response_model=EntryResponse,
    summary="Fetch a single entry",
)
@limiter.limit("120/minute")
async def get_entry_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> EntryResponse:
    try:
        entry = await get_entry(db, user_id=user.id, entry_id=entry_id)
    except EntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entry not found",
        ) from exc
    return EntryResponse.model_validate(entry)


# ---------------------------------------------------------------------------
# Read — list
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[EntryResponse],
    summary="List entries (newest first)",
)
@limiter.limit("120/minute")
async def list_entries_endpoint(
    request: Request,
    start_date: date_type | None = Query(default=None, alias="start_date"),
    end_date: date_type | None = Query(default=None, alias="end_date"),
    limit: int = Query(default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[EntryResponse]:
    entries = await list_entries(
        db,
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [EntryResponse.model_validate(e) for e in entries]


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@router.patch(
    "/{entry_id}",
    response_model=EntryResponse,
    summary="Update an entry within the 7-day window",
)
@limiter.limit("60/minute")
async def update_entry_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    payload: EntryUpdate,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> EntryResponse:
    try:
        entry = await update_entry(db, user_id=user.id, entry_id=entry_id, payload=payload)
    except EntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entry not found",
        ) from exc
    except EntryReadOnlyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except EntryConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return EntryResponse.model_validate(entry)

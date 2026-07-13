"""Insight read endpoints (M3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.insight import (
    InsightEventWindowsResponse,
    InsightListResponse,
    InsightResponse,
)
from app.schemas.stats import (
    SymptomTagCooccurrenceResponse,
    TagClustersResponse,
    TagCooccurrenceRange,
    TagCooccurrenceResponse,
)
from app.services.insight_service import (
    DEFAULT_INSIGHT_LIST_LIMIT,
    DEFAULT_LATEST_INSIGHT_LIMIT,
    MAX_INSIGHT_LIST_LIMIT,
    MAX_LATEST_INSIGHT_LIMIT,
    InsightEventWindowsUnsupportedError,
    InsightNotFoundError,
    get_insight_event_windows,
    get_insight_maturity,
    list_insights,
    list_latest_insights,
)
from app.services.stats_service import get_symptom_tag_cooccurrence, get_tag_cooccurrence
from app.services.tag_cluster_service import get_tag_clusters

router = APIRouter()


def _cooccurrence_range_query(
    range: str = Query(default="90d", alias="range"),
) -> TagCooccurrenceRange:
    if range not in {"30d", "90d", "1y"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="range must be one of 30d, 90d, 1y",
        )
    return range  # type: ignore[return-value]


@router.get(
    "",
    response_model=InsightListResponse,
    summary="List generated insights",
)
@limiter.limit("120/minute")
async def list_insights_endpoint(
    request: Request,
    limit: int = Query(default=DEFAULT_INSIGHT_LIST_LIMIT, ge=1, le=MAX_INSIGHT_LIST_LIMIT),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> InsightListResponse:
    insights = await list_insights(db, user_id=user.id, limit=limit)
    insight_maturity = await get_insight_maturity(db, user_id=user.id)
    return InsightListResponse(
        insight_maturity=insight_maturity,
        insights=[InsightResponse.model_validate(insight) for insight in insights],
    )


@router.get(
    "/latest",
    response_model=InsightListResponse,
    summary="List latest generated insights by analytical subject",
)
@limiter.limit("120/minute")
async def list_latest_insights_endpoint(
    request: Request,
    limit: int = Query(default=DEFAULT_LATEST_INSIGHT_LIMIT, ge=1, le=MAX_LATEST_INSIGHT_LIMIT),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> InsightListResponse:
    insights = await list_latest_insights(db, user_id=user.id, limit=limit)
    insight_maturity = await get_insight_maturity(db, user_id=user.id)
    return InsightListResponse(
        insight_maturity=insight_maturity,
        insights=[InsightResponse.model_validate(insight) for insight in insights],
    )


@router.get(
    "/tag-cooccurrence",
    response_model=TagCooccurrenceResponse,
    summary="Tag co-occurrence pairs for heatmap visualisation",
)
@limiter.limit("120/minute")
async def get_tag_cooccurrence_endpoint(
    request: Request,
    range: TagCooccurrenceRange = Depends(_cooccurrence_range_query),
    min_count: int = Query(default=2, ge=1, le=100),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> TagCooccurrenceResponse:
    return await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_=range,
        min_count=min_count,
    )


@router.get(
    "/symptom-tag-cooccurrence",
    response_model=SymptomTagCooccurrenceResponse,
    summary="Symptom x tag co-occurrence cells for heatmap visualisation",
)
@limiter.limit("120/minute")
async def get_symptom_tag_cooccurrence_endpoint(
    request: Request,
    range: TagCooccurrenceRange = Depends(_cooccurrence_range_query),
    min_count: int = Query(default=3, ge=1, le=100),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> SymptomTagCooccurrenceResponse:
    return await get_symptom_tag_cooccurrence(
        db,
        user_id=user.id,
        range_=range,
        min_count=min_count,
    )


@router.get(
    "/tag-clusters",
    response_model=TagClustersResponse,
    summary="Tag groups that often appear together",
)
@limiter.limit("120/minute")
async def get_tag_clusters_endpoint(
    request: Request,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> TagClustersResponse:
    return await get_tag_clusters(db, user_id=user.id)


@router.get(
    "/{insight_id}/event-windows",
    response_model=InsightEventWindowsResponse,
    summary="Event-aligned onset dates and timeseries for an insight",
)
@limiter.limit("120/minute")
async def get_insight_event_windows_endpoint(
    request: Request,
    insight_id: uuid.UUID,
    range: TagCooccurrenceRange = Depends(_cooccurrence_range_query),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> InsightEventWindowsResponse:
    try:
        return await get_insight_event_windows(
            db,
            user_id=user.id,
            insight_id=insight_id,
            range_=range,
        )
    except InsightNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        ) from exc
    except InsightEventWindowsUnsupportedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Event windows are only available for tag and symptom insights",
        ) from exc

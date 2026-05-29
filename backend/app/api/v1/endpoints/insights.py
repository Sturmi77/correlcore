"""Insight read endpoints (M3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.insight import InsightListResponse, InsightResponse
from app.schemas.stats import TagCooccurrenceRange, TagCooccurrenceResponse
from app.services.insight_service import (
    DEFAULT_INSIGHT_LIST_LIMIT,
    DEFAULT_LATEST_INSIGHT_LIMIT,
    MAX_INSIGHT_LIST_LIMIT,
    MAX_LATEST_INSIGHT_LIMIT,
    get_insight_maturity,
    list_insights,
    list_latest_insights,
)
from app.services.stats_service import get_tag_cooccurrence

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

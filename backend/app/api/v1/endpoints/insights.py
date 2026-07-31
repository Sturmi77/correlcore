"""Insight read and regeneration endpoints (M3, M10.1)."""

from __future__ import annotations

import uuid
from datetime import date

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import (
    get_current_insight_trigger_admin,
    get_current_verified_user,
)
from app.core.rate_limit import limiter
from app.db.redis_client import get_redis
from app.db.session import get_session
from app.models.insight import Insight, InsightType
from app.models.insight_dismissal import InsightDismissal
from app.models.user import User
from app.schemas.insight import (
    InsightDigestItemResponse,
    InsightDigestResponse,
    InsightDismissalCreate,
    InsightDismissalListResponse,
    InsightDismissalResponse,
    InsightEventWindowsResponse,
    InsightHistoryItem,
    InsightHistoryResponse,
    InsightListResponse,
    InsightRegenerateResponse,
    InsightResponse,
    InsightTriggerResponse,
)
from app.schemas.stats import (
    SymptomTagCooccurrenceResponse,
    TagClustersResponse,
    TagCooccurrenceRange,
    TagCooccurrenceResponse,
)
from app.services.insight_digest import (
    DigestDisabledError,
    DigestNotAvailableError,
    build_push_payload,
    get_latest_weekly_digest,
)
from app.services.insight_dismissal_service import (
    InsightDismissalNotFoundError,
    InsightDismissalView,
    create_insight_dismissal,
    delete_insight_dismissal,
    delete_insight_dismissal_by_insight_id,
    list_insight_dismissals,
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
    list_insight_history,
    list_insights,
    list_latest_insights,
)
from app.services.insight_worker_service import (
    AnalyticsDisabledError,
    InsightJobNotFoundError,
    regenerate_insights_for_user,
    try_acquire_regenerate_slot,
)
from app.services.stats_service import get_symptom_tag_cooccurrence, get_tag_cooccurrence
from app.services.tag_cluster_service import get_tag_clusters
from app.workers.analytics import run_insights_once

router = APIRouter()


def _cooccurrence_range_query(
    range: str = Query(default="90d", alias="range"),
) -> TagCooccurrenceRange:
    if range not in {"7d", "30d", "90d", "1y"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="range must be one of 7d, 30d, 90d, 1y",
        )
    return range  # type: ignore[return-value]


@router.get(
    "/digest/latest",
    response_model=InsightDigestResponse,
    summary="Latest weekly insight digest",
)
@limiter.limit("60/minute")
async def get_latest_digest_endpoint(
    request: Request,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> InsightDigestResponse:
    try:
        digest = await get_latest_weekly_digest(db, user_id=user.id)
    except DigestDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Weekly insight digest is disabled for this account",
        ) from exc
    except DigestNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not enough recent insights for a weekly digest",
        ) from exc

    push = build_push_payload(digest)
    return InsightDigestResponse(
        week_start=digest.week_start,
        week_end=digest.week_end,
        insight_count=digest.insight_count,
        insights=[
            InsightDigestItemResponse(
                id=item.id,
                insight_type=(
                    item.insight_type
                    if isinstance(item.insight_type, InsightType)
                    else InsightType(item.insight_type)
                ),
                metric=item.metric,
                effect_size=item.effect_size,
                confidence=item.confidence,
                statement=item.statement,
            )
            for item in digest.insights
        ],
        push_title=push["title"],
        push_body=push["body"],
    )


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
    "/history",
    response_model=InsightHistoryResponse,
    summary="Chronological insight history for timeline / archive",
)
@limiter.limit("60/minute")
async def list_insight_history_endpoint(
    request: Request,
    status_filter: str = Query(default="all", alias="status"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=DEFAULT_INSIGHT_LIST_LIMIT, ge=1, le=MAX_INSIGHT_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> InsightHistoryResponse:
    if status_filter not in {"active", "dismissed", "all"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be one of active, dismissed, all",
        )
    entries, total = await list_insight_history(
        db,
        user_id=user.id,
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return InsightHistoryResponse(
        insights=[
            InsightHistoryItem(
                **InsightResponse.model_validate(entry.insight).model_dump(),
                visibility=entry.visibility,  # type: ignore[arg-type]
                subject_key=entry.subject_key,
                first_seen_on=entry.first_seen_on,
                last_seen_on=entry.last_seen_on,
                observation_count=entry.observation_count,
            )
            for entry in entries
        ],
        total=total,
        limit=limit,
        offset=offset,
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


def _dismissal_response(
    view_or_row: InsightDismissalView | InsightDismissal,
    insight: Insight | None = None,
) -> InsightDismissalResponse:
    if isinstance(view_or_row, InsightDismissalView):
        row = view_or_row.dismissal
        insight = view_or_row.insight
    else:
        row = view_or_row
    return InsightDismissalResponse(
        id=row.id,
        subject_key=row.subject_key,
        insight_id=row.insight_id,
        dismissed_at=row.dismissed_at,
        created_at=row.created_at,
        insight=InsightResponse.model_validate(insight) if insight is not None else None,
    )


@router.get(
    "/dismissals",
    response_model=InsightDismissalListResponse,
    summary="List subject-stable hidden insights",
)
@limiter.limit("60/minute")
async def list_insight_dismissals_endpoint(
    request: Request,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> InsightDismissalListResponse:
    views = await list_insight_dismissals(db, user_id=user.id)
    return InsightDismissalListResponse(dismissals=[_dismissal_response(view) for view in views])


@router.post(
    "/dismissals",
    response_model=InsightDismissalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Hide an insight by subject-stable key",
)
@limiter.limit("60/minute")
async def create_insight_dismissal_endpoint(
    request: Request,
    payload: InsightDismissalCreate,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> InsightDismissalResponse:
    try:
        row = await create_insight_dismissal(db, user_id=user.id, insight_id=payload.insight_id)
    except InsightNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        ) from exc
    await db.refresh(row)
    return _dismissal_response(row)


@router.delete(
    "/dismissals/by-insight/{insight_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Undo hide for the subject of an insight id",
)
@limiter.limit("60/minute")
async def delete_insight_dismissal_by_insight_endpoint(
    request: Request,
    insight_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await delete_insight_dismissal_by_insight_id(db, user_id=user.id, insight_id=insight_id)


@router.delete(
    "/dismissals/{dismissal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Undo a subject-stable insight hide",
)
@limiter.limit("60/minute")
async def delete_insight_dismissal_endpoint(
    request: Request,
    dismissal_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await delete_insight_dismissal(db, user_id=user.id, dismissal_id=dismissal_id)
    except InsightDismissalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight dismissal not found",
        ) from exc


@router.post(
    "/regenerate",
    response_model=InsightRegenerateResponse,
    summary="Regenerate insights and tag clusters for the current user",
)
@limiter.limit("10/minute")
async def regenerate_insights_endpoint(
    request: Request,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> InsightRegenerateResponse:
    if not await try_acquire_regenerate_slot(user_id=user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Insight regeneration is limited to once per hour",
        )
    try:
        result = await regenerate_insights_for_user(
            db,
            user_id=user.id,
            trigger_source="user_regenerate",
        )
        await db.commit()
    except AnalyticsDisabledError as exc:
        await db.rollback()
        await redis.delete(f"insight:regenerate:{user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics processing is disabled for this account",
        ) from exc
    except InsightJobNotFoundError as exc:
        await db.rollback()
        await redis.delete(f"insight:regenerate:{user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encryption key found for insight generation",
        ) from exc

    return InsightRegenerateResponse(
        generated_for_date=result.generated_for_date,
        insight_count=result.insight_count,
        tag_clusters_status=result.tag_clusters_status,
        trigger_source=result.trigger_source,
    )


@router.post(
    "/trigger",
    response_model=InsightTriggerResponse,
    summary="Run scheduled insight generation for all eligible users (admin)",
)
@limiter.limit("10/minute")
async def trigger_insights_endpoint(
    request: Request,
    _admin: User = Depends(get_current_insight_trigger_admin),
) -> InsightTriggerResponse:
    summary = await run_insights_once(trigger_source="admin_trigger")
    return InsightTriggerResponse(
        eligible_users=summary.eligible_users,
        processed_users=summary.processed_users,
        failed_users=summary.failed_users,
        generated_insights=summary.generated_insights,
    )


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

"""Habit statistics endpoints for M5."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.habit import HabitListResponse, HabitStatsResponse, HabitWindow
from app.services.habit_service import HabitNotFoundError, get_habit_stats, list_habit_stats

router = APIRouter()


def _window_query(window: int = Query(default=28)) -> HabitWindow:
    if window not in {7, 14, 28, 90}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="window must be one of 7, 14, 28, 90",
        )
    return window  # type: ignore[return-value]


@router.get("", response_model=HabitListResponse, summary="List habit statistics")
@limiter.limit("120/minute")
async def list_habits_endpoint(
    request: Request,
    window: HabitWindow = Depends(_window_query),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> HabitListResponse:
    return await list_habit_stats(db, user_id=user.id, window=window)


@router.get(
    "/{tag_id}/stats",
    response_model=HabitStatsResponse,
    summary="Return habit statistics for one tag",
)
@limiter.limit("120/minute")
async def get_habit_stats_endpoint(
    request: Request,
    tag_id: uuid.UUID,
    window: HabitWindow = Depends(_window_query),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> HabitStatsResponse:
    try:
        return await get_habit_stats(db, user_id=user.id, tag_id=tag_id, window=window)
    except HabitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="habit not found",
        ) from exc

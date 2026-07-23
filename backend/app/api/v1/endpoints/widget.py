"""Homescreen widget endpoints (M11 Sprint 4)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.widget import WidgetSummaryResponse
from app.services.widget_service import get_widget_summary

router = APIRouter()


@router.get(
    "/summary",
    response_model=WidgetSummaryResponse,
    summary="Return compact summary for the Android homescreen widget",
)
@limiter.limit("120/minute")
async def get_widget_summary_endpoint(
    request: Request,
    tz: Annotated[
        str | None,
        Query(
            max_length=64,
            description=(
                "Device IANA timezone (e.g. America/Los_Angeles). Resolves "
                "'today' the same way the entry flow does; omitted or unknown "
                "values fall back to UTC."
            ),
        ),
    ] = None,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> WidgetSummaryResponse:
    return await get_widget_summary(db, user_id=user.id, tz=tz)

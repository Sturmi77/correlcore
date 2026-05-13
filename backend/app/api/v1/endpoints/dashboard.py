"""Dashboard summary endpoints."""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import get_dashboard_summary

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Return dashboard insight confidence summary",
)
@limiter.limit("120/minute")
async def get_dashboard_summary_endpoint(
    request: Request,
    as_of: date_type | None = Query(default=None, alias="as_of"),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> DashboardSummaryResponse:
    return await get_dashboard_summary(db, user_id=user.id, as_of=as_of)

"""Feature-flagged developer diagnostics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.schemas.dev import DevInfoResponse
from app.services.dev_service import build_dev_info

router = APIRouter()


def require_dev_view_enabled() -> None:
    if not settings.DEV_VIEW_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get(
    "/info",
    response_model=DevInfoResponse,
    summary="Developer runtime and infrastructure diagnostics",
)
async def dev_info(
    _flag: None = Depends(require_dev_view_enabled),
    _user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> DevInfoResponse:
    return await build_dev_info(db)

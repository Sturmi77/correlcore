"""Sync endpoints — offline push/pull (M4.1 Sprint 2, Issue #10)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.sync import SyncPullResponse, SyncPushRequest, SyncPushResponse
from app.services.sync_service import (
    DEFAULT_PULL_LIMIT,
    MAX_PULL_LIMIT,
    SyncBadRequestError,
    pull_changes,
    push_changes,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/push",
    response_model=SyncPushResponse,
    summary="Upload offline client changes",
)
@limiter.limit("60/minute")
async def sync_push(
    request: Request,
    request_body: SyncPushRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> SyncPushResponse:
    try:
        return await push_changes(db, user_id=current_user.id, request=request_body)
    except SyncBadRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/pull",
    response_model=SyncPullResponse,
    summary="Download server changes since cursor",
)
@limiter.limit("120/minute")
async def sync_pull(
    request: Request,
    since: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_PULL_LIMIT, ge=1, le=MAX_PULL_LIMIT),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> SyncPullResponse:
    try:
        return await pull_changes(db, user_id=current_user.id, since=since, limit=limit)
    except SyncBadRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

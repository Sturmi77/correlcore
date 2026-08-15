"""Admin console — user management (#677).

Every route is gated by ``require_admin`` (403 for non-admins). Destructive and
credential-adjacent actions (disable/enable/delete/password-reset) are recorded
in ``admin_audit_log``. Admins cannot disable or delete their own account (so an
instance can never be left without an operator by accident).
"""

from __future__ import annotations

import uuid

import redis.asyncio as aioredis
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import require_admin
from app.core.rate_limit import limiter
from app.db.redis_client import TokenStore, get_redis
from app.db.session import get_session
from app.models.admin_audit_log import (
    ADMIN_ACTION_DELETE_USER,
    ADMIN_ACTION_DISABLE_USER,
    ADMIN_ACTION_ENABLE_USER,
    ADMIN_ACTION_TRIGGER_PASSWORD_RESET,
)
from app.models.user import User
from app.schemas.admin import (
    AdminMessageResponse,
    AdminSetActiveRequest,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserListResponse,
)
from app.services import admin_service
from app.services.auth_service import request_password_reset
from app.services.email_service import send_password_reset_email
from app.services.user_service import purge_user_account

router = APIRouter()


async def _require_target(db: AsyncSession, user_id: uuid.UUID) -> tuple[User, int]:
    found = await admin_service.get_user_with_entry_count(db, user_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return found


def _forbid_self(admin: User, target: User) -> None:
    if target.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot perform this action on their own account.",
        )


@router.get("/users", response_model=AdminUserListResponse, summary="List/search users")
async def list_users_endpoint(
    query: str | None = Query(default=None, max_length=255),
    active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=admin_service.MAX_ADMIN_PAGE),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> AdminUserListResponse:
    users, total = await admin_service.list_users(
        db, query=query, active=active, limit=limit, offset=offset
    )
    return AdminUserListResponse(
        items=[AdminUserListItem.model_validate(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail, summary="User detail")
async def get_user_endpoint(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> AdminUserDetail:
    target, entry_count = await _require_target(db, user_id)
    return AdminUserDetail.model_validate(target).model_copy(update={"entry_count": entry_count})


@router.patch(
    "/users/{user_id}/active",
    response_model=AdminUserDetail,
    summary="Disable / enable a user (reversible)",
)
async def set_user_active_endpoint(
    user_id: uuid.UUID,
    body: AdminSetActiveRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> AdminUserDetail:
    target, entry_count = await _require_target(db, user_id)
    _forbid_self(admin, target)
    await admin_service.set_user_active(db, target, is_active=body.is_active)
    await admin_service.record_admin_action(
        db,
        actor=admin,
        action=ADMIN_ACTION_ENABLE_USER if body.is_active else ADMIN_ACTION_DISABLE_USER,
        target=target,
    )
    return AdminUserDetail.model_validate(target).model_copy(update={"entry_count": entry_count})


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Hard-delete a user (DSGVO Art. 17)",
)
@limiter.limit("10/minute")
async def delete_user_endpoint(
    request: Request,  # noqa: ARG001 — slowapi reads the rate-limit key off it
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> Response:
    target, _ = await _require_target(db, user_id)
    _forbid_self(admin, target)
    # Audit BEFORE the row is gone (target_email must still be readable; the
    # audit row itself carries no FK and survives the deletion).
    await admin_service.record_admin_action(
        db, actor=admin, action=ADMIN_ACTION_DELETE_USER, target=target
    )
    await purge_user_account(db, TokenStore(redis), target)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users/{user_id}/password-reset",
    response_model=AdminMessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send the user a password-reset email",
)
@limiter.limit("10/minute")
async def trigger_password_reset_endpoint(
    request: Request,  # noqa: ARG001 — slowapi reads the rate-limit key off it
    user_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> AdminMessageResponse:
    target, _ = await _require_target(db, user_id)
    result = await request_password_reset(db, target.email)
    if result is None:
        # request_password_reset only issues for active + verified users.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User must be active and verified to receive a reset link.",
        )
    user, plaintext_token = result
    background_tasks.add_task(
        send_password_reset_email,
        to_email=user.email,
        display_name=user.display_name,
        token=plaintext_token,
    )
    await admin_service.record_admin_action(
        db, actor=admin, action=ADMIN_ACTION_TRIGGER_PASSWORD_RESET, target=target
    )
    return AdminMessageResponse(message="Password-reset email sent.")

"""Device push-token endpoints (M11 Sprint 5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.device_token import (
    DeviceTokenDelete,
    DeviceTokenResponse,
    DeviceTokenUpsert,
    PushTestResponse,
)
from app.services.device_token_service import (
    DeviceTokenNotFoundError,
    FcmNotConfiguredError,
    delete_device_token,
    fcm_is_configured,
    list_device_tokens,
    send_check_in_reminder_to_user,
    to_response,
    upsert_device_token,
)
from app.services.push_copy import CHECK_IN_REMINDER_BODY

router = APIRouter()


@router.put(
    "/push-token",
    response_model=DeviceTokenResponse,
    summary="Register or refresh a device push token",
)
@limiter.limit("30/minute")
async def put_push_token(
    request: Request,
    payload: DeviceTokenUpsert,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> DeviceTokenResponse:
    row = await upsert_device_token(db, user_id=user.id, payload=payload)
    return to_response(row)


@router.delete(
    "/push-token",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unregister a device push token",
)
@limiter.limit("30/minute")
async def delete_push_token(
    request: Request,
    payload: DeviceTokenDelete,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await delete_device_token(db, user_id=user.id, token=payload.token)
    except DeviceTokenNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/push-tokens",
    response_model=list[DeviceTokenResponse],
    summary="List registered push tokens for the current user",
)
@limiter.limit("60/minute")
async def get_push_tokens(
    request: Request,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[DeviceTokenResponse]:
    rows = await list_device_tokens(db, user_id=user.id)
    return [to_response(row) for row in rows]


@router.post(
    "/push-test",
    response_model=PushTestResponse,
    summary="Send a neutral check-in reminder to the caller's FCM tokens",
)
@limiter.limit("5/hour")
async def post_push_test(
    request: Request,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> PushTestResponse:
    """QA helper for Sprint 5 exit — requires FCM credentials on the API."""

    if not fcm_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FCM is not configured on this API (selfhost / sideload builds omit it)",
        )
    try:
        sent, skipped = await send_check_in_reminder_to_user(db, user_id=user.id)
    except FcmNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if sent == 0 and skipped == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No FCM tokens registered for this user",
        )
    return PushTestResponse(
        sent=sent,
        skipped=skipped,
        message=CHECK_IN_REMINDER_BODY,
    )

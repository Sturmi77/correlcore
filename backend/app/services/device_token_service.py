"""Device push-token registration and FCM send helpers (M11 Sprint 5)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.device_token import DeviceToken, PushProvider
from app.schemas.device_token import DeviceTokenResponse, DeviceTokenUpsert
from app.services.push_copy import CHECK_IN_REMINDER_BODY, CHECK_IN_REMINDER_TITLE

logger = logging.getLogger(__name__)


class DeviceTokenError(Exception):
    """Base class for device-token errors."""


class DeviceTokenNotFoundError(DeviceTokenError):
    """Token does not exist for this user."""


class FcmNotConfiguredError(DeviceTokenError):
    """FCM credentials / optional dependency are missing."""


def fcm_is_configured() -> bool:
    """True when SaaS/staging may attempt FCM sends."""

    if not settings.FCM_ENABLED:
        return False
    return bool(settings.FCM_CREDENTIALS_JSON.strip() or settings.GOOGLE_APPLICATION_CREDENTIALS.strip())


def to_response(row: DeviceToken) -> DeviceTokenResponse:
    return DeviceTokenResponse(
        id=row.id,
        provider=row.provider,  # type: ignore[arg-type]
        platform=row.platform,  # type: ignore[arg-type]
        device_label=row.device_label,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_seen_at=row.last_seen_at,
    )


async def upsert_device_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: DeviceTokenUpsert,
) -> DeviceToken:
    now = datetime.now(UTC)
    result = await db.execute(select(DeviceToken).where(DeviceToken.token == payload.token))
    row = result.scalar_one_or_none()
    if row is None:
        row = DeviceToken(
            user_id=user_id,
            token=payload.token,
            provider=payload.provider,
            platform=payload.platform,
            device_label=payload.device_label,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        db.add(row)
    else:
        row.user_id = user_id
        row.provider = payload.provider
        row.platform = payload.platform
        row.device_label = payload.device_label
        row.updated_at = now
        row.last_seen_at = now
    await db.flush()
    await db.refresh(row)
    # Never log the raw token — only id / user / provider.
    logger.info(
        "device_token_upserted",
        extra={
            "user_id": str(user_id),
            "device_token_id": str(row.id),
            "provider": row.provider,
            "platform": row.platform,
        },
    )
    return row


async def delete_device_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    token: str,
) -> None:
    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.token == token,
            DeviceToken.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise DeviceTokenNotFoundError("push token not found")
    await db.delete(row)
    await db.flush()
    logger.info(
        "device_token_deleted",
        extra={"user_id": str(user_id), "device_token_id": str(row.id)},
    )


async def list_device_tokens(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[DeviceToken]:
    result = await db.execute(
        select(DeviceToken)
        .where(DeviceToken.user_id == user_id)
        .order_by(DeviceToken.updated_at.desc())
    )
    return list(result.scalars().all())


def _init_firebase_app() -> None:
    """Lazy-init firebase-admin once per process."""

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError as exc:  # pragma: no cover - optional extra
        raise FcmNotConfiguredError(
            "firebase-admin is not installed (pip install correlcore-backend[fcm])"
        ) from exc

    if firebase_admin._apps:  # type: ignore[attr-defined]
        return

    creds_json = settings.FCM_CREDENTIALS_JSON.strip()
    if creds_json:
        import json

        cred = credentials.Certificate(json.loads(creds_json))
        firebase_admin.initialize_app(cred)
        return

    path = settings.GOOGLE_APPLICATION_CREDENTIALS.strip()
    if path:
        cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred)
        return

    raise FcmNotConfiguredError("FCM credentials are not configured")


def send_fcm_message(
    *,
    token: str,
    title: str,
    body: str,
) -> bool:
    """Send one FCM data+notification message. Returns True on success."""

    if not fcm_is_configured():
        raise FcmNotConfiguredError("FCM is disabled or credentials missing")

    _init_firebase_app()
    from firebase_admin import messaging

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
        android=messaging.AndroidConfig(priority="normal"),
    )
    messaging.send(message)
    return True


async def send_check_in_reminder_to_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> tuple[int, int]:
    """Send the neutral check-in reminder to the user's FCM tokens.

    Returns ``(sent, skipped)``. Raises :class:`FcmNotConfiguredError` when
    the SaaS FCM path is unavailable. UnifiedPush tokens are skipped here
    (M4.2 / selfhost).
    """

    if not fcm_is_configured():
        raise FcmNotConfiguredError("FCM is disabled or credentials missing")

    tokens = await list_device_tokens(db, user_id=user_id)
    fcm_tokens = [row for row in tokens if row.provider == PushProvider.FCM]
    if not fcm_tokens:
        return 0, 0

    sent = 0
    skipped = 0
    for row in fcm_tokens:
        try:
            send_fcm_message(
                token=row.token,
                title=CHECK_IN_REMINDER_TITLE,
                body=CHECK_IN_REMINDER_BODY,
            )
            sent += 1
            row.last_seen_at = datetime.now(UTC)
        except Exception:
            skipped += 1
            logger.warning(
                "fcm_send_failed",
                extra={
                    "user_id": str(user_id),
                    "device_token_id": str(row.id),
                },
            )
    await db.flush()
    return sent, skipped

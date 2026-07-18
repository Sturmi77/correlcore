"""Tests for device push-token API (M11 Sprint 5)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.device_token import DeviceToken, PushPlatform, PushProvider
from app.models.user import User
from app.schemas.device_token import DeviceTokenUpsert
from app.services.device_token_service import (
    DeviceTokenNotFoundError,
    FcmNotConfiguredError,
    delete_device_token,
    fcm_is_configured,
    send_check_in_reminder_to_user,
    upsert_device_token,
)
from app.services.push_copy import CHECK_IN_REMINDER_BODY
from tests.conftest import make_user


def test_check_in_copy_is_neutral() -> None:
    assert "streak" not in CHECK_IN_REMINDER_BODY.lower()
    assert "mood" not in CHECK_IN_REMINDER_BODY.lower()
    assert CHECK_IN_REMINDER_BODY == "Time for your daily check-in."


def test_fcm_is_configured_requires_flag_and_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.device_token_service.settings.FCM_ENABLED", False)
    monkeypatch.setattr("app.services.device_token_service.settings.FCM_CREDENTIALS_JSON", "{}")
    assert fcm_is_configured() is False

    monkeypatch.setattr("app.services.device_token_service.settings.FCM_ENABLED", True)
    monkeypatch.setattr("app.services.device_token_service.settings.FCM_CREDENTIALS_JSON", "")
    monkeypatch.setattr(
        "app.services.device_token_service.settings.GOOGLE_APPLICATION_CREDENTIALS",
        "",
    )
    assert fcm_is_configured() is False

    monkeypatch.setattr(
        "app.services.device_token_service.settings.FCM_CREDENTIALS_JSON",
        '{"type":"service_account"}',
    )
    assert fcm_is_configured() is True


@pytest.mark.asyncio
async def test_upsert_device_token_creates_then_updates() -> None:
    user = make_user()
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    empty = MagicMock()
    empty.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=empty)

    created = await upsert_device_token(
        db,
        user_id=user.id,
        payload=DeviceTokenUpsert(
            token="fcm-token-abcdef",
            provider="fcm",
            platform="android",
        ),
    )
    assert isinstance(created, DeviceToken)
    assert created.user_id == user.id
    assert created.token == "fcm-token-abcdef"
    db.add.assert_called_once()

    existing_row = created
    found = MagicMock()
    found.scalar_one_or_none.return_value = existing_row
    db.execute = AsyncMock(return_value=found)

    updated = await upsert_device_token(
        db,
        user_id=user.id,
        payload=DeviceTokenUpsert(
            token="fcm-token-abcdef",
            provider="fcm",
            platform="android",
            device_label="Pixel",
        ),
    )
    assert updated is existing_row
    assert updated.device_label == "Pixel"
    assert updated.user_id == user.id


@pytest.mark.asyncio
async def test_delete_device_token_missing_raises() -> None:
    user = make_user()
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(DeviceTokenNotFoundError):
        await delete_device_token(db, user_id=user.id, token="missing-token-xx")


@pytest.mark.asyncio
async def test_send_check_in_reminder_requires_fcm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.device_token_service.fcm_is_configured", lambda: False)
    db = MagicMock()
    with pytest.raises(FcmNotConfiguredError):
        await send_check_in_reminder_to_user(db, user_id=make_user().id)


@pytest.mark.asyncio
async def test_put_push_token_endpoint(
    async_client: AsyncClient,
    user: User,
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.devices.upsert_device_token",
            new_callable=AsyncMock,
        ) as upsert:
            row = DeviceToken(
                user_id=user.id,
                token="fcm-token-abcdef",
                provider=PushProvider.FCM,
                platform=PushPlatform.ANDROID,
            )
            # Populate timestamps for response model
            from datetime import UTC, datetime

            now = datetime.now(UTC)
            row.id = user.id
            row.created_at = now
            row.updated_at = now
            row.last_seen_at = now
            upsert.return_value = row

            response = await async_client.put(
                "/api/v1/devices/push-token",
                json={
                    "token": "fcm-token-abcdef",
                    "provider": "fcm",
                    "platform": "android",
                },
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "fcm"
    assert body["platform"] == "android"
    assert "token" not in body


@pytest.mark.asyncio
async def test_push_test_returns_503_when_fcm_off(
    async_client: AsyncClient,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def override() -> User:
        return user

    monkeypatch.setattr("app.api.v1.endpoints.devices.fcm_is_configured", lambda: False)
    app.dependency_overrides[get_current_verified_user] = override
    try:
        response = await async_client.post(
            "/api/v1/devices/push-test",
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_devices_require_auth(async_client: AsyncClient) -> None:
    response = await async_client.put(
        "/api/v1/devices/push-token",
        json={"token": "fcm-token-abcdef", "provider": "fcm", "platform": "android"},
    )
    assert response.status_code in (401, 403)

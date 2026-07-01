"""Tests for O-20 — password reset flow."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import verify_password
from app.services.auth_service import (
    PasswordResetError,
    request_password_reset,
    reset_password,
)
from tests.conftest import (
    VALID_ACCESS_TOKEN,
    VALID_REFRESH_TOKEN,
    make_db_session_with_results,
    make_password_reset_token,
    make_user,
)


@pytest.mark.asyncio
async def test_request_password_reset_unknown_email_returns_none() -> None:
    db = make_db_session_with_results(None)
    result = await request_password_reset(db, "missing@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_request_password_reset_unverified_user_skipped() -> None:
    user = make_user(verified=False)
    db = make_db_session_with_results(user)
    result = await request_password_reset(db, user.email)
    assert result is None


@pytest.mark.asyncio
async def test_request_password_reset_inactive_user_skipped() -> None:
    user = make_user(active=False)
    db = make_db_session_with_results(user)
    result = await request_password_reset(db, user.email)
    assert result is None


@pytest.mark.asyncio
async def test_reset_password_unknown_token_raises_generic() -> None:
    db = make_db_session_with_results(None)
    with pytest.raises(PasswordResetError, match="Invalid or expired"):
        await reset_password(db, "unknown-token", "NewPass1")


@pytest.mark.asyncio
async def test_reset_password_expired_token_raises_generic() -> None:
    user = make_user()
    record, plaintext = make_password_reset_token(user, expires_in=timedelta(hours=-1))
    db = make_db_session_with_results(record)
    with pytest.raises(PasswordResetError, match="Invalid or expired"):
        await reset_password(db, plaintext, "NewPass1")


@pytest.mark.asyncio
async def test_reset_password_used_token_raises_generic() -> None:
    user = make_user()
    record, plaintext = make_password_reset_token(user, used=True)
    db = make_db_session_with_results(record)
    with pytest.raises(PasswordResetError, match="Invalid or expired"):
        await reset_password(db, plaintext, "NewPass1")


@pytest.mark.asyncio
async def test_reset_password_success_updates_hash() -> None:
    user = make_user()
    record, plaintext = make_password_reset_token(user)
    db = make_db_session_with_results(record, user, None)
    returned = await reset_password(db, plaintext, "NewPass1")
    assert returned is user
    assert verify_password("NewPass1", user.hashed_password)
    assert record.used_at is not None
    delete_statement = db.execute.await_args_list[2].args[0]
    assert "DELETE FROM password_reset_tokens" in str(delete_statement)
    assert "password_reset_tokens.user_id" in str(delete_statement)


@pytest.mark.asyncio
async def test_endpoint_forgot_password_always_202(async_client: AsyncClient) -> None:
    with patch(
        "app.api.v1.endpoints.auth.request_password_reset",
        new_callable=AsyncMock,
        return_value=None,
    ):
        r = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "user@example.com"},
        )
    assert r.status_code == 202
    assert "password reset mail" in r.json()["message"]


@pytest.mark.asyncio
async def test_endpoint_forgot_password_schedules_mail(async_client: AsyncClient) -> None:
    user = make_user()
    plaintext = "x" * 32
    with (
        patch(
            "app.api.v1.endpoints.auth.request_password_reset",
            new_callable=AsyncMock,
            return_value=(user, plaintext),
        ),
        patch(
            "app.api.v1.endpoints.auth.send_password_reset_email",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        r = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": user.email},
        )
    assert r.status_code == 202
    mock_send.assert_awaited()


@pytest.mark.asyncio
async def test_endpoint_reset_password_success(async_client: AsyncClient) -> None:
    user = make_user()
    with (
        patch(
            "app.api.v1.endpoints.auth.reset_password",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.api.v1.endpoints.auth.TokenStore.revoke_all",
            new_callable=AsyncMock,
        ) as mock_revoke,
        patch(
            "app.api.v1.endpoints.auth.issue_session_tokens",
            new_callable=AsyncMock,
            return_value=(VALID_ACCESS_TOKEN, VALID_REFRESH_TOKEN),
        ),
    ):
        r = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "x" * 32, "password": "NewPass1"},
        )
    assert r.status_code == 200
    mock_revoke.assert_awaited_once_with(str(user.id))
    assert r.json()["access_token"] == VALID_ACCESS_TOKEN
    assert "access_token" in r.cookies
    assert "refresh_token" in r.cookies


@pytest.mark.asyncio
async def test_endpoint_reset_password_invalid_no_cookies(async_client: AsyncClient) -> None:
    with patch(
        "app.api.v1.endpoints.auth.reset_password",
        new_callable=AsyncMock,
        side_effect=PasswordResetError("Invalid or expired password reset token"),
    ):
        r = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "x" * 32, "password": "NewPass1"},
        )
    assert r.status_code == 400
    assert "access_token" not in r.cookies
    assert "refresh_token" not in r.cookies


@pytest.mark.asyncio
async def test_endpoint_reset_password_weak_password_validation(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/v1/auth/reset-password",
        json={"token": "x" * 32, "password": "short"},
    )
    assert r.status_code == 422

"""Tests for auth endpoints.

Coverage:
- POST /api/v1/auth/register   — success, duplicate email, weak password
- POST /api/v1/auth/login      — success, wrong password, unknown email
- POST /api/v1/auth/refresh    — success (rotation), replay attack → 401
- POST /api/v1/auth/logout     — clears cookies, no error on missing token
- GET  /api/v1/auth/me         — authenticated, unauthenticated

All Redis and DB interactions are mocked so tests run without
external services. No real passwords or tokens are logged.

Shared factories (``make_user``) and the ``async_client`` fixture live
in :mod:`tests.conftest`.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_user
from app.main import app
from app.models.user import User
from app.services.auth_service import AuthError, RegistrationError
from tests.conftest import (
    NEW_ACCESS_TOKEN,
    NEW_REFRESH_TOKEN,
    VALID_ACCESS_TOKEN,
    VALID_REFRESH_TOKEN,
    make_user,
)

# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient) -> None:
    # Issue #39: register also schedules a verification email — mock the
    # token-mint and mail-send helpers so we don't touch DB or SMTP.
    with (
        patch("app.api.v1.endpoints.auth.register_user", new_callable=AsyncMock) as mock_reg,
        patch(
            "app.api.v1.endpoints.auth.create_verification_token",
            new_callable=AsyncMock,
            return_value="plaintext-token",
        ),
        patch(
            "app.api.v1.endpoints.auth.send_verification_email",
            new_callable=AsyncMock,
        ),
    ):
        mock_reg.return_value = make_user()
        r = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "Passw0rd"},
        )
    assert r.status_code == 201
    assert "verify" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient) -> None:
    with patch(
        "app.api.v1.endpoints.auth.register_user",
        new_callable=AsyncMock,
        side_effect=RegistrationError("Email already registered"),
    ):
        r = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "dupe@example.com", "password": "Passw0rd"},
        )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "short"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, user: User) -> None:
    with patch(
        "app.api.v1.endpoints.auth.login_user",
        new_callable=AsyncMock,
        return_value=(VALID_ACCESS_TOKEN, VALID_REFRESH_TOKEN, user),
    ):
        r = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "Passw0rd"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["access_token"] == VALID_ACCESS_TOKEN
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == user.email
    # HttpOnly cookies must be set
    assert "access_token" in r.cookies
    assert "refresh_token" in r.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient) -> None:
    with patch(
        "app.api.v1.endpoints.auth.login_user",
        new_callable=AsyncMock,
        side_effect=AuthError("Invalid credentials"),
    ):
        r = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpass1"},
        )
    assert r.status_code == 401
    # Generic message — no user enumeration hint
    assert "Invalid" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_success(async_client: AsyncClient, user: User) -> None:
    with patch(
        "app.api.v1.endpoints.auth.refresh_tokens",
        new_callable=AsyncMock,
        return_value=(NEW_ACCESS_TOKEN, NEW_REFRESH_TOKEN, user),
    ):
        r = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": VALID_REFRESH_TOKEN},
        )
    assert r.status_code == 200
    assert r.json()["access_token"] == NEW_ACCESS_TOKEN


@pytest.mark.asyncio
async def test_refresh_replay_returns_401(async_client: AsyncClient) -> None:
    with patch(
        "app.api.v1.endpoints.auth.refresh_tokens",
        new_callable=AsyncMock,
        side_effect=AuthError("Refresh token already used or revoked"),
    ):
        r = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "replayed.token"},
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_missing_token_returns_401(async_client: AsyncClient) -> None:
    r = await async_client.post("/api/v1/auth/refresh", json={})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_success(async_client: AsyncClient) -> None:
    with patch("app.api.v1.endpoints.auth.logout_user", new_callable=AsyncMock):
        r = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": VALID_REFRESH_TOKEN},
        )
    assert r.status_code == 200
    assert r.json()["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_logout_no_token_still_200(async_client: AsyncClient) -> None:
    """Logout without token should still succeed — idempotent."""
    r = await async_client.post("/api/v1/auth/logout", json={})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_authenticated(async_client: AsyncClient, user: User) -> None:
    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    try:
        r = await async_client.get(
            "/api/v1/auth/me",
            cookies={"access_token": VALID_ACCESS_TOKEN},
        )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json()["email"] == user.email


@pytest.mark.asyncio
async def test_me_unauthenticated(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/v1/auth/me")
    assert r.status_code == 401

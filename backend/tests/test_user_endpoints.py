"""Endpoint tests for /api/v1/user/me (Issue #66, SA-4).

Covers:

- 401 when no token is sent.
- 401 when the password in the body is wrong.
- 204 on success, with auth cookies cleared in the response.
- DB DELETE statement is issued against ``users`` and refresh tokens
  are revoked in Redis (both via mocks).
- Both verified and unverified users can exercise their right to be
  forgotten — Art. 17 must not be gated on email verification.
- Body validation: missing/short password → 422.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_user
from app.core.security import hash_password
from app.db.redis_client import get_redis
from app.db.session import get_session
from app.main import app
from app.models.user import User
from app.services.user_service import UserDeletionError
from tests.conftest import VALID_ACCESS_TOKEN, make_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _override_user(user: User) -> None:
    """Bind ``get_current_user`` to ``user`` for the duration of a test."""

    async def _yield_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = _yield_user


def _override_db_and_redis() -> tuple[MagicMock, MagicMock]:
    """Bind dummy DB + Redis clients so the dependencies don't try to talk
    to real services. Returns the two mocks for assertion access."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def _yield_db() -> MagicMock:
        return db

    redis = MagicMock()

    async def _yield_redis() -> MagicMock:
        return redis

    app.dependency_overrides[get_session] = _yield_db
    app.dependency_overrides[get_redis] = _yield_redis
    return db, redis


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_me_requires_auth(async_client: AsyncClient) -> None:
    """No token → 401, regardless of body."""
    r = await async_client.request(
        "DELETE",
        "/api/v1/user/me",
        json={"password": "anything-goes-12"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Wrong password
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_me_wrong_password_returns_401(async_client: AsyncClient) -> None:
    user = make_user(hashed_password=hash_password("correct-pw1"))
    _override_user(user)
    _override_db_and_redis()

    try:
        with patch(
            "app.api.v1.endpoints.user.delete_user_account",
            new_callable=AsyncMock,
            side_effect=UserDeletionError("Invalid credentials"),
        ):
            r = await async_client.request(
                "DELETE",
                "/api/v1/user/me",
                json={"password": "wrong-pw1"},
                cookies={"access_token": VALID_ACCESS_TOKEN},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_me_success_returns_204_and_clears_cookies(
    async_client: AsyncClient,
) -> None:
    user = make_user(hashed_password=hash_password("correct-pw1"))
    _override_user(user)
    _override_db_and_redis()

    try:
        with patch(
            "app.api.v1.endpoints.user.delete_user_account",
            new_callable=AsyncMock,
            return_value=None,
        ) as svc:
            r = await async_client.request(
                "DELETE",
                "/api/v1/user/me",
                json={"password": "correct-pw1"},
                cookies={"access_token": VALID_ACCESS_TOKEN},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 204
    assert r.text == ""

    # Both auth cookies are explicitly invalidated on the response.
    set_cookie_headers = r.headers.get_list("set-cookie")
    joined = " | ".join(set_cookie_headers).lower()
    assert "access_token=" in joined
    assert "refresh_token=" in joined
    # Path scoping must match what the auth endpoints set.
    assert "path=/api" in joined

    # Service was called exactly once with the password from the body.
    svc.assert_awaited_once()
    _, _, called_user, called_password = svc.await_args.args
    assert called_user is user
    assert called_password == "correct-pw1"


@pytest.mark.asyncio
async def test_delete_me_works_for_unverified_user(async_client: AsyncClient) -> None:
    """DSGVO Art. 17 must not require email verification."""
    user = make_user(verified=False, hashed_password=hash_password("correct-pw1"))
    _override_user(user)
    _override_db_and_redis()

    try:
        with patch(
            "app.api.v1.endpoints.user.delete_user_account",
            new_callable=AsyncMock,
            return_value=None,
        ):
            r = await async_client.request(
                "DELETE",
                "/api/v1/user/me",
                json={"password": "correct-pw1"},
                cookies={"access_token": VALID_ACCESS_TOKEN},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Body validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_me_missing_password_returns_422(async_client: AsyncClient) -> None:
    user = make_user(hashed_password=hash_password("correct-pw1"))
    _override_user(user)
    _override_db_and_redis()
    try:
        r = await async_client.request(
            "DELETE",
            "/api/v1/user/me",
            json={},
            cookies={"access_token": VALID_ACCESS_TOKEN},
        )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_me_short_password_returns_422(async_client: AsyncClient) -> None:
    user = make_user(hashed_password=hash_password("correct-pw1"))
    _override_user(user)
    _override_db_and_redis()
    try:
        r = await async_client.request(
            "DELETE",
            "/api/v1/user/me",
            json={"password": "short"},  # < 8 chars → 422 by schema
            cookies={"access_token": VALID_ACCESS_TOKEN},
        )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_export_my_data_returns_zip_attachment(async_client: AsyncClient) -> None:
    user = make_user()
    _override_user(user)

    fake_zip = b"PK\x03\x04fake-export"

    try:
        with (
            patch(
                "app.api.v1.endpoints.user.build_export_envelope",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch(
                "app.api.v1.endpoints.user.render_export_zip",
                return_value=fake_zip,
            ),
        ):
            r = await async_client.get(
                "/api/v1/user/export",
                cookies={"access_token": VALID_ACCESS_TOKEN},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.content == fake_zip
    assert "application/zip" in r.headers["content-type"]
    assert "correlcore-export" in r.headers["content-disposition"]

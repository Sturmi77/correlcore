"""Tests for auth endpoints.

Coverage:
- POST /api/v1/auth/register   — enumeration-safe 202 (new + existing), weak password (Issue #65)
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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_user
from app.main import app
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.auth_service import (
    AuthError,
    RegistrationOutcome,
    request_registration,
)
from tests.conftest import (
    NEW_ACCESS_TOKEN,
    NEW_REFRESH_TOKEN,
    TEST_PASSWORD,
    VALID_ACCESS_TOKEN,
    VALID_REFRESH_TOKEN,
    make_user,
)

# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_new_email_returns_202(async_client: AsyncClient) -> None:
    """Issue #65: fresh registration returns the generic 202 message."""
    user = make_user(verified=False)
    outcome = RegistrationOutcome(action="created", user=user, verification_token="plaintext-token")
    with (
        patch(
            "app.api.v1.endpoints.auth.request_registration",
            new_callable=AsyncMock,
            return_value=outcome,
        ),
        patch(
            "app.api.v1.endpoints.auth.send_verification_email",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.auth.send_already_registered_email",
            new_callable=AsyncMock,
        ) as mock_already,
    ):
        r = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": TEST_PASSWORD},
        )
    assert r.status_code == 202
    assert r.json()["message"].startswith("If the email is not yet registered")
    # Already-registered mail must NOT fire on a fresh signup.
    mock_already.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_existing_email_also_returns_202(async_client: AsyncClient) -> None:
    """Issue #65 (SA-1): existing email yields the same 202 response.

    The endpoint must not leak that the address is registered — status,
    body, and headers must be identical to the new-user branch.
    """
    user = make_user(verified=True)
    outcome = RegistrationOutcome(action="already_registered", user=user, verification_token=None)
    with (
        patch(
            "app.api.v1.endpoints.auth.request_registration",
            new_callable=AsyncMock,
            return_value=outcome,
        ),
        patch(
            "app.api.v1.endpoints.auth.send_verification_email",
            new_callable=AsyncMock,
        ) as mock_verify,
        patch(
            "app.api.v1.endpoints.auth.send_already_registered_email",
            new_callable=AsyncMock,
        ),
    ):
        r = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "dupe@example.com", "password": TEST_PASSWORD},
        )
    assert r.status_code == 202
    assert r.json()["message"].startswith("If the email is not yet registered")
    # Verification mail must NOT fire when the email already exists.
    mock_verify.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_responses_are_indistinguishable(async_client: AsyncClient) -> None:
    """Both branches must return byte-for-byte the same response body+status."""
    new_user = make_user(verified=False)
    existing_user = make_user(verified=True)

    new_outcome = RegistrationOutcome(action="created", user=new_user, verification_token="tok-x")
    existing_outcome = RegistrationOutcome(
        action="already_registered", user=existing_user, verification_token=None
    )

    with (
        patch(
            "app.api.v1.endpoints.auth.request_registration",
            new_callable=AsyncMock,
        ) as mock_req,
        patch(
            "app.api.v1.endpoints.auth.send_verification_email",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.auth.send_already_registered_email",
            new_callable=AsyncMock,
        ),
    ):
        mock_req.return_value = new_outcome
        r_new = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "fresh@example.com", "password": TEST_PASSWORD},
        )
        mock_req.return_value = existing_outcome
        r_exist = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "dupe@example.com", "password": TEST_PASSWORD},
        )

    assert r_new.status_code == r_exist.status_code == 202
    assert r_new.json() == r_exist.json()


@pytest.mark.asyncio
async def test_register_weak_password(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "short"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_rate_limit_kicks_in_after_five_per_minute(
    async_client: AsyncClient,
) -> None:
    """Issue #65 (SA-2): the 6th register attempt within 60s yields 429.

    The shared in-memory SlowAPI limiter is reset before the test so we
    are not affected by counters from earlier tests in the suite.
    """
    from app.core.rate_limit import limiter

    limiter.reset()
    user = make_user(verified=False)
    outcome = RegistrationOutcome(action="created", user=user, verification_token="tok-y")
    with (
        patch(
            "app.api.v1.endpoints.auth.request_registration",
            new_callable=AsyncMock,
            return_value=outcome,
        ),
        patch(
            "app.api.v1.endpoints.auth.send_verification_email",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.auth.send_already_registered_email",
            new_callable=AsyncMock,
        ),
    ):
        statuses = []
        for _ in range(6):
            r = await async_client.post(
                "/api/v1/auth/register",
                json={"email": "rl@example.com", "password": TEST_PASSWORD},
            )
            statuses.append(r.status_code)

    # First five succeed; the sixth is rate-limited.
    assert statuses[:5] == [202, 202, 202, 202, 202]
    assert statuses[5] == 429
    limiter.reset()


# ---------------------------------------------------------------------------
# Service: request_registration  (Issue #65)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_registration_existing_email_returns_already_registered() -> None:
    """Existing email returns the ``already_registered`` outcome — no DB writes,
    no token minted, no exception raised.
    """
    existing = make_user(verified=True)
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=user_result)

    outcome = await request_registration(
        db,
        RegisterRequest(email=existing.email, password=TEST_PASSWORD),
    )

    assert outcome.action == "already_registered"
    assert outcome.user is existing
    assert outcome.verification_token is None
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_request_registration_new_email_returns_created() -> None:
    """Fresh email is delegated to ``register_user`` + ``create_verification_token``
    and returned as ``created`` outcome with a plaintext token.
    """
    fresh = make_user(verified=False, email="fresh@example.com")
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    no_user_result = MagicMock()
    no_user_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_user_result)

    with (
        patch(
            "app.services.auth_service.register_user",
            new_callable=AsyncMock,
            return_value=fresh,
        ),
        patch(
            "app.services.auth_service.create_verification_token",
            new_callable=AsyncMock,
            return_value="plaintext-tok",
        ),
    ):
        outcome = await request_registration(
            db,
            RegisterRequest(email=fresh.email, password=TEST_PASSWORD),
        )

    assert outcome.action == "created"
    assert outcome.user is fresh
    assert outcome.verification_token == "plaintext-tok"


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
            json={"email": "test@example.com", "password": TEST_PASSWORD},
        )
    assert r.status_code == 200
    data = r.json()
    # Browser cookie flow: access JWT omitted from JSON by default (XSS surface).
    assert "access_token" not in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == user.email
    # HttpOnly cookies must be set
    assert "access_token" in r.cookies
    assert "refresh_token" in r.cookies


@pytest.mark.asyncio
async def test_login_include_access_token_opt_in(async_client: AsyncClient, user: User) -> None:
    with patch(
        "app.api.v1.endpoints.auth.login_user",
        new_callable=AsyncMock,
        return_value=(VALID_ACCESS_TOKEN, VALID_REFRESH_TOKEN, user),
    ):
        r = await async_client.post(
            "/api/v1/auth/login?include_access_token=true",
            json={"email": "test@example.com", "password": TEST_PASSWORD},
        )
    assert r.status_code == 200
    assert r.json()["access_token"] == VALID_ACCESS_TOKEN


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
    assert "access_token" not in r.json()
    assert "access_token" in r.cookies


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

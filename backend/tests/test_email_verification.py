"""Tests for Issue #39 \u2014 email verification flow.

Coverage:
- Service: ``_hash_token`` is deterministic and SHA-256 sized.
- Service: ``verify_email`` rejects unknown / expired / already-used tokens
  with the same generic error (no enumeration via message comparison).
- Service: ``verify_email`` succeeds, sets ``is_verified=True`` and stamps
  ``used_at`` so a second call with the same token fails.
- Service: ``request_verification_resend`` returns ``None`` for unknown
  email and for already-verified user.
- Endpoint: POST /verify-email returns 200 on success, 400 on bad token.
- Endpoint: POST /resend-verification always returns 202 with the same
  generic message, regardless of whether the email is registered.
- Endpoint: POST /register schedules the verification email as a
  background task.

DB is mocked at the service boundary \u2014 we don't want a Postgres dep in
unit tests. End-to-end DB integration is covered by the Compose-stack
integration test (separate, not in this PR).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User
from app.services.auth_service import (
    VerificationError,
    _hash_token,
    request_verification_resend,
    verify_email,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, verified: bool = False, active: bool = True) -> User:
    u = User()
    u.id = uuid.uuid4()
    u.email = "test@example.com"
    u.hashed_password = "$2b$12$placeholder"
    u.display_name = "Test User"
    u.is_active = active
    u.is_verified = verified
    u.created_at = datetime.now(UTC)
    u.updated_at = datetime.now(UTC)
    return u


def _make_token(
    user: User,
    *,
    plaintext: str | None = None,
    expires_in: timedelta = timedelta(hours=1),
    used: bool = False,
) -> tuple[EmailVerificationToken, str]:
    plaintext = plaintext or secrets.token_urlsafe(32)
    record = EmailVerificationToken()
    record.id = uuid.uuid4()
    record.user_id = user.id
    record.token_hash = _hash_token(plaintext)
    record.expires_at = datetime.now(UTC) + expires_in
    record.used_at = datetime.now(UTC) if used else None
    record.created_at = datetime.now(UTC)
    return record, plaintext


def _make_db_with_token(
    token_record: EmailVerificationToken | None,
    user: User | None,
) -> MagicMock:
    """Build an AsyncSession mock that yields ``token_record`` then ``user``
    on consecutive ``execute().scalar_one_or_none()`` calls."""
    db = MagicMock()
    db.flush = AsyncMock()

    token_result = MagicMock()
    token_result.scalar_one_or_none.return_value = token_record
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    db.execute = AsyncMock(side_effect=[token_result, user_result])
    return db


# ---------------------------------------------------------------------------
# Service: _hash_token
# ---------------------------------------------------------------------------


def test_hash_token_is_sha256() -> None:
    assert _hash_token("abc") == hashlib.sha256(b"abc").hexdigest()
    assert len(_hash_token("anything")) == 64


def test_hash_token_is_deterministic() -> None:
    assert _hash_token("same") == _hash_token("same")
    assert _hash_token("a") != _hash_token("b")


# ---------------------------------------------------------------------------
# Service: verify_email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_email_unknown_token() -> None:
    db = _make_db_with_token(None, None)
    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, "does-not-exist")


@pytest.mark.asyncio
async def test_verify_email_expired_token() -> None:
    user = _make_user()
    token, plaintext = _make_token(user, expires_in=timedelta(hours=-1))
    db = _make_db_with_token(token, user)

    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, plaintext)


@pytest.mark.asyncio
async def test_verify_email_already_used_token() -> None:
    user = _make_user()
    token, plaintext = _make_token(user, used=True)
    db = _make_db_with_token(token, user)

    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, plaintext)


@pytest.mark.asyncio
async def test_verify_email_inactive_user() -> None:
    user = _make_user(active=False)
    token, plaintext = _make_token(user)
    db = _make_db_with_token(token, user)

    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, plaintext)


@pytest.mark.asyncio
async def test_verify_email_success_marks_user_verified() -> None:
    user = _make_user(verified=False)
    token, plaintext = _make_token(user)
    db = _make_db_with_token(token, user)

    result_user = await verify_email(db, plaintext)

    assert result_user.is_verified is True
    assert token.used_at is not None
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_email_idempotent_for_already_verified() -> None:
    """A user who is already verified stays verified; token is still consumed."""
    user = _make_user(verified=True)
    token, plaintext = _make_token(user)
    db = _make_db_with_token(token, user)

    result_user = await verify_email(db, plaintext)

    assert result_user.is_verified is True
    assert token.used_at is not None


# ---------------------------------------------------------------------------
# Service: request_verification_resend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resend_returns_none_for_unknown_email() -> None:
    db = MagicMock()
    db.flush = AsyncMock()
    no_user_result = MagicMock()
    no_user_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_user_result)

    result = await request_verification_resend(db, "ghost@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_resend_returns_none_for_already_verified() -> None:
    user = _make_user(verified=True)
    db = MagicMock()
    db.flush = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=user_result)

    result = await request_verification_resend(db, user.email)
    assert result is None


# ---------------------------------------------------------------------------
# Endpoint: POST /verify-email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoint_verify_email_success() -> None:
    with patch(
        "app.api.v1.endpoints.auth.verify_email",
        new_callable=AsyncMock,
    ) as mock_verify:
        mock_verify.return_value = _make_user(verified=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/auth/verify-email",
                json={"token": "x" * 32},
            )
    assert r.status_code == 200
    assert "verified" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_endpoint_verify_email_invalid_returns_400() -> None:
    with patch(
        "app.api.v1.endpoints.auth.verify_email",
        new_callable=AsyncMock,
        side_effect=VerificationError("Invalid or expired verification token"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/auth/verify-email",
                json={"token": "x" * 32},
            )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_endpoint_verify_email_short_token_validation() -> None:
    """Pydantic should reject obviously short tokens before the service is called."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/verify-email",
            json={"token": "short"},
        )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Endpoint: POST /resend-verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoint_resend_unknown_email_still_202() -> None:
    """Enumeration protection: response is the same whether email exists or not."""
    with patch(
        "app.api.v1.endpoints.auth.request_verification_resend",
        new_callable=AsyncMock,
        return_value=None,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/auth/resend-verification",
                json={"email": "unknown@example.com"},
            )
    assert r.status_code == 202


@pytest.mark.asyncio
async def test_endpoint_resend_known_email_schedules_mail() -> None:
    user = _make_user(verified=False)
    plaintext = "tok_" + "x" * 32

    with patch(
        "app.api.v1.endpoints.auth.request_verification_resend",
        new_callable=AsyncMock,
        return_value=(user, plaintext),
    ), patch(
        "app.api.v1.endpoints.auth.send_verification_email",
        new_callable=AsyncMock,
    ) as mock_send:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/auth/resend-verification",
                json={"email": user.email},
            )
    assert r.status_code == 202
    # BackgroundTask runs after response \u2014 give it a tick
    mock_send.assert_awaited()


# ---------------------------------------------------------------------------
# Endpoint: POST /register schedules verification email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_schedules_verification_email() -> None:
    user = _make_user(verified=False)
    plaintext = "tok_" + "y" * 32

    with patch(
        "app.api.v1.endpoints.auth.register_user",
        new_callable=AsyncMock,
        return_value=user,
    ), patch(
        "app.api.v1.endpoints.auth.create_verification_token",
        new_callable=AsyncMock,
        return_value=plaintext,
    ), patch(
        "app.api.v1.endpoints.auth.send_verification_email",
        new_callable=AsyncMock,
    ) as mock_send:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/auth/register",
                json={
                    "email": "fresh@example.com",
                    "password": "Passw0rd",
                },
            )

    assert r.status_code == 201
    mock_send.assert_awaited()
    # Verify the call carried the plaintext token (NOT a hash)
    awaited_kwargs = mock_send.call_args.kwargs
    assert awaited_kwargs["token"] == plaintext

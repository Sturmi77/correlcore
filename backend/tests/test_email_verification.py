"""Tests for Issue #39 — email verification flow.

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

DB is mocked at the service boundary — we don't want a Postgres dep in
unit tests. End-to-end DB integration is covered by the Compose-stack
integration test (separate, not in this PR).

Shared factories (``make_user``, ``make_verification_token``,
``make_db_session_with_results``) and the ``async_client`` fixture live
in :mod:`tests.conftest`.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.services.auth_service import (
    VerificationError,
    _hash_token,
    request_verification_resend,
    verify_email,
)
from tests.conftest import (
    VALID_ACCESS_TOKEN,
    VALID_REFRESH_TOKEN,
    make_db_session_with_results,
    make_user,
    make_verification_token,
)

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
    db = make_db_session_with_results(None, None)
    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, "does-not-exist")


@pytest.mark.asyncio
async def test_verify_email_expired_token() -> None:
    user = make_user(verified=False)
    token, plaintext = make_verification_token(user, expires_in=timedelta(hours=-1))
    db = make_db_session_with_results(token, user)

    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, plaintext)


@pytest.mark.asyncio
async def test_verify_email_already_used_token() -> None:
    user = make_user(verified=False)
    token, plaintext = make_verification_token(user, used=True)
    db = make_db_session_with_results(token, user)

    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, plaintext)


@pytest.mark.asyncio
async def test_verify_email_inactive_user() -> None:
    user = make_user(verified=False, active=False)
    token, plaintext = make_verification_token(user)
    db = make_db_session_with_results(token, user)

    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, plaintext)


@pytest.mark.asyncio
async def test_verify_email_success_marks_user_verified() -> None:
    user = make_user(verified=False)
    token, plaintext = make_verification_token(user)
    db = make_db_session_with_results(token, user)

    result_user = await verify_email(db, plaintext)

    assert result_user.is_verified is True
    assert token.used_at is not None
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_email_idempotent_for_already_verified() -> None:
    """A user who is already verified stays verified; token is still consumed."""
    user = make_user(verified=True)
    token, plaintext = make_verification_token(user)
    db = make_db_session_with_results(token, user)

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
    user = make_user(verified=True)
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
async def test_endpoint_verify_email_success(async_client: AsyncClient) -> None:
    user = make_user(verified=True)
    with (
        patch(
            "app.api.v1.endpoints.auth.verify_email",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.api.v1.endpoints.auth.issue_session_tokens",
            new_callable=AsyncMock,
            return_value=(VALID_ACCESS_TOKEN, VALID_REFRESH_TOKEN),
        ),
    ):
        r = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "x" * 32},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["access_token"] == VALID_ACCESS_TOKEN
    assert data["user"]["email"] == user.email
    assert "access_token" in r.cookies
    assert "refresh_token" in r.cookies


@pytest.mark.asyncio
async def test_endpoint_verify_email_invalid_returns_400(async_client: AsyncClient) -> None:
    with patch(
        "app.api.v1.endpoints.auth.verify_email",
        new_callable=AsyncMock,
        side_effect=VerificationError("Invalid or expired verification token"),
    ):
        r = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "x" * 32},
        )
    assert r.status_code == 400
    assert "access_token" not in r.cookies
    assert "refresh_token" not in r.cookies


@pytest.mark.asyncio
async def test_endpoint_verify_email_short_token_validation(async_client: AsyncClient) -> None:
    """Pydantic should reject obviously short tokens before the service is called."""
    r = await async_client.post(
        "/api/v1/auth/verify-email",
        json={"token": "short"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Endpoint: POST /resend-verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoint_resend_unknown_email_still_202(async_client: AsyncClient) -> None:
    """Enumeration protection: response is the same whether email exists or not."""
    with patch(
        "app.api.v1.endpoints.auth.request_verification_resend",
        new_callable=AsyncMock,
        return_value=None,
    ):
        r = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "unknown@example.com"},
        )
    assert r.status_code == 202


@pytest.mark.asyncio
async def test_endpoint_resend_known_email_schedules_mail(async_client: AsyncClient) -> None:
    user = make_user(verified=False)
    plaintext = "tok_" + "x" * 32

    with (
        patch(
            "app.api.v1.endpoints.auth.request_verification_resend",
            new_callable=AsyncMock,
            return_value=(user, plaintext),
        ),
        patch(
            "app.api.v1.endpoints.auth.send_verification_email",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        r = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": user.email},
        )
    assert r.status_code == 202
    # BackgroundTask runs after response — give it a tick
    mock_send.assert_awaited()


# ---------------------------------------------------------------------------
# Endpoint: POST /register schedules verification email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_schedules_verification_email(async_client: AsyncClient) -> None:
    """Issue #39 / Issue #65: a fresh registration schedules the verify mail.

    The endpoint now goes through ``request_registration`` (Issue #65) and
    always returns 202; the verify-mail must still be dispatched in the
    background for the ``created`` branch.
    """
    from app.services.auth_service import RegistrationOutcome

    user = make_user(verified=False)
    plaintext = "tok_" + "y" * 32
    outcome = RegistrationOutcome(action="created", user=user, verification_token=plaintext)

    with (
        patch(
            "app.api.v1.endpoints.auth.request_registration",
            new_callable=AsyncMock,
            return_value=outcome,
        ),
        patch(
            "app.api.v1.endpoints.auth.send_verification_email",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        r = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "fresh@example.com",
                "password": "Passw0rd",
            },
        )

    assert r.status_code == 202
    mock_send.assert_awaited()
    # Verify the call carried the plaintext token (NOT a hash)
    awaited_kwargs = mock_send.call_args.kwargs
    assert awaited_kwargs["token"] == plaintext

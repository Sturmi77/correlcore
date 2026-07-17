"""Service-layer tests for ``app.services.auth_service`` (Issue #64).

These tests target the auth-service code paths that are not exercised
by the endpoint tests in :mod:`tests.test_auth` and
:mod:`tests.test_email_verification` and bring the module's coverage
from ~53 % to ≥ 85 % per Design-Doc § 9 / Quality-Gate Finding CQR-1.

DB and TokenStore are mocked — no Postgres or Redis is required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_refresh_token
from app.models.email_verification_token import EmailVerificationToken
from app.schemas.auth import RegisterRequest
from app.services.auth_service import (
    AuthError,
    EmailNotVerifiedError,
    RegistrationError,
    VerificationError,
    create_verification_token,
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
    request_verification_resend,
    verify_email,
)
from tests.conftest import TEST_PASSWORD, make_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(scalar_one_or_none: object = None) -> MagicMock:
    """Build a mock AsyncSession that returns ``scalar_one_or_none`` from
    every ``execute`` call. ``flush`` and ``add`` are stubbed."""
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    db.execute = AsyncMock(return_value=result)
    return db


def _make_token_record(
    *,
    user_id: uuid.UUID,
    used_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> EmailVerificationToken:
    rec = EmailVerificationToken()
    rec.id = uuid.uuid4()
    rec.user_id = user_id
    rec.token_hash = "x" * 64
    rec.used_at = used_at
    rec.expires_at = expires_at or (datetime.now(UTC) + timedelta(hours=24))
    return rec


# ---------------------------------------------------------------------------
# register_user — duplicate path + happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_user_raises_on_duplicate_email() -> None:
    """``register_user`` raises ``RegistrationError`` when the email exists.

    The endpoint pathway uses ``request_registration`` instead and never
    surfaces this exception (Issue #65), but the helper is still called
    by tests and is documented to raise.
    """
    existing = make_user()
    db = _make_db(scalar_one_or_none=existing)

    with pytest.raises(RegistrationError, match="already registered"):
        await register_user(
            db,
            RegisterRequest(email=existing.email, password=TEST_PASSWORD),
        )
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_register_user_creates_user_and_dek() -> None:
    """Happy path: db.add is called twice — once for User, once for DEK row.

    The DEK plaintext is generated and immediately wrapped; we just
    assert the DB-side bookkeeping here, the crypto roundtrip is
    covered separately in ``test_crypto.py``.
    """
    db = _make_db(scalar_one_or_none=None)

    with (
        patch("app.services.auth_service.generate_dek", return_value=b"x" * 32) as mock_gen,
        patch("app.services.auth_service.wrap_dek", return_value=b"wrapped-dek-bytes") as mock_wrap,
    ):
        user = await register_user(
            db,
            RegisterRequest(email="fresh@example.com", password=TEST_PASSWORD),
        )

    assert user.email == "fresh@example.com"
    assert user.is_active is True
    assert user.is_verified is False
    # Two add() calls: User then UserEncryptionKey
    assert db.add.call_count == 2
    # Two flush() calls: after User add (to mint UUID) and after key add
    assert db.flush.await_count == 2
    mock_gen.assert_called_once()
    mock_wrap.assert_called_once()


# ---------------------------------------------------------------------------
# verify_email — all 4 error branches share the same generic message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_email_unknown_token_raises_generic() -> None:
    db = _make_db(scalar_one_or_none=None)
    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, "tok_unknown")


@pytest.mark.asyncio
async def test_verify_email_replay_uses_same_message() -> None:
    user = make_user(verified=True)
    rec = _make_token_record(user_id=user.id, used_at=datetime.now(UTC))
    db = _make_db(scalar_one_or_none=rec)
    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, "tok_replay")


@pytest.mark.asyncio
async def test_verify_email_expired_uses_same_message() -> None:
    user = make_user(verified=False)
    rec = _make_token_record(
        user_id=user.id,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db = _make_db(scalar_one_or_none=rec)
    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, "tok_expired")


@pytest.mark.asyncio
async def test_verify_email_user_inactive_uses_same_message() -> None:
    """Token is fine but the user has been deactivated — must still 400 generic."""
    user = make_user(active=False)
    rec = _make_token_record(user_id=user.id)

    # First execute() → returns the token, second → returns the user
    token_result = MagicMock()
    token_result.scalar_one_or_none.return_value = rec
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(side_effect=[token_result, user_result])

    with pytest.raises(VerificationError, match="Invalid or expired"):
        await verify_email(db, "tok_inactive_user")


@pytest.mark.asyncio
async def test_verify_email_success_marks_user_verified_and_consumes_token() -> None:
    user = make_user(verified=False)
    rec = _make_token_record(user_id=user.id)

    token_result = MagicMock()
    token_result.scalar_one_or_none.return_value = rec
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(side_effect=[token_result, user_result])

    returned = await verify_email(db, "tok_valid")

    assert returned is user
    assert user.is_verified is True
    assert rec.used_at is not None  # token consumed
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_email_idempotent_for_already_verified_user() -> None:
    """Already-verified user stays verified; token is still consumed."""
    user = make_user(verified=True)
    rec = _make_token_record(user_id=user.id)
    token_result = MagicMock()
    token_result.scalar_one_or_none.return_value = rec
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(side_effect=[token_result, user_result])

    returned = await verify_email(db, "tok_idem")
    assert returned is user
    assert user.is_verified is True
    assert rec.used_at is not None


# ---------------------------------------------------------------------------
# create_verification_token / request_verification_resend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_verification_token_returns_plaintext_and_persists_hash() -> None:
    user = make_user()
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()  # for the DELETE prior tokens

    plaintext = await create_verification_token(db, user)

    assert isinstance(plaintext, str) and len(plaintext) >= 32
    # delete-prior + add-new: one execute for delete, one add for new
    db.execute.assert_awaited_once()
    db.add.assert_called_once()
    persisted: EmailVerificationToken = db.add.call_args.args[0]
    # Only the SHA-256 hash is persisted, never the plaintext.
    assert persisted.token_hash != plaintext
    assert len(persisted.token_hash) == 64  # sha256 hex


@pytest.mark.asyncio
async def test_request_verification_resend_returns_token_for_unverified_user() -> None:
    user = make_user(verified=False)
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user)))
    with patch(
        "app.services.auth_service.create_verification_token",
        new_callable=AsyncMock,
        return_value="plaintext-tok",
    ):
        result = await request_verification_resend(db, user.email)

    assert result is not None
    returned_user, plaintext = result
    assert returned_user is user
    assert plaintext == "plaintext-tok"


@pytest.mark.asyncio
async def test_request_verification_resend_returns_none_for_inactive_user() -> None:
    user = make_user(active=False, verified=False)
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user)))
    result = await request_verification_resend(db, user.email)
    assert result is None


# ---------------------------------------------------------------------------
# login_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_user_unknown_email_raises_generic_auth_error() -> None:
    db = _make_db(scalar_one_or_none=None)
    store = MagicMock()
    store.store = AsyncMock()

    with patch("app.services.auth_service.verify_password", return_value=False):
        with pytest.raises(AuthError, match="Invalid credentials"):
            await login_user(db, store, "ghost@example.com", TEST_PASSWORD)
    # Even with no user, the password verification must run (constant-time path)
    store.store.assert_not_called()


@pytest.mark.asyncio
async def test_login_user_wrong_password_raises_auth_error() -> None:
    user = make_user()
    db = _make_db(scalar_one_or_none=user)
    store = MagicMock()
    store.store = AsyncMock()

    with patch("app.services.auth_service.verify_password", return_value=False):
        with pytest.raises(AuthError, match="Invalid credentials"):
            await login_user(db, store, user.email, "wrong")
    store.store.assert_not_called()


@pytest.mark.asyncio
async def test_login_user_inactive_account_raises_distinct_auth_error() -> None:
    user = make_user(active=False)
    db = _make_db(scalar_one_or_none=user)
    store = MagicMock()
    store.store = AsyncMock()

    with patch("app.services.auth_service.verify_password", return_value=True):
        with pytest.raises(AuthError, match="disabled"):
            await login_user(db, store, user.email, TEST_PASSWORD)
    store.store.assert_not_called()


@pytest.mark.asyncio
async def test_login_user_unverified_email_raises_email_not_verified_error() -> None:
    """Active but unverified accounts must be blocked from login (→ HTTP 403).

    EmailNotVerifiedError is a subclass of AuthError; the endpoint catches
    it specifically before the generic AuthError handler so it can return
    403 instead of 401, enabling the frontend's 'resend verification' UI.
    """
    user = make_user(verified=False, active=True)
    db = _make_db(scalar_one_or_none=user)
    store = MagicMock()
    store.store = AsyncMock()

    with patch("app.services.auth_service.verify_password", return_value=True):
        with pytest.raises(EmailNotVerifiedError, match="not verified"):
            await login_user(db, store, user.email, TEST_PASSWORD)
    # Subclass relationship matters for endpoint mapping
    assert issubclass(EmailNotVerifiedError, AuthError)
    store.store.assert_not_called()


@pytest.mark.asyncio
async def test_login_user_success_stores_jti_and_returns_token_pair() -> None:
    user = make_user()
    db = _make_db(scalar_one_or_none=user)
    store = MagicMock()
    store.store = AsyncMock()

    with patch("app.services.auth_service.verify_password", return_value=True):
        access, refresh, returned = await login_user(db, store, user.email, TEST_PASSWORD)

    assert returned is user
    assert isinstance(access, str) and access.count(".") == 2
    assert isinstance(refresh, str) and refresh.count(".") == 2
    store.store.assert_awaited_once()
    stored_user_id, stored_jti = store.store.await_args.args
    assert stored_user_id == str(user.id)
    # JTI from the refresh token must equal what was stored in Redis.
    payload = jwt.decode(refresh, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["jti"] == stored_jti
    assert payload["type"] == "refresh"


# ---------------------------------------------------------------------------
# refresh_tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_tokens_invalid_signature_raises() -> None:
    db = MagicMock()
    store = MagicMock()
    with pytest.raises(AuthError, match="Invalid or expired"):
        await refresh_tokens(db, store, "not.a.jwt")


@pytest.mark.asyncio
async def test_refresh_tokens_wrong_type_raises() -> None:
    """An access-token in the refresh slot must be rejected."""
    user = make_user()
    db = MagicMock()
    store = MagicMock()
    # Build a token with type=access on purpose.
    payload = {
        "sub": str(user.id),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iat": datetime.now(UTC),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    bad = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(AuthError, match="Wrong token type"):
        await refresh_tokens(db, store, bad)


@pytest.mark.asyncio
async def test_refresh_tokens_replay_revokes_all_for_user() -> None:
    """A replayed JTI revokes every refresh token for that user."""
    user = make_user()
    db = _make_db(scalar_one_or_none=user)
    store = MagicMock()
    store.rotate = AsyncMock(return_value=False)
    store.revoke_all = AsyncMock()
    refresh = create_refresh_token(subject=str(user.id), jti=str(uuid.uuid4()))

    with pytest.raises(AuthError, match="already used or revoked"):
        await refresh_tokens(db, store, refresh)
    store.revoke_all.assert_awaited_once_with(str(user.id))


@pytest.mark.asyncio
async def test_refresh_tokens_malformed_subject_raises() -> None:
    """A non-UUID subject in an otherwise valid token is rejected."""
    db = MagicMock()
    store = MagicMock()
    payload = {
        "sub": "not-a-uuid",
        "exp": datetime.now(UTC) + timedelta(days=30),
        "iat": datetime.now(UTC),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    bad = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(AuthError, match="Malformed token"):
        await refresh_tokens(db, store, bad)
    store.rotate.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_tokens_user_disabled_raises() -> None:
    user = make_user(active=False)
    db = _make_db(scalar_one_or_none=user)
    store = MagicMock()
    store.rotate = AsyncMock()
    refresh = create_refresh_token(subject=str(user.id), jti=str(uuid.uuid4()))

    with pytest.raises(AuthError, match="not found or disabled"):
        await refresh_tokens(db, store, refresh)
    store.rotate.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_tokens_success_rotates_jti_in_redis() -> None:
    user = make_user()
    db = _make_db(scalar_one_or_none=user)
    store = MagicMock()
    store.rotate = AsyncMock(return_value=True)
    old_jti = str(uuid.uuid4())
    refresh = create_refresh_token(subject=str(user.id), jti=old_jti)

    new_access, new_refresh, returned = await refresh_tokens(db, store, refresh)

    assert returned is user
    assert isinstance(new_access, str) and new_access.count(".") == 2
    assert new_refresh != refresh
    store.rotate.assert_awaited_once()
    user_id_arg, old_jti_arg, new_jti_arg = store.rotate.await_args.args
    assert user_id_arg == str(user.id)
    assert old_jti_arg == old_jti
    assert new_jti_arg != old_jti
    # The new refresh token must carry the new JTI.
    payload = jwt.decode(new_refresh, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["jti"] == new_jti_arg


# ---------------------------------------------------------------------------
# logout_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_user_revokes_jti_for_valid_token() -> None:
    user = make_user()
    store = MagicMock()
    store.revoke = AsyncMock()
    jti = str(uuid.uuid4())
    refresh = create_refresh_token(subject=str(user.id), jti=jti)

    await logout_user(store, refresh)

    store.revoke.assert_awaited_once_with(str(user.id), jti)


@pytest.mark.asyncio
async def test_logout_user_swallows_invalid_token() -> None:
    """Invalid/expired tokens must not raise — logout is best-effort."""
    store = MagicMock()
    store.revoke = AsyncMock()
    # Should not raise.
    await logout_user(store, "garbage.not.jwt")
    store.revoke.assert_not_called()

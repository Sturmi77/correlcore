"""Auth service — business logic for register, login, refresh, logout.

ADR-0004 compliance:
- bcrypt work factor ≥ 12 (set in core/security.py pwd_context)
- Refresh tokens are single-use (rotated on every /refresh call)
- Access tokens: 15 min TTL
- Refresh tokens: 30 day TTL, stored in Redis by JTI
- HttpOnly + Secure + SameSite=Strict cookies set by endpoint layer
- Rate-limiting applied at endpoint layer (SlowAPI)

Privacy: no user content (mood/symptoms/notes) is ever touched here.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from jose import JWTError, jwt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import generate_dek, wrap_dek
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.db.redis_client import TokenStore
from app.db.session import bind_rls_current_user
from app.models.email_verification_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.models.user_encryption_key import UserEncryptionKey
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)
_DUMMY_PASSWORD_HASH = hash_password("__correlcore_dummy_password__")

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Base auth error — maps to HTTP 401."""


class EmailNotVerifiedError(AuthError):
    """Login attempt with unverified email — maps to HTTP 403.

    Distinct from generic AuthError so the endpoint can return 403 and the
    frontend can offer a 'resend verification' action.
    """


class RegistrationError(Exception):
    """Maps to HTTP 409 (conflict) or HTTP 422 (validation)."""


class VerificationError(Exception):
    """Email verification failed — maps to HTTP 400.

    Error message is intentionally generic to avoid leaking whether a
    token existed-but-expired vs. never-existed (timing/enumeration).
    """


class PasswordResetError(Exception):
    """Password reset failed — maps to HTTP 400.

    Error message is intentionally generic to avoid leaking token state.
    """


# ---------------------------------------------------------------------------
# Registration request — enumeration-safe envelope (Issue #65, SA-1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegistrationOutcome:
    """Result of :func:`request_registration`.

    The endpoint layer always responds with the same generic 202 message,
    regardless of which branch fires. This envelope tells the endpoint
    which background mail (if any) to dispatch — never propagated to the
    HTTP response.

    ``action``:
        - ``"created"`` — fresh user; ``user`` and ``verification_token``
          are set.
        - ``"already_registered"`` — email exists; ``user`` is set,
          ``verification_token`` is ``None``.
    """

    action: Literal["created", "already_registered"]
    user: User
    verification_token: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def _get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Email verification (Issue #39)
# ---------------------------------------------------------------------------

_TOKEN_BYTES = 32  # 256 bits — 64 hex chars after .hex()


def _hash_token(plaintext: str) -> str:
    """SHA-256 hex digest. Plaintext token is never persisted."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


async def create_verification_token(
    db: AsyncSession,
    user: User,
) -> str:
    """Create a fresh single-use email-verification token for ``user``.

    Any previously-issued unused tokens for the same user are deleted to
    enforce "latest token wins" semantics on resend (matches the refresh
    token rotation pattern from ADR-0004).

    Returns the **plaintext** token — caller must put it into the email
    URL and never log it. Only the hash is persisted.
    """
    # Invalidate prior tokens for this user (resend semantics)
    await db.execute(
        delete(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
    )

    plaintext = secrets.token_urlsafe(_TOKEN_BYTES)
    record = EmailVerificationToken(
        user_id=user.id,
        token_hash=_hash_token(plaintext),
        expires_at=datetime.now(UTC) + timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS),
    )
    db.add(record)
    await db.flush()
    logger.info(
        "verification token issued",
        extra={"user_id": str(user.id), "token_id": str(record.id)},
    )
    return plaintext


async def verify_email(db: AsyncSession, plaintext_token: str) -> User:
    """Consume a verification token and mark the user as verified.

    Raises ``VerificationError`` for any failure mode (unknown / expired /
    used / inactive user). The error message is generic to prevent
    enumeration via timing or message comparison.
    """
    token_hash = _hash_token(plaintext_token)

    result = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()

    if token is None:
        logger.warning("verify-email: unknown token")
        raise VerificationError("Invalid or expired verification token")

    if token.used_at is not None:
        logger.warning(
            "verify-email: token replay",
            extra={"user_id": str(token.user_id), "token_id": str(token.id)},
        )
        raise VerificationError("Invalid or expired verification token")

    # expires_at is timezone-aware (DateTime(timezone=True))
    if token.expires_at < datetime.now(UTC):
        logger.info(
            "verify-email: token expired",
            extra={"user_id": str(token.user_id), "token_id": str(token.id)},
        )
        raise VerificationError("Invalid or expired verification token")

    user = await _get_user_by_id(db, token.user_id)
    if user is None or not user.is_active:
        raise VerificationError("Invalid or expired verification token")

    # Idempotent on the user side: already-verified is a no-op success
    if not user.is_verified:
        user.is_verified = True

    token.used_at = datetime.now(UTC)
    await db.flush()
    logger.info("user email verified", extra={"user_id": str(user.id)})
    return user


async def request_verification_resend(
    db: AsyncSession,
    email: str,
) -> tuple[User, str] | None:
    """Resend a verification mail for the given email if applicable.

    Returns ``(user, plaintext_token)`` if a token was minted, ``None``
    otherwise (unknown email, already verified, or inactive). The endpoint
    layer must always respond with the same generic 202 message regardless
    of return value to avoid email enumeration.
    """
    user = await _get_user_by_email(db, email)
    if user is None or not user.is_active or user.is_verified:
        return None
    plaintext = await create_verification_token(db, user)
    return user, plaintext


# ---------------------------------------------------------------------------
# Password reset (O-20)
# ---------------------------------------------------------------------------

_PASSWORD_RESET_GENERIC_ERROR = "Invalid or expired password reset token"


async def create_password_reset_token(
    db: AsyncSession,
    user: User,
) -> str:
    """Create a fresh single-use password-reset token for ``user``.

    Prior unused tokens for the same user are deleted ("latest wins").
    Returns the plaintext token for the email link — never log it.
    """
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))

    plaintext = secrets.token_urlsafe(_TOKEN_BYTES)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(plaintext),
        expires_at=datetime.now(UTC) + timedelta(hours=settings.PASSWORD_RESET_TTL_HOURS),
    )
    db.add(record)
    await db.flush()
    logger.info(
        "password reset token issued",
        extra={"user_id": str(user.id), "token_id": str(record.id)},
    )
    return plaintext


async def request_password_reset(
    db: AsyncSession,
    email: str,
) -> tuple[User, str] | None:
    """Issue a password-reset mail for verified active users only.

    Returns ``(user, plaintext_token)`` when applicable, else ``None``.
    The endpoint must always respond with the same generic 202 message.
    """
    user = await _get_user_by_email(db, email)
    if user is None or not user.is_active or not user.is_verified:
        return None
    plaintext = await create_password_reset_token(db, user)
    return user, plaintext


async def reset_password(
    db: AsyncSession,
    plaintext_token: str,
    new_password: str,
) -> User:
    """Consume a reset token and set a new password for the user."""
    token_hash = _hash_token(plaintext_token)

    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()

    if token is None:
        logger.warning("reset-password: unknown token")
        raise PasswordResetError(_PASSWORD_RESET_GENERIC_ERROR)

    if token.used_at is not None:
        logger.warning(
            "reset-password: token replay",
            extra={"user_id": str(token.user_id), "token_id": str(token.id)},
        )
        raise PasswordResetError(_PASSWORD_RESET_GENERIC_ERROR)

    if token.expires_at < datetime.now(UTC):
        logger.info(
            "reset-password: token expired",
            extra={"user_id": str(token.user_id), "token_id": str(token.id)},
        )
        raise PasswordResetError(_PASSWORD_RESET_GENERIC_ERROR)

    user = await _get_user_by_id(db, token.user_id)
    if user is None or not user.is_active:
        raise PasswordResetError(_PASSWORD_RESET_GENERIC_ERROR)

    user.hashed_password = hash_password(new_password)
    token.used_at = datetime.now(UTC)
    await db.flush()
    logger.info("user password reset", extra={"user_id": str(user.id)})
    return user


def _build_token_pair(user: User) -> tuple[str, str, str]:
    """Return (access_token, refresh_token, jti)."""
    jti = str(uuid.uuid4())
    access = create_access_token(subject=str(user.id))
    refresh = create_refresh_token(subject=str(user.id), jti=jti)
    return access, refresh, jti


async def issue_session_tokens(
    token_store: TokenStore,
    user: User,
) -> tuple[str, str]:
    """Issue a fresh access/refresh pair and persist the refresh JTI."""
    access, refresh, jti = _build_token_pair(user)
    await token_store.store(str(user.id), jti)
    return access, refresh


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


async def request_registration(
    db: AsyncSession,
    data: RegisterRequest,
) -> RegistrationOutcome:
    """Enumeration-safe entry point for ``POST /auth/register`` (Issue #65).

    Always returns a :class:`RegistrationOutcome`; never raises
    :class:`RegistrationError` for duplicate emails. The endpoint layer
    responds with the same generic 202 message in both branches so an
    attacker cannot tell whether an email is registered.

    Branches:
        - email is new → create user + DEK, return ``action="created"``
          plus the plaintext verification token to be mailed.
        - email exists → return ``action="already_registered"`` with the
          existing user; the endpoint dispatches an "already-registered"
          notice mail instead of a verification mail. No DB writes.
    """
    existing = await _get_user_by_email(db, data.email)
    if existing is not None:
        logger.info(
            "register hit existing email — enumeration-safe branch",
            extra={"user_id": str(existing.id)},
        )
        return RegistrationOutcome(
            action="already_registered",
            user=existing,
            verification_token=None,
        )

    user = await register_user(db, data)
    plaintext_token = await create_verification_token(db, user)
    return RegistrationOutcome(
        action="created",
        user=user,
        verification_token=plaintext_token,
    )


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Create a new user + provision DEK. Internal helper.

    Raises :class:`RegistrationError` on duplicate email — the endpoint
    layer no longer surfaces this as 4xx (Issue #65) but the error is
    kept for direct service-layer callers and tests. Production traffic
    goes through :func:`request_registration` which never raises.
    """
    existing = await _get_user_by_email(db, data.email)
    if existing:
        raise RegistrationError("Email already registered")

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        display_name=data.display_name,
        is_active=True,
        is_verified=False,  # requires email verification
    )
    db.add(user)
    await db.flush()  # get the generated UUID without committing
    await bind_rls_current_user(db, user.id)

    # Issue #26: provision a per-user Data-Encryption-Key (DEK) wrapped
    # by the master MultiFernet. The plaintext DEK never touches disk —
    # it is unwrapped on demand inside the request via auth dependency.
    dek = generate_dek()
    db.add(
        UserEncryptionKey(
            user_id=user.id,
            wrapped_dek=wrap_dek(dek),
            key_version=1,
        )
    )
    await db.flush()
    # Wipe the local plaintext reference; GC will collect.
    del dek

    logger.info("user registered", extra={"user_id": str(user.id)})
    return user


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def login_user(
    db: AsyncSession,
    token_store: TokenStore,
    email: str,
    password: str,
) -> tuple[str, str, User]:
    """Verify credentials and return (access_token, refresh_token, user).
    Raises AuthError on invalid credentials.
    """
    user = await _get_user_by_email(db, email)

    # Constant-time path: always verify even if user not found to prevent
    # timing-based user enumeration.
    valid = verify_password(
        password,
        user.hashed_password if user else _DUMMY_PASSWORD_HASH,
    )

    if not valid or not user:
        logger.warning("failed login attempt", extra={"email_domain": email.split("@")[-1]})
        raise AuthError("Invalid credentials")

    if not user.is_active:
        raise AuthError("Account is disabled")

    if not user.is_verified:
        logger.info(
            "login blocked: email not verified",
            extra={"user_id": str(user.id)},
        )
        raise EmailNotVerifiedError("Email not verified")

    access, refresh = await issue_session_tokens(token_store, user)

    logger.info("user logged in", extra={"user_id": str(user.id)})
    return access, refresh, user


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


async def refresh_tokens(
    db: AsyncSession,
    token_store: TokenStore,
    refresh_token: str,
) -> tuple[str, str, User]:
    """Validate refresh token, rotate it, return new token pair."""
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise AuthError("Invalid or expired refresh token") from exc

    if payload.get("type") != "refresh":
        raise AuthError("Wrong token type")

    user_id_str: str = payload.get("sub", "")
    jti: str = payload.get("jti", "")

    if not user_id_str or not jti:
        raise AuthError("Malformed token")

    if not await token_store.is_valid(user_id_str, jti):
        # Token already used or revoked — possible replay attack
        logger.warning("refresh token replay attempt", extra={"user_id": user_id_str})
        # Revoke ALL tokens for this user as precaution
        await token_store.revoke_all(user_id_str)
        raise AuthError("Refresh token already used or revoked")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise AuthError("Malformed token") from exc

    user = await _get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise AuthError("User not found or disabled")

    new_access, new_refresh, new_jti = _build_token_pair(user)
    await token_store.rotate(user_id_str, jti, new_jti)

    logger.info("tokens refreshed", extra={"user_id": str(user.id)})
    return new_access, new_refresh, user


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def logout_user(
    token_store: TokenStore,
    refresh_token: str,
) -> None:
    """Invalidate the refresh token. Best-effort — no error if already gone."""
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id_str = payload.get("sub", "")
        jti = payload.get("jti", "")
        if user_id_str and jti:
            await token_store.revoke(user_id_str, jti)
            logger.info("user logged out", extra={"user_id": user_id_str})
    except JWTError:
        # Token already expired — logout is still successful from user's POV
        pass

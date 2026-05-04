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

import logging
import uuid

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.db.redis_client import TokenStore
from app.models.user import User
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)
_DUMMY_PASSWORD_HASH = hash_password("__moodsync_dummy_password__")

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Base auth error — maps to HTTP 401."""


class RegistrationError(Exception):
    """Maps to HTTP 409 (conflict) or HTTP 422 (validation)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def _get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def _build_token_pair(user: User) -> tuple[str, str, str]:
    """Return (access_token, refresh_token, jti)."""
    jti = str(uuid.uuid4())
    access = create_access_token(subject=str(user.id))
    refresh = create_refresh_token(subject=str(user.id), jti=jti)
    return access, refresh, jti


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
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

    access, refresh, jti = _build_token_pair(user)
    await token_store.store(str(user.id), jti)

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

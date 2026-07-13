"""FastAPI dependencies for authentication.

``get_current_user``     — requires valid access token, returns active User
``get_current_user_lax`` — returns None if unauthenticated (optional auth)

Token extraction order:
1. HttpOnly cookie  ``access_token``  (primary — browser clients)
2. Authorization header  ``Bearer <token>``  (API / mobile clients)

Issue #26 — App-Level at-rest encryption:
After resolving the User, this dependency unwraps the per-user Data
Encryption Key (DEK) from the ``user_encryption_keys`` table and binds
it into a request-scoped ``ContextVar`` via
:func:`app.core.crypto.set_current_user_dek`. The DEK is reset on
request completion through the ``yield``/``finally`` pattern so that no
plaintext key material leaks into worker reuse or concurrent requests.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import (
    DecryptionError,
    reset_current_user_dek,
    set_current_user_dek,
    unwrap_dek,
)
from app.core.security import decode_token
from app.db.session import bind_rls_current_user, get_session
from app.models.user import User
from app.models.user_encryption_key import UserEncryptionKey

logger = logging.getLogger(__name__)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _resolve_user(token: str, db: AsyncSession) -> User:
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != "access":
        raise _CREDENTIALS_EXCEPTION

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user


async def _load_and_bind_dek(db: AsyncSession, user: User) -> object | None:
    """Fetch the user's wrapped DEK, unwrap it, and bind it to the request
    ContextVar.

    Returns the ``contextvars.Token`` for cleanup, or ``None`` when no key
    record exists yet (e.g. legacy users created before migration 007 —
    should not happen post-deploy because the migration backfills, but
    we degrade gracefully so login still works for diagnostics).
    """
    result = await db.execute(select(UserEncryptionKey).where(UserEncryptionKey.user_id == user.id))
    record = result.scalar_one_or_none()
    if record is None:
        logger.error(
            "missing user_encryption_keys row — encrypted fields will fail",
            extra={"user_id": str(user.id)},
        )
        return None

    try:
        dek = unwrap_dek(record.wrapped_dek)
    except DecryptionError:
        # Master key rotated incorrectly or DB tampering. Surface as 401
        # rather than 500 to avoid leaking crypto details.
        logger.error(
            "failed to unwrap DEK — master key mismatch?",
            extra={"user_id": str(user.id)},
        )
        raise _CREDENTIALS_EXCEPTION from None

    return set_current_user_dek(user.id, dek)


async def get_current_user(
    db: AsyncSession = Depends(get_session),
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> AsyncIterator[User]:
    """Require a valid access token. Raises 401 if missing or invalid.

    On success, also unwraps the user's DEK and binds it to a
    request-scoped ``ContextVar`` (Issue #26). The DEK is reset after the
    response is sent.
    """
    token: str | None = None

    if access_token:
        token = access_token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise _CREDENTIALS_EXCEPTION

    user = await _resolve_user(token, db)
    await bind_rls_current_user(db, user.id)
    dek_token = await _load_and_bind_dek(db, user)
    try:
        yield user
    finally:
        if dek_token is not None:
            reset_current_user_dek(dek_token)  # type: ignore[arg-type]


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Like get_current_user but also requires email verification."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified",
        )
    return current_user


async def get_current_insight_trigger_admin(
    current_user: User = Depends(get_current_verified_user),
) -> User:
    """Require a verified user whose email is listed in INSIGHT_TRIGGER_ADMIN_EMAILS."""
    from app.core.config import settings

    allowed = settings.INSIGHT_TRIGGER_ADMIN_EMAILS
    if not allowed or current_user.email.casefold() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insight trigger requires admin privileges",
        )
    return current_user

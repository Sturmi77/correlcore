"""FastAPI dependencies for authentication.

``get_current_user``     — requires valid access token, returns active User
``get_current_user_lax`` — returns None if unauthenticated (optional auth)

Token extraction order:
1. HttpOnly cookie  ``access_token``  (primary — browser clients)
2. Authorization header  ``Bearer <token>``  (API / mobile clients)
"""

from __future__ import annotations

import logging
import uuid

from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User

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


async def get_current_user(
    db: AsyncSession = Depends(get_session),
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> User:
    """Require a valid access token. Raises 401 if missing or invalid."""
    token: str | None = None

    if access_token:
        token = access_token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise _CREDENTIALS_EXCEPTION

    return await _resolve_user(token, db)


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

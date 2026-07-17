"""Security utilities: JWT creation/verification, password hashing.

ADR-0004: Phase 1 — Native JWT with refresh-token rotation.
All refresh tokens stored in Redis (single-use via JTI).

Password hashing uses the ``bcrypt`` library directly. ``passlib``'s bcrypt
backend runs a wraparound self-test with a >72-byte secret that raises on
bcrypt ≥ 4.1 (and blocks API startup after Dependabot allowed bcrypt 5.x).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import bcrypt
from jose import jwt

from app.core.config import settings

# bcrypt truncates at 72 bytes; keep explicit for hash/verify parity.
_BCRYPT_MAX_SECRET_BYTES = 72
_BCRYPT_ROUNDS = 12


def _secret_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_SECRET_BYTES]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_secret_bytes(plain_password), hashed_password.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def hash_password(password: str) -> str:
    digest = bcrypt.hashpw(_secret_bytes(password), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return digest.decode("utf-8")


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """Create a short-lived access token (15 min by default)."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return cast(str, jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM))


def create_refresh_token(subject: str, jti: str) -> str:
    """Create a long-lived refresh token with a caller-supplied JTI.

    The JTI is stored in Redis by the TokenStore. Supplying it from the
    caller allows the service layer to atomically store the key before
    returning the token to the client.
    """
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
        "jti": jti,
    }
    return cast(str, jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM))


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises JWTError on invalid/expired tokens."""
    return cast(
        dict[str, Any],
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]),
    )

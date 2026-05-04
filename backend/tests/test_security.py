"""Unit tests for app.core.security (CQR-3, Issue #64).

Covers:
- bcrypt roundtrip via hash_password / verify_password
- JWT roundtrip for access and refresh tokens (incl. extra payload)
- Expired access token raises JWTError
- Wrong/altered signature raises JWTError
- Refresh token preserves caller-supplied JTI
- Token type is set correctly ("access" vs "refresh")
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def test_hash_password_returns_bcrypt_hash() -> None:
    digest = hash_password("super-secret-pw")
    # bcrypt identifier prefix
    assert digest.startswith("$2b$") or digest.startswith("$2a$") or digest.startswith("$2y$")
    assert digest != "super-secret-pw"


def test_verify_password_accepts_correct_password() -> None:
    digest = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", digest) is True


def test_verify_password_rejects_wrong_password() -> None:
    digest = hash_password("correct horse battery staple")
    assert verify_password("wrong-password", digest) is False


def test_hash_password_is_salted() -> None:
    """Two hashes of the same password must differ (random salt)."""
    a = hash_password("same-password")
    b = hash_password("same-password")
    assert a != b
    # but both verify
    assert verify_password("same-password", a) is True
    assert verify_password("same-password", b) is True


# ---------------------------------------------------------------------------
# JWT — access token
# ---------------------------------------------------------------------------


def test_create_access_token_roundtrip() -> None:
    token = create_access_token(subject="user-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload
    assert "iat" in payload


def test_create_access_token_merges_extra_claims() -> None:
    token = create_access_token(subject="user-1", extra={"role": "admin", "scope": "rw"})
    payload = decode_token(token)
    assert payload["role"] == "admin"
    assert payload["scope"] == "rw"
    assert payload["sub"] == "user-1"
    assert payload["type"] == "access"


def test_create_access_token_jti_is_unique() -> None:
    a = decode_token(create_access_token(subject="u"))
    b = decode_token(create_access_token(subject="u"))
    assert a["jti"] != b["jti"]


# ---------------------------------------------------------------------------
# JWT — refresh token
# ---------------------------------------------------------------------------


def test_create_refresh_token_uses_supplied_jti() -> None:
    jti = str(uuid.uuid4())
    token = create_refresh_token(subject="user-7", jti=jti)
    payload = decode_token(token)
    assert payload["sub"] == "user-7"
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_create_refresh_token_has_longer_expiry_than_access() -> None:
    access = decode_token(create_access_token(subject="u"))
    refresh = decode_token(create_refresh_token(subject="u", jti="x"))
    # refresh exp must be strictly later (days vs minutes)
    assert refresh["exp"] > access["exp"]


# ---------------------------------------------------------------------------
# JWT — failure modes
# ---------------------------------------------------------------------------


def test_decode_token_rejects_expired_token() -> None:
    """Manually craft an already-expired JWT and ensure decode_token raises."""
    payload: dict[str, Any] = {
        "sub": "user-x",
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    expired = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(JWTError):
        decode_token(expired)


def test_decode_token_rejects_wrong_signature() -> None:
    token = create_access_token(subject="user-1")
    # Replace the entire signature segment with a different-but-valid-base64 string.
    header_payload, _sig = token.rsplit(".", 1)
    tampered = header_payload + "." + "A" * len(_sig)
    with pytest.raises(JWTError):
        decode_token(tampered)


def test_decode_token_rejects_token_signed_with_other_secret() -> None:
    payload: dict[str, Any] = {
        "sub": "user-x",
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    foreign = jwt.encode(
        payload, "totally-different-secret-key-32-bytes!!", algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(JWTError):
        decode_token(foreign)


def test_decode_token_rejects_garbage() -> None:
    with pytest.raises(JWTError):
        decode_token("not-a-jwt-at-all")

"""Tests for ``app.api.v1.deps.auth`` (Issue #64).

Targets the FastAPI auth dependency that resolves the User from the
access token, unwraps the per-user DEK and binds it into the
request-scoped ``ContextVar`` for the request lifetime (Issue #26).

DB and Redis are mocked. Tests cover Cookie-vs-Bearer extraction, the
DEK happy path / unwrap-error path / missing-key-row degrade path, and
the ``get_current_verified_user`` gate (CQR-2).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from jose import jwt

from app.api.v1.deps.auth import (
    _load_and_bind_dek,
    _resolve_user,
    get_current_verified_user,
    require_admin,
)
from app.core.config import settings
from app.core.crypto import DecryptionError
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.models.user_encryption_key import UserEncryptionKey
from tests.conftest import make_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(scalar_one_or_none: object = None) -> MagicMock:
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    db.execute = AsyncMock(return_value=result)
    return db


def _build_expired_access_token(user_id: uuid.UUID) -> str:
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) - timedelta(minutes=5),
        "iat": datetime.now(UTC) - timedelta(hours=1),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# _resolve_user — token validation branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_user_rejects_garbage_token() -> None:
    db = _make_db()
    with pytest.raises(HTTPException) as exc_info:
        await _resolve_user("not.a.jwt", db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_user_rejects_expired_access_token() -> None:
    user = make_user()
    token = _build_expired_access_token(user.id)
    db = _make_db()
    with pytest.raises(HTTPException) as exc_info:
        await _resolve_user(token, db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_user_rejects_refresh_token_used_as_access() -> None:
    """A refresh token must not work on access-protected endpoints."""
    user = make_user()
    refresh = create_refresh_token(subject=str(user.id), jti=str(uuid.uuid4()))
    db = _make_db()
    with pytest.raises(HTTPException) as exc_info:
        await _resolve_user(refresh, db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_user_rejects_token_with_non_uuid_subject() -> None:
    """An access token with a non-UUID `sub` is rejected before DB lookup."""
    payload = {
        "sub": "not-a-uuid",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iat": datetime.now(UTC),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    bad = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    db = _make_db()
    with pytest.raises(HTTPException) as exc_info:
        await _resolve_user(bad, db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_user_rejects_token_without_subject() -> None:
    payload = {
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iat": datetime.now(UTC),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    bad = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    db = _make_db()
    with pytest.raises(HTTPException) as exc_info:
        await _resolve_user(bad, db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_user_rejects_unknown_user_id() -> None:
    """Token signs a UUID that no row matches → 401, not 500."""
    user = make_user()
    token = create_access_token(subject=str(user.id))
    db = _make_db(scalar_one_or_none=None)
    with pytest.raises(HTTPException) as exc_info:
        await _resolve_user(token, db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_user_rejects_inactive_user() -> None:
    user = make_user(active=False)
    token = create_access_token(subject=str(user.id))
    db = _make_db(scalar_one_or_none=user)
    with pytest.raises(HTTPException) as exc_info:
        await _resolve_user(token, db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_user_returns_active_user() -> None:
    user = make_user(active=True)
    token = create_access_token(subject=str(user.id))
    db = _make_db(scalar_one_or_none=user)
    returned = await _resolve_user(token, db)
    assert returned is user


# ---------------------------------------------------------------------------
# _load_and_bind_dek — happy / missing-row / unwrap-error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_and_bind_dek_returns_none_when_row_missing() -> None:
    """Legacy users without a key row degrade gracefully (no crash, no DEK)."""
    user = make_user()
    db = _make_db(scalar_one_or_none=None)
    token = await _load_and_bind_dek(db, user)
    assert token is None


@pytest.mark.asyncio
async def test_load_and_bind_dek_raises_401_on_unwrap_failure() -> None:
    """A `DecryptionError` from `unwrap_dek` is converted to 401, never 500.

    This is the master-key-rotation-mismatch path; we must not leak the
    crypto detail to the client.
    """
    user = make_user()
    rec = MagicMock(spec=UserEncryptionKey)
    rec.wrapped_dek = b"corrupt-or-wrong-key"
    db = _make_db(scalar_one_or_none=rec)

    with patch(
        "app.api.v1.deps.auth.unwrap_dek",
        side_effect=DecryptionError("bad key"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await _load_and_bind_dek(db, user)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_load_and_bind_dek_binds_context_var_on_happy_path() -> None:
    user = make_user()
    rec = MagicMock(spec=UserEncryptionKey)
    rec.wrapped_dek = b"wrapped"
    db = _make_db(scalar_one_or_none=rec)

    with (
        patch(
            "app.api.v1.deps.auth.unwrap_dek",
            return_value=b"\x01" * 32,
        ),
        patch(
            "app.api.v1.deps.auth.set_current_user_dek",
            return_value="cv-token-handle",
        ) as mock_set,
    ):
        result = await _load_and_bind_dek(db, user)

    assert result == "cv-token-handle"
    mock_set.assert_called_once()


# ---------------------------------------------------------------------------
# get_current_verified_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_verified_user_passes_through_for_verified() -> None:
    user = make_user(verified=True)
    returned = await get_current_verified_user(current_user=user)
    assert returned is user


@pytest.mark.asyncio
async def test_get_current_verified_user_blocks_unverified_with_403() -> None:
    user = make_user(verified=False)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_verified_user(current_user=user)
    assert exc_info.value.status_code == 403
    assert "not verified" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# require_admin (#677 admin console)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_passes_through_for_admin() -> None:
    user = make_user(verified=True)
    user.is_admin = True
    returned = await require_admin(current_user=user)
    assert returned is user


@pytest.mark.asyncio
async def test_require_admin_blocks_non_admin_with_403() -> None:
    user = make_user(verified=True)
    user.is_admin = False
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=user)
    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Endpoint integration — Cookie vs Bearer extraction + finally-cleanup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_accepts_bearer_header(async_client: AsyncClient) -> None:
    """The Bearer-token branch (API / mobile) reaches /me without a cookie."""
    user = make_user()

    async def fake_resolve(token: str, db: Any) -> User:
        return user

    async def fake_load_and_bind(db: Any, u: User) -> object | None:
        return None  # exercise the "no DEK row" cleanup branch (token is None)

    with (
        patch("app.api.v1.deps.auth._resolve_user", side_effect=fake_resolve),
        patch("app.api.v1.deps.auth.bind_rls_current_user", new_callable=AsyncMock),
        patch("app.api.v1.deps.auth._load_and_bind_dek", side_effect=fake_load_and_bind),
    ):
        r = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer some-access-jwt"},
        )
    assert r.status_code == 200
    assert r.json()["email"] == user.email


@pytest.mark.asyncio
async def test_get_current_user_resets_dek_after_response(
    async_client: AsyncClient,
) -> None:
    """The yield/finally pattern must call ``reset_current_user_dek`` exactly
    once when ``_load_and_bind_dek`` returned a non-None handle.
    """
    user = make_user()

    async def fake_resolve(token: str, db: Any) -> User:
        return user

    async def fake_load_and_bind(db: Any, u: User) -> object | None:
        return "context-token-handle"

    with (
        patch("app.api.v1.deps.auth._resolve_user", side_effect=fake_resolve),
        patch("app.api.v1.deps.auth.bind_rls_current_user", new_callable=AsyncMock),
        patch("app.api.v1.deps.auth._load_and_bind_dek", side_effect=fake_load_and_bind),
        patch("app.api.v1.deps.auth.reset_current_user_dek") as mock_reset,
    ):
        r = await async_client.get(
            "/api/v1/auth/me",
            cookies={"access_token": "cookie-jwt"},
        )

    assert r.status_code == 200
    mock_reset.assert_called_once_with("context-token-handle")


@pytest.mark.asyncio
async def test_get_current_user_returns_401_without_token(
    async_client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No cookie, no Bearer header → 401 before any DB call.

    Client detail stays opaque; ops logs must carry ``auth_fail_reason`` so
    Secure-cookie-discard vs bad JWT can be distinguished without guessing.
    """
    with caplog.at_level("INFO", logger="app.api.v1.deps.auth"):
        r = await async_client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "Could not validate credentials"
    # Homelab/staging: reason visible in Network tab (not in production).
    assert r.headers.get("x-auth-fail-reason") == "missing_access_token"
    assert any(
        getattr(rec, "auth_fail_reason", None) == "missing_access_token"
        or "missing_access_token" in rec.getMessage()
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_get_current_user_ignores_non_bearer_authorization(
    async_client: AsyncClient,
) -> None:
    """An ``Authorization`` header that does not start with ``Bearer ``
    must not be treated as a token (no Basic-auth surprise)."""
    r = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic abc"},
    )
    assert r.status_code == 401

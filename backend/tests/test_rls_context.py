"""Regression coverage for PostgreSQL RLS request binding."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.db.session import bind_rls_current_user
from tests.conftest import make_user


@pytest.mark.asyncio
async def test_bind_rls_current_user_sets_transaction_local_guc() -> None:
    db = MagicMock()
    db.execute = AsyncMock()
    user_id = uuid.uuid4()

    await bind_rls_current_user(db, user_id)

    db.execute.assert_awaited_once()
    statement, params = db.execute.await_args.args
    assert "set_config('app.current_user_id'" in str(statement)
    assert "true" in str(statement)
    assert params == {"user_id": str(user_id)}


@pytest.mark.asyncio
async def test_get_current_user_binds_rls_before_loading_dek(async_client: AsyncClient) -> None:
    user = make_user()
    calls: list[str] = []

    async def fake_resolve(token: str, db: object) -> object:
        calls.append("resolve")
        return user

    async def fake_bind(db: object, user_id: uuid.UUID) -> None:
        calls.append("bind_rls")
        assert user_id == user.id

    async def fake_load_and_bind(db: object, u: object) -> object | None:
        calls.append("load_dek")
        return None

    with (
        patch("app.api.v1.deps.auth._resolve_user", side_effect=fake_resolve),
        patch("app.api.v1.deps.auth.bind_rls_current_user", side_effect=fake_bind),
        patch("app.api.v1.deps.auth._load_and_bind_dek", side_effect=fake_load_and_bind),
    ):
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer some-access-jwt"},
        )

    assert response.status_code == 200
    assert calls == ["resolve", "bind_rls", "load_dek"]

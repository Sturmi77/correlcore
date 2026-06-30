"""Tests for sync_conflicts storage and read API (M4.1 Sprint 1, Issue #24)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.sync_conflict import SyncConflict
from app.models.user import User
from app.services.sync_conflict_service import (
    cleanup_stale_sync_conflicts,
    create_sync_conflict,
    list_sync_conflicts,
    sanitize_conflict_value,
)
from tests.conftest import make_user


def _scalars_result(values: list[object]) -> MagicMock:
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _make_conflict(
    user: User,
    *,
    field_name: str = "mood_score",
    entity_type: str = "entry",
    created_at: datetime | None = None,
    client_value: dict | None = None,
    server_value: dict | None = None,
) -> SyncConflict:
    now = created_at or datetime.now(UTC)
    row = SyncConflict()
    row.id = uuid.uuid4()
    row.user_id = user.id
    row.entity_id = uuid.uuid4()
    row.entity_type = entity_type
    row.field_name = field_name
    row.client_value = client_value if client_value is not None else {"value": 4}
    row.server_value = server_value if server_value is not None else {"value": 3}
    row.client_ts = now
    row.server_ts = now - timedelta(minutes=1)
    row.resolved_at = None
    row.created_at = now
    return row


def test_sanitize_conflict_value_redacts_note_plaintext_keys() -> None:
    redacted = sanitize_conflict_value(
        "note",
        {"text": "secret headache note", "present": True},
    )
    assert redacted == {"present": True, "changed": True, "redacted": True}
    assert "secret" not in str(redacted)


def test_sanitize_conflict_value_redacts_mood_values() -> None:
    assert sanitize_conflict_value("mood_score", {"value": 4}) == {
        "changed": True,
        "redacted": True,
    }
    assert sanitize_conflict_value("symptoms", {"map": {"id": 2}}) == {
        "changed": True,
        "redacted": True,
    }


@pytest.mark.asyncio
async def test_create_sync_conflict_sanitizes_note_before_persist() -> None:
    user = make_user()
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    row = await create_sync_conflict(
        db,
        user_id=user.id,
        entity_id=uuid.uuid4(),
        entity_type="entry",
        field_name="note",
        client_value={"text": "should not persist"},
        server_value={"note": "also blocked"},
        client_ts=datetime.now(UTC),
        server_ts=datetime.now(UTC),
    )

    assert row.client_value == {"present": True, "changed": True, "redacted": True}
    assert row.server_value == {"present": True, "changed": True, "redacted": True}
    db.add.assert_called_once_with(row)


@pytest.mark.asyncio
async def test_list_sync_conflicts_applies_entity_filter_and_pagination() -> None:
    user = make_user()
    row = _make_conflict(user)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_result(1), _scalars_result([row])])

    rows, total = await list_sync_conflicts(
        db,
        user_id=user.id,
        entity_type="entry",
        limit=10,
        offset=5,
    )

    assert total == 1
    assert rows == [row]
    list_stmt = db.execute.await_args_list[1].args[0]
    compiled = str(list_stmt)
    assert "sync_conflicts.entity_type" in compiled
    assert list_stmt._limit_clause.value == 10  # type: ignore[attr-defined]
    assert list_stmt._offset_clause.value == 5  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_cleanup_stale_sync_conflicts_deletes_rows_before_threshold() -> None:
    stale_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_result([stale_id]))

    deleted = await cleanup_stale_sync_conflicts(
        db,
        now=datetime(2026, 6, 30, tzinfo=UTC),
        retention_days=90,
    )

    assert deleted == 1
    stmt = db.execute.await_args.args[0]
    assert "sync_conflicts.created_at <" in str(stmt.whereclause)
    assert stmt.compile().params["created_at_1"] == datetime(2026, 4, 1, tzinfo=UTC)


@pytest.mark.asyncio
async def test_sync_conflicts_endpoint_requires_verified_user(
    async_client: AsyncClient,
) -> None:
    r = await async_client.get("/api/v1/user/sync-conflicts")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_sync_conflicts_endpoint_returns_paginated_rows(
    async_client: AsyncClient,
) -> None:
    user = make_user()
    row = _make_conflict(
        user,
        field_name="note",
        client_value={"present": True, "changed": True},
        server_value={"present": False},
    )

    async def override_user() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override_user

    with patch(
        "app.api.v1.endpoints.user.list_sync_conflicts",
        new_callable=AsyncMock,
        return_value=([row], 1),
    ):
        try:
            r = await async_client.get("/api/v1/user/sync-conflicts?entity_type=entry&limit=20")
        finally:
            app.dependency_overrides.pop(get_current_verified_user, None)

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["field_name"] == "note"
    assert item["entity_type"] == "entry"
    assert "text" not in item["client_value"]
    assert "note" not in item["client_value"]


@pytest.mark.asyncio
async def test_sync_conflicts_endpoint_never_returns_decrypted_note_text(
    async_client: AsyncClient,
) -> None:
    user = make_user()
    row = _make_conflict(
        user,
        field_name="note",
        client_value={"text": "migraine flare-up"},
        server_value={"plaintext": "old note"},
    )

    async def override_user() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override_user

    with patch(
        "app.api.v1.endpoints.user.list_sync_conflicts",
        new_callable=AsyncMock,
        return_value=([row], 1),
    ):
        try:
            r = await async_client.get("/api/v1/user/sync-conflicts")
        finally:
            app.dependency_overrides.pop(get_current_verified_user, None)

    payload = r.text
    assert "migraine" not in payload
    assert "old note" not in payload
    item = r.json()["items"][0]
    assert item["client_value"]["redacted"] is True
    assert item["server_value"]["redacted"] is True


def test_migration_017_declares_sync_conflicts_table() -> None:
    path = Path(__file__).resolve().parents[1] / "migrations/versions/017_add_sync_conflicts.py"
    source = path.read_text(encoding="utf-8")
    assert 'revision: str = "017"' in source
    assert 'down_revision: str | None = "016"' in source
    assert 'op.create_table(\n        "sync_conflicts"' in source
    assert "ck_sync_conflicts_entity_type" in source

"""Tests for offline sync push/pull (M4.1 Sprint 2, Issue #10)."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.crypto import reset_current_user_dek, set_current_user_dek, unwrap_dek
from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.entry import Entry, EntrySlot, WorkContext
from app.models.sync_conflict import SyncConflict
from app.models.user_encryption_key import UserEncryptionKey
from app.schemas.auth import RegisterRequest
from app.schemas.sync import SyncChange, SyncPushRequest
from app.services.auth_service import register_user
from app.services.sync_service import (
    SyncBadRequestError,
    decode_cursor,
    encode_cursor,
    pull_changes,
    push_changes,
)
from tests.conftest import make_user


async def _dek_token_for_user(session, user_id: uuid.UUID):
    wrapped = (
        await session.execute(
            select(UserEncryptionKey.wrapped_dek).where(UserEncryptionKey.user_id == user_id)
        )
    ).scalar_one()
    return set_current_user_dek(user_id, unwrap_dek(wrapped))


def _integration_enabled() -> bool:
    return os.getenv("CORRELCORE_RUN_INTEGRATION") == "1"


def _entry_change(
    *,
    entry_id: uuid.UUID,
    seq: int,
    mood_score: int = 3,
    updated_at: datetime,
) -> SyncChange:
    return SyncChange(
        seq=seq,
        id=entry_id,
        table="entries",
        operation="upsert",
        data={
            "entry_date": date.today().isoformat(),
            "slot": EntrySlot.DAY.value,
            "mood_score": mood_score,
            "energy": 3,
            "stress": 2,
            "work_context": WorkContext.HOMEOFFICE.value,
            "note": None,
            "tag_ids": [],
            "symptoms": {},
        },
        updated_at=updated_at,
    )


@pytest.fixture(autouse=True)
async def dispose_async_engine_after_integration_test() -> None:
    yield
    from app.db.session import engine

    await engine.dispose()


def test_encode_decode_cursor_round_trip() -> None:
    wall = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)
    cursor = encode_cursor(user_rev=42, wall=wall)
    user_rev, decoded_wall = decode_cursor(cursor)
    assert user_rev == 42
    assert decoded_wall == wall


def test_decode_cursor_rejects_garbage() -> None:
    with pytest.raises(SyncBadRequestError):
        decode_cursor("not-a-valid-cursor")


@pytest.mark.asyncio
async def test_push_idempotency_replays_stored_batch() -> None:
    user = make_user()
    client_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    request = SyncPushRequest(
        client_id=client_id,
        batch_id=batch_id,
        changes=[
            _entry_change(
                entry_id=uuid.uuid4(),
                seq=1,
                updated_at=datetime.now(UTC),
            )
        ],
    )

    stored_response = MagicMock()
    stored_response.cursor = "stored"
    stored_response.applied = 1
    stored_response.skipped = 0
    stored_response.conflicts = []

    db = MagicMock()
    with (
        patch(
            "app.services.sync_service._get_existing_batch",
            new_callable=AsyncMock,
            return_value=MagicMock(
                cursor="stored",
                applied=1,
                skipped=0,
                conflicts=[],
            ),
        ),
        patch("app.services.sync_service._get_client_state", new_callable=AsyncMock),
    ):
        response = await push_changes(db, user_id=user.id, request=request)

    assert response.idempotent_replay is True
    assert response.cursor == "stored"
    assert response.applied == 1


@pytest.mark.asyncio
async def test_sync_push_endpoint_requires_verified_user(async_client: AsyncClient) -> None:
    payload = {
        "client_id": str(uuid.uuid4()),
        "batch_id": str(uuid.uuid4()),
        "changes": [],
    }
    response = await async_client.post("/api/v1/sync/push", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sync_pull_endpoint_requires_verified_user(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/sync/pull")
    assert response.status_code == 401


def test_migration_018_declares_sync_engine_tables() -> None:
    path = Path(__file__).resolve().parents[1] / "migrations/versions/018_add_sync_engine_infrastructure.py"
    source = path.read_text(encoding="utf-8")
    assert 'revision: str = "018"' in source
    assert "sync_revision_log" in source
    assert "sync_push_batches" in source


@pytest.mark.integration
@pytest.mark.asyncio
async def test_push_new_entry_visible_in_database() -> None:
    if not _integration_enabled():
        pytest.skip("requires PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    entry_id = uuid.uuid4()
    client_id = uuid.uuid4()
    email = f"sync-push-{uuid.uuid4().hex[:8]}@localhost.dev"

    async with AsyncSessionLocal() as session:
        user = await register_user(
            session,
            RegisterRequest(email=email, password="test-password-12", display_name="Sync"),
        )
        user.is_verified = True
        await session.commit()

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user.id)
        dek_token = await _dek_token_for_user(session, user.id)
        try:
            response = await push_changes(
                session,
                user_id=user.id,
                request=SyncPushRequest(
                    client_id=client_id,
                    batch_id=uuid.uuid4(),
                    changes=[
                        _entry_change(
                            entry_id=entry_id,
                            seq=1,
                            mood_score=4,
                            updated_at=datetime.now(UTC),
                        )
                    ],
                ),
            )
            await session.commit()
        finally:
            reset_current_user_dek(dek_token)

    assert response.applied == 1

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user.id)
        entry = (
            await session.execute(select(Entry).where(Entry.id == entry_id, Entry.user_id == user.id))
        ).scalar_one_or_none()
        assert entry is not None
        assert entry.mood_score == 4


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pull_returns_only_changes_after_cursor() -> None:
    if not _integration_enabled():
        pytest.skip("requires PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    client_id = uuid.uuid4()
    email = f"sync-pull-{uuid.uuid4().hex[:8]}@localhost.dev"
    first_id = uuid.uuid4()
    second_id = uuid.uuid4()
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as session:
        user = await register_user(
            session,
            RegisterRequest(email=email, password="test-password-12", display_name="Sync"),
        )
        user.is_verified = True
        await session.commit()

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user.id)
        dek_token = await _dek_token_for_user(session, user.id)
        try:
            await push_changes(
                session,
                user_id=user.id,
                request=SyncPushRequest(
                    client_id=client_id,
                    batch_id=uuid.uuid4(),
                    changes=[_entry_change(entry_id=first_id, seq=1, updated_at=now)],
                ),
            )
            first_pull = await pull_changes(session, user_id=user.id, since=None, limit=10)
            await push_changes(
                session,
                user_id=user.id,
                request=SyncPushRequest(
                    client_id=client_id,
                    batch_id=uuid.uuid4(),
                    changes=[
                        _entry_change(
                            entry_id=second_id,
                            seq=2,
                            mood_score=5,
                            updated_at=now + timedelta(seconds=1),
                        )
                    ],
                ),
            )
            second_pull = await pull_changes(
                session,
                user_id=user.id,
                since=first_pull.cursor,
                limit=10,
            )
            await session.commit()
        finally:
            reset_current_user_dek(dek_token)

    assert len(first_pull.changes) == 1
    assert first_pull.changes[0].id == first_id
    assert len(second_pull.changes) == 1
    assert second_pull.changes[0].id == second_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stale_client_edit_logs_conflict_and_keeps_server_value() -> None:
    if not _integration_enabled():
        pytest.skip("requires PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    entry_id = uuid.uuid4()
    client_id = uuid.uuid4()
    email = f"sync-conflict-{uuid.uuid4().hex[:8]}@localhost.dev"
    server_time = datetime.now(UTC)
    stale_time = server_time - timedelta(minutes=5)

    async with AsyncSessionLocal() as session:
        user = await register_user(
            session,
            RegisterRequest(email=email, password="test-password-12", display_name="Sync"),
        )
        user.is_verified = True
        await session.commit()

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user.id)
        dek_token = await _dek_token_for_user(session, user.id)
        try:
            await push_changes(
                session,
                user_id=user.id,
                request=SyncPushRequest(
                    client_id=client_id,
                    batch_id=uuid.uuid4(),
                    changes=[
                        _entry_change(
                            entry_id=entry_id,
                            seq=1,
                            mood_score=3,
                            updated_at=server_time,
                        )
                    ],
                ),
            )
            response = await push_changes(
                session,
                user_id=user.id,
                request=SyncPushRequest(
                    client_id=uuid.uuid4(),
                    batch_id=uuid.uuid4(),
                    changes=[
                        _entry_change(
                            entry_id=entry_id,
                            seq=1,
                            mood_score=5,
                            updated_at=stale_time,
                        )
                    ],
                ),
            )
            conflicts = (
                await session.execute(
                    select(SyncConflict).where(
                        SyncConflict.user_id == user.id,
                        SyncConflict.entity_id == entry_id,
                    )
                )
            ).scalars().all()
            entry = (
                await session.execute(select(Entry).where(Entry.id == entry_id))
            ).scalar_one()
            await session.commit()
        finally:
            reset_current_user_dek(dek_token)

    assert response.conflicts
    assert response.conflicts[0].field_name == "mood_score"
    assert len(conflicts) == 1
    assert entry.mood_score == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_push_batch_replay_is_idempotent() -> None:
    if not _integration_enabled():
        pytest.skip("requires PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    entry_id = uuid.uuid4()
    client_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    email = f"sync-idem-{uuid.uuid4().hex[:8]}@localhost.dev"

    async with AsyncSessionLocal() as session:
        user = await register_user(
            session,
            RegisterRequest(email=email, password="test-password-12", display_name="Sync"),
        )
        user.is_verified = True
        await session.commit()

    request = SyncPushRequest(
        client_id=client_id,
        batch_id=batch_id,
        changes=[_entry_change(entry_id=entry_id, seq=1, updated_at=datetime.now(UTC))],
    )

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user.id)
        dek_token = await _dek_token_for_user(session, user.id)
        try:
            first = await push_changes(session, user_id=user.id, request=request)
            second = await push_changes(session, user_id=user.id, request=request)
            await session.commit()
        finally:
            reset_current_user_dek(dek_token)

    assert first.idempotent_replay is False
    assert second.idempotent_replay is True
    assert second.cursor == first.cursor


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pull_is_scoped_to_authenticated_user() -> None:
    if not _integration_enabled():
        pytest.skip("requires PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    client_id = uuid.uuid4()
    entry_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user_a = await register_user(
            session,
            RegisterRequest(email=f"sync-a-{uuid.uuid4().hex[:8]}@localhost.dev", password="test-password-12"),
        )
        user_a.is_verified = True
        user_b = await register_user(
            session,
            RegisterRequest(email=f"sync-b-{uuid.uuid4().hex[:8]}@localhost.dev", password="test-password-12"),
        )
        user_b.is_verified = True
        await session.commit()
        user_a_id = user_a.id
        user_b_id = user_b.id

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user_a_id)
        dek_token = await _dek_token_for_user(session, user_a_id)
        try:
            await push_changes(
                session,
                user_id=user_a_id,
                request=SyncPushRequest(
                    client_id=client_id,
                    batch_id=uuid.uuid4(),
                    changes=[_entry_change(entry_id=entry_id, seq=1, updated_at=datetime.now(UTC))],
                ),
            )
            await session.commit()
        finally:
            reset_current_user_dek(dek_token)

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user_b_id)
        pull = await pull_changes(session, user_id=user_b_id, since=None, limit=50)

    assert pull.changes == []

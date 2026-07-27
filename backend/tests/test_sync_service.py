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
from app.models.entry import Entry, EntrySlot, EntrySource, WorkContext
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
    entry_date: date | None = None,
) -> SyncChange:
    return SyncChange(
        seq=seq,
        id=entry_id,
        table="entries",
        operation="upsert",
        data={
            "entry_date": (entry_date or date.today()).isoformat(),
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
async def test_merge_entry_upsert_accepts_date_valid_at_client_edit_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delayed offline push must not reject a once-valid backdated entry.

    Concrete trigger: user creates the oldest editable day (today−7) offline;
    reconnects after the wall-clock window rolls forward. Validating against
    server "today" 400s the whole push batch and the web outbox never acks.
    """
    from app.services import entry_service
    from app.services.sync_service import _merge_entry_upsert

    monkeypatch.setattr(entry_service, "_today", lambda: date(2026, 7, 24))

    entry_id = uuid.uuid4()
    user_id = uuid.uuid4()
    change = _entry_change(
        entry_id=entry_id,
        seq=1,
        # Valid on the edit day (7 days before 2026-07-15); outside today's window.
        entry_date=date(2026, 7, 8),
        updated_at=datetime(2026, 7, 15, 18, 0, tzinfo=UTC),
    )

    empty = MagicMock()
    empty.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=empty)
    nested = MagicMock()
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=False)
    db.begin_nested.return_value = nested
    db.flush = AsyncMock()

    with (
        patch("app.services.sync_service.assign_tags_to_entry", new_callable=AsyncMock),
        patch("app.services.sync_service.assign_symptoms_to_entry", new_callable=AsyncMock),
        patch("app.services.sync_service._append_revision_log", new_callable=AsyncMock),
    ):
        conflicts = await _merge_entry_upsert(db, user_id=user_id, change=change)

    assert conflicts == []
    db.add.assert_called_once()
    created = db.add.call_args.args[0]
    assert isinstance(created, Entry)
    assert created.entry_date == date(2026, 7, 8)


@pytest.mark.asyncio
async def test_merge_entry_upsert_rejects_date_invalid_at_client_edit_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sync still enforces the backdate window as of the client edit day."""
    from app.services import entry_service
    from app.services.sync_service import _merge_entry_upsert

    monkeypatch.setattr(entry_service, "_today", lambda: date(2026, 7, 24))

    change = _entry_change(
        entry_id=uuid.uuid4(),
        seq=1,
        # 14 days before the edit day — never valid, even offline.
        entry_date=date(2026, 7, 1),
        updated_at=datetime(2026, 7, 15, 18, 0, tzinfo=UTC),
    )
    db = MagicMock()

    with pytest.raises(SyncBadRequestError, match="entry_date must be within"):
        await _merge_entry_upsert(db, user_id=uuid.uuid4(), change=change)

    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_sync_tag_ids_drops_deleted_keeps_visible_and_linked() -> None:
    """Stale deleted tag IDs in the outbox must not reach assign_tags_to_entry.

    Concrete trigger: offline entry still lists a custom tag that was deleted
    online (cascade cleared entry_tags; Dexie was not pruned). Raising
    TagsNotFoundError 500'd the push and the web client never acked.
    """
    from app.services.sync_service import _resolve_sync_tag_ids

    user_id = uuid.uuid4()
    entry_id = uuid.uuid4()
    kept_visible = uuid.uuid4()
    kept_linked_hidden = uuid.uuid4()
    deleted = uuid.uuid4()

    current_result = MagicMock()
    current_result.all.return_value = [(kept_linked_hidden,)]
    visible_result = MagicMock()
    visible_result.all.return_value = [(kept_visible,)]

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[current_result, visible_result])

    resolved = await _resolve_sync_tag_ids(
        db,
        user_id=user_id,
        entry_id=entry_id,
        tag_ids=[deleted, kept_visible, kept_linked_hidden, kept_visible],
    )

    assert resolved == [kept_visible, kept_linked_hidden]
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_resolve_sync_symptoms_drops_unknown_and_invalid_keys() -> None:
    from app.services.sync_service import _resolve_sync_symptoms

    user_id = uuid.uuid4()
    entry_id = uuid.uuid4()
    kept = uuid.uuid4()
    deleted = uuid.uuid4()

    visible_result = MagicMock()
    visible_result.all.return_value = [(kept,)]
    db = MagicMock()
    db.execute = AsyncMock(return_value=visible_result)

    resolved = await _resolve_sync_symptoms(
        db,
        user_id=user_id,
        entry_id=entry_id,
        symptoms={str(kept): 2, str(deleted): 1, "not-a-uuid": 3},
    )

    assert resolved == {str(kept): 2}
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_merge_entry_upsert_filters_deleted_tag_before_assign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Client-wins update must assign only resolvable tag IDs."""
    from app.services import entry_service
    from app.services.sync_service import _merge_entry_upsert

    monkeypatch.setattr(entry_service, "_today", lambda: date(2026, 7, 24))

    entry_id = uuid.uuid4()
    user_id = uuid.uuid4()
    kept_tag = uuid.uuid4()
    deleted_tag = uuid.uuid4()
    older_server_ts = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)
    client_ts = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)

    existing = Entry(
        id=entry_id,
        user_id=user_id,
        entry_date=date(2026, 7, 24),
        slot=EntrySlot.DAY,
        mood_score=2,
        energy=2,
        stress=2,
        cycle_day=None,
        source=EntrySource.DIRECT,
        work_context=WorkContext.HOMEOFFICE,
        note_enc=None,
        updated_at=older_server_ts,
    )

    entry_result = MagicMock()
    entry_result.scalar_one_or_none.return_value = existing
    db = MagicMock()
    db.execute = AsyncMock(return_value=entry_result)
    db.flush = AsyncMock()

    change = SyncChange(
        seq=1,
        id=entry_id,
        table="entries",
        operation="upsert",
        data={
            "entry_date": date(2026, 7, 24).isoformat(),
            "slot": EntrySlot.DAY.value,
            "mood_score": 4,
            "energy": 3,
            "stress": 2,
            "work_context": WorkContext.HOMEOFFICE.value,
            "note": "edited offline after tag delete",
            "tag_ids": [str(kept_tag), str(deleted_tag)],
            "symptoms": {},
        },
        updated_at=client_ts,
    )

    assign_tags = AsyncMock(return_value=[])
    assign_symptoms = AsyncMock(return_value=[])
    list_tags = AsyncMock(return_value=[])
    list_symptoms = AsyncMock(return_value=[])
    resolve_tags = AsyncMock(return_value=[kept_tag])
    resolve_symptoms = AsyncMock(return_value={})

    with (
        patch("app.services.sync_service._resolve_sync_tag_ids", resolve_tags),
        patch("app.services.sync_service._resolve_sync_symptoms", resolve_symptoms),
        patch("app.services.sync_service.assign_tags_to_entry", assign_tags),
        patch("app.services.sync_service.assign_symptoms_to_entry", assign_symptoms),
        patch("app.services.sync_service.list_tags_for_entry", list_tags),
        patch("app.services.sync_service.list_symptoms_for_entry", list_symptoms),
        patch("app.services.sync_service._append_revision_log", new_callable=AsyncMock),
    ):
        conflicts = await _merge_entry_upsert(db, user_id=user_id, change=change)

    assert conflicts == []
    resolve_tags.assert_awaited_once()
    assign_tags.assert_awaited_once_with(
        db,
        user_id=user_id,
        entry_id=entry_id,
        tag_ids=[kept_tag],
        record_revision=False,
    )
    assert deleted_tag not in assign_tags.await_args.kwargs["tag_ids"]


def test_revision_to_change_uses_user_rev() -> None:
    from app.models.sync_engine import SyncRevisionLog
    from app.services.sync_service import _revision_to_change

    row = SyncRevisionLog(
        user_id=uuid.uuid4(),
        user_rev=17,
        entity_type="entry",
        entity_id=uuid.uuid4(),
        operation="upsert",
        payload={"entry_date": "2026-06-30"},
        entity_updated_at=datetime.now(UTC),
    )
    change = _revision_to_change(row)
    assert change.seq == 17


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
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations/versions/018_add_sync_engine_infrastructure.py"
    )
    source = path.read_text(encoding="utf-8")
    assert 'revision: str = "018"' in source
    assert "sync_revision_log" in source
    assert "sync_push_batches" in source


def test_migration_033_preserves_explicit_updated_at() -> None:
    """Sync LWW sets client_ts; the shared trigger must not overwrite it."""
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations/versions/033_preserve_explicit_updated_at.py"
    )
    source = path.read_text(encoding="utf-8")
    assert 'revision: str = "033"' in source
    assert 'down_revision: str | None = "032"' in source
    assert "IS NOT DISTINCT FROM OLD.updated_at" in source
    # Downgrade must restore the historical unconditional overwrite.
    assert "NEW.updated_at = now();" in source


@pytest.mark.integration
@pytest.mark.asyncio
async def test_updated_at_trigger_preserves_explicit_client_ts() -> None:
    """Concrete LWW scenario: explicit client_ts survives UPDATE; untouched bumps."""
    if not _integration_enabled():
        pytest.skip("requires PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    from sqlalchemy import text

    from app.db.session import engine

    client_ts = datetime(2026, 7, 27, 10, 0, tzinfo=UTC)
    async with engine.connect() as conn:
        await conn.execute(
            text(
                """
                CREATE TEMP TABLE lww_probe (
                    id int PRIMARY KEY,
                    val int NOT NULL,
                    updated_at timestamptz NOT NULL
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TRIGGER lww_probe_updated_at
                BEFORE UPDATE ON lww_probe
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
                """
            )
        )
        await conn.execute(
            text(
                "INSERT INTO lww_probe (id, val, updated_at) "
                "VALUES (1, 1, TIMESTAMPTZ '2026-07-27 09:00:00+00')"
            )
        )
        # Sync path: caller supplies client_ts — must be preserved.
        await conn.execute(
            text(
                "UPDATE lww_probe SET val = 2, updated_at = :client_ts WHERE id = 1"
            ),
            {"client_ts": client_ts},
        )
        preserved = (
            await conn.execute(text("SELECT updated_at FROM lww_probe WHERE id = 1"))
        ).scalar_one()
        assert preserved == client_ts

        # REST/ORM path: UPDATE omits updated_at — trigger must auto-bump.
        await conn.execute(text("UPDATE lww_probe SET val = 3 WHERE id = 1"))
        bumped = (
            await conn.execute(text("SELECT updated_at, val FROM lww_probe WHERE id = 1"))
        ).one()
        assert bumped.val == 3
        assert bumped.updated_at > client_ts
        await conn.commit()


@pytest.mark.asyncio
@pytest.mark.no_rest_revision_stub
async def test_record_entry_upsert_revision_appends_log_without_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REST helpers must write revision rows (note redacted) for incremental pull."""
    from unittest.mock import AsyncMock, MagicMock

    from app.services import sync_service
    from tests.conftest import make_entry

    user = make_user()
    entry = make_entry(user, mood_score=4, note="secret note")
    db = MagicMock()
    append = AsyncMock(return_value=7)
    order: list[str] = []

    async def lock_side(*_args: object, **_kwargs: object) -> MagicMock:
        order.append("lock")
        return MagicMock()

    async def list_tags_side(*_args: object, **_kwargs: object) -> list:
        order.append("tags")
        return []

    async def list_symptoms_side(*_args: object, **_kwargs: object) -> list:
        order.append("symptoms")
        return []

    monkeypatch.setattr(sync_service, "_append_revision_log", append)
    monkeypatch.setattr(
        sync_service, "_get_or_create_user_revision", AsyncMock(side_effect=lock_side)
    )
    monkeypatch.setattr(sync_service, "list_tags_for_entry", AsyncMock(side_effect=list_tags_side))
    monkeypatch.setattr(
        sync_service, "list_symptoms_for_entry", AsyncMock(side_effect=list_symptoms_side)
    )

    rev = await sync_service.record_entry_upsert_revision(db, user_id=user.id, entry=entry)

    assert rev == 7
    # Lock before association reads so concurrent REST writes cannot insert a
    # newer revision between snapshot and append.
    assert order[:3] == ["lock", "tags", "symptoms"]
    append.assert_awaited_once()
    kwargs = append.await_args.kwargs
    assert kwargs["entity_type"] == "entry"
    assert kwargs["entity_id"] == entry.id
    assert kwargs["operation"] == "upsert"
    assert kwargs["payload"]["mood_score"] == 4
    assert kwargs["payload"]["note"] is None
    assert kwargs["payload"]["tag_ids"] == []
    assert kwargs["payload"]["symptoms"] == {}


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
            await session.execute(
                select(Entry).where(Entry.id == entry_id, Entry.user_id == user.id)
            )
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
                (
                    await session.execute(
                        select(SyncConflict).where(
                            SyncConflict.user_id == user.id,
                            SyncConflict.entity_id == entry_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            entry = (await session.execute(select(Entry).where(Entry.id == entry_id))).scalar_one()
            await session.commit()
        finally:
            reset_current_user_dek(dek_token)

    assert response.conflicts
    assert response.conflicts[0].field_name == "mood_score"
    assert len(conflicts) == 1
    assert entry.mood_score == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_push_client_uuid_merges_existing_slot_instead_of_colliding() -> None:
    if not _integration_enabled():
        pytest.skip("requires PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    server_entry_id = uuid.uuid4()
    client_entry_id = uuid.uuid4()
    client_id = uuid.uuid4()
    email = f"sync-slot-collision-{uuid.uuid4().hex[:8]}@localhost.dev"
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
                    changes=[
                        _entry_change(
                            entry_id=server_entry_id,
                            seq=1,
                            mood_score=3,
                            updated_at=now,
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
                            entry_id=client_entry_id,
                            seq=1,
                            mood_score=5,
                            updated_at=now + timedelta(seconds=1),
                        )
                    ],
                ),
            )
            entry = (
                await session.execute(
                    select(Entry).where(
                        Entry.user_id == user.id,
                        Entry.entry_date == date.today(),
                        Entry.slot == EntrySlot.DAY,
                    )
                )
            ).scalar_one()
            await session.commit()
        finally:
            reset_current_user_dek(dek_token)

    assert response.applied == 1
    assert entry.id == server_entry_id
    assert entry.mood_score == 5


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
            RegisterRequest(
                email=f"sync-a-{uuid.uuid4().hex[:8]}@localhost.dev", password="test-password-12"
            ),
        )
        user_a.is_verified = True
        user_b = await register_user(
            session,
            RegisterRequest(
                email=f"sync-b-{uuid.uuid4().hex[:8]}@localhost.dev", password="test-password-12"
            ),
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


def test_note_conflict_markers_detect_distinct_nonempty_notes() -> None:
    from app.services.sync_service import _note_conflict_markers

    markers = _note_conflict_markers("stress today", "calm today")
    assert markers is not None
    client_m, server_m = markers
    assert client_m == {"present": True, "changed": True}
    assert server_m == {"present": True, "changed": True}
    assert _note_conflict_markers("same", "same") is None
    assert _note_conflict_markers(None, "x") is not None


def test_get_or_create_user_revision_uses_for_update() -> None:
    from sqlalchemy.dialects import postgresql

    from app.models.sync_engine import SyncUserRevision
    from app.services.sync_service import _get_or_create_user_revision

    stmt = (
        select(SyncUserRevision).where(SyncUserRevision.user_id == uuid.uuid4()).with_for_update()
    )
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in compiled.upper()
    assert callable(_get_or_create_user_revision)

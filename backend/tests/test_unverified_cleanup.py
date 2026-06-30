"""Tests for Issue #101: auto-cleanup of stale unverified accounts."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.cleanup_service import cleanup_unverified_accounts
from app.workers.analytics import run_cleanup_once, seconds_until_next_cleanup


def _session_with_deleted_ids(*deleted_ids: uuid.UUID) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(deleted_ids)
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_cleanup_deletes_unverified_accounts_older_than_retention() -> None:
    user_id = uuid.uuid4()
    db = _session_with_deleted_ids(user_id)

    count = await cleanup_unverified_accounts(
        db,
        now=datetime(2026, 5, 10, 12, tzinfo=UTC),
        retention_days=7,
    )

    assert count == 1
    stmt = db.execute.await_args.args[0]
    assert "users.is_verified IS false" in str(stmt.whereclause)
    assert "users.created_at <" in str(stmt.whereclause)
    assert stmt.compile().params["created_at_1"] == datetime(2026, 5, 3, 12, tzinfo=UTC)


@pytest.mark.asyncio
async def test_cleanup_keeps_accounts_exactly_on_threshold_by_using_strict_less_than() -> None:
    db = _session_with_deleted_ids()
    now = datetime(2026, 5, 10, 3, tzinfo=UTC)

    count = await cleanup_unverified_accounts(db, now=now, retention_days=7)

    assert count == 0
    stmt = db.execute.await_args.args[0]
    assert "users.created_at <" in str(stmt.whereclause)
    assert "<=" not in str(stmt.whereclause)


@pytest.mark.asyncio
async def test_cleanup_preserves_verified_accounts_by_filtering_false_only() -> None:
    db = _session_with_deleted_ids()

    await cleanup_unverified_accounts(
        db,
        now=datetime(2026, 5, 10, tzinfo=UTC),
        retention_days=7,
    )

    stmt = db.execute.await_args.args[0]
    assert "users.is_verified IS false" in str(stmt.whereclause)
    assert "users.is_verified IS true" not in str(stmt.whereclause)


@pytest.mark.asyncio
async def test_cleanup_returns_deleted_count_from_database_returning() -> None:
    db = _session_with_deleted_ids(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    count = await cleanup_unverified_accounts(
        db,
        now=datetime(2026, 5, 10, tzinfo=UTC),
        retention_days=7,
    )

    assert count == 3


@pytest.mark.asyncio
async def test_cleanup_is_idempotent_when_nothing_matches() -> None:
    db = _session_with_deleted_ids()

    first = await cleanup_unverified_accounts(
        db,
        now=datetime(2026, 5, 10, tzinfo=UTC),
        retention_days=7,
    )
    second = await cleanup_unverified_accounts(
        db,
        now=datetime(2026, 5, 10, tzinfo=UTC),
        retention_days=7,
    )

    assert first == 0
    assert second == 0
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_cleanup_log_contains_count_and_user_ids_but_never_email(
    caplog: pytest.LogCaptureFixture,
) -> None:
    db = _session_with_deleted_ids(uuid.uuid4())

    with caplog.at_level(logging.INFO, logger="app.services.cleanup_service"):
        await cleanup_unverified_accounts(
            db,
            now=datetime(2026, 5, 10, tzinfo=UTC),
            retention_days=7,
        )

    record = next(r for r in caplog.records if r.message == "unverified account cleanup completed")
    assert record.deleted_count == 1
    assert len(record.user_ids) == 1
    rendered = caplog.text.lower()
    assert "@" not in rendered
    assert "email" not in rendered


def test_worker_schedules_next_cleanup_for_today_before_three_utc() -> None:
    now = datetime(2026, 5, 10, 2, 30, tzinfo=UTC)

    assert seconds_until_next_cleanup(now) == 30 * 60


def test_worker_schedules_next_cleanup_for_tomorrow_after_three_utc() -> None:
    now = datetime(2026, 5, 10, 3, 0, tzinfo=UTC)

    assert seconds_until_next_cleanup(now) == timedelta(days=1).total_seconds()


@pytest.mark.asyncio
async def test_run_cleanup_once_accepts_session_factory() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.commit = AsyncMock()
            self.rollback = AsyncMock()
            self.execute = AsyncMock(return_value=MagicMock())
            self.execute.return_value.scalars.return_value.all.return_value = []

        async def __aenter__(self) -> FakeSession:
            return self

        async def __aexit__(self, *_exc: object) -> None:
            return None

    session = FakeSession()

    deleted_accounts, deleted_conflicts = await run_cleanup_once(session_factory=lambda: session)

    assert deleted_accounts == 0
    assert deleted_conflicts == 0
    assert session.commit.await_count == 1
    assert session.rollback.await_count == 0

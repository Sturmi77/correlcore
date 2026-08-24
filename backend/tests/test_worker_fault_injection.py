"""Fault-injection tests for analytics-worker robustness (#759).

These deliberately break the two external dependencies the scheduled worker
and the on-demand regenerate path lean on — the database connection and Redis
— and assert the worker *recovers* (retries a transient blip, isolates a
persistent one, degrades gracefully) instead of dying or taking the whole
batch down with it. They guard the hardening added in #752 (bulkhead),
#753 (timeouts) and #758 (retry classification / graceful degradation) against
future regressions.

They run in the standard ``pytest`` collection, so they execute on every
backend CI run (``.github/workflows/ci-api.yml``) with no extra wiring. The
faults are injected at the mock boundary (a session/Redis client that raises
connection errors) rather than by tearing down a live container, which keeps
the suite fast and deterministic while still exercising the real recovery code
paths. See ``tests/README.md`` for how to add a new case.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import DBAPIError, OperationalError

from app.services.insight_worker_service import (
    InsightGenerationJob,
    schedule_post_batch_insight_regeneration,
    try_acquire_regenerate_slot,
)
from app.workers.analytics import run_insights_once


class _FakeSession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[_FakeSession] = []

    def __call__(self) -> _FakeSession:
        session = _FakeSession()
        self.sessions.append(session)
        return session


def _killed_connection_error() -> OperationalError:
    """A SQLAlchemy error shaped like asyncpg losing its server connection.

    A real lost/reset connection is flagged ``connection_invalidated`` by
    SQLAlchemy's disconnect detection; the worker only retries those.
    """

    err = OperationalError(
        "SELECT 1",
        {},
        Exception("server closed the connection unexpectedly"),
    )
    err.connection_invalidated = True
    return err


def _invalidated_connection_error() -> DBAPIError:
    """A DBAPIError explicitly flagged as having invalidated the connection."""

    err = DBAPIError("SELECT 1", {}, Exception("connection invalidated"))
    err.connection_invalidated = True
    return err


# --------------------------------------------------------------------------- #
# Database connection faults                                                   #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_worker_recovers_when_db_connection_killed_mid_user() -> None:
    """A transient DB disconnect is retried on a fresh session and recovers."""
    job = InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"one")
    session_factory = _FakeSessionFactory()
    attempts = {"n": 0}

    async def fake_generate(_session: object, *, job: InsightGenerationJob, as_of: object) -> int:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise _killed_connection_error()
        return 5

    with (
        patch(
            "app.workers.analytics.list_insight_generation_jobs",
            new=AsyncMock(return_value=[job]),
        ),
        patch("app.workers.analytics.generate_insights_for_job", side_effect=fake_generate),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()),
        patch("app.workers.analytics.settings.WORKER_TRANSIENT_RETRY_BACKOFF_SECONDS", 0),
    ):
        summary = await run_insights_once(
            as_of=datetime(2026, 5, 12, tzinfo=UTC),
            session_factory=session_factory,
        )

    assert attempts["n"] == 2
    assert summary.processed_users == 1
    assert summary.failed_users == 0
    assert summary.generated_insights == 5
    # A fresh session is used per attempt so the invalidated one is discarded:
    # the job-listing session plus two user attempts.
    assert len(session_factory.sessions) == 3


@pytest.mark.asyncio
async def test_connection_invalidated_error_is_retried() -> None:
    """A DBAPIError flagged connection_invalidated is treated as transient."""
    job = InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"one")
    session_factory = _FakeSessionFactory()
    attempts = {"n": 0}

    async def fake_generate(_session: object, *, job: InsightGenerationJob, as_of: object) -> int:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise _invalidated_connection_error()
        return 1

    with (
        patch(
            "app.workers.analytics.list_insight_generation_jobs",
            new=AsyncMock(return_value=[job]),
        ),
        patch("app.workers.analytics.generate_insights_for_job", side_effect=fake_generate),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()),
        patch("app.workers.analytics.settings.WORKER_TRANSIENT_RETRY_BACKOFF_SECONDS", 0),
    ):
        summary = await run_insights_once(
            as_of=datetime(2026, 5, 12, tzinfo=UTC),
            session_factory=session_factory,
        )

    assert attempts["n"] == 2
    assert summary.processed_users == 1
    assert summary.failed_users == 0


@pytest.mark.asyncio
async def test_non_disconnect_operational_error_is_not_retried() -> None:
    """A non-disconnect OperationalError (e.g. too-many-connections) is permanent.

    Retrying would not fix a load/resource error and could amplify nightly work,
    so only connection_invalidated / InterfaceError faults are retried (#772).
    """
    job = InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"one")
    session_factory = _FakeSessionFactory()
    calls = {"n": 0}

    async def fake_generate(_session: object, *, job: InsightGenerationJob, as_of: object) -> int:
        calls["n"] += 1
        # connection_invalidated defaults to False -> not a disconnect.
        raise OperationalError("SELECT 1", {}, Exception("sorry, too many clients already"))

    with (
        patch(
            "app.workers.analytics.list_insight_generation_jobs",
            new=AsyncMock(return_value=[job]),
        ),
        patch("app.workers.analytics.generate_insights_for_job", side_effect=fake_generate),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()),
        patch(
            "app.workers.analytics.count_consecutive_user_insight_failures",
            new=AsyncMock(return_value=0),
        ),
    ):
        summary = await run_insights_once(
            as_of=datetime(2026, 5, 12, tzinfo=UTC),
            session_factory=session_factory,
        )

    assert calls["n"] == 1  # no retry for a non-disconnect OperationalError
    assert summary.failed_users == 1
    assert summary.processed_users == 0


@pytest.mark.asyncio
async def test_worker_isolates_user_whose_db_connection_stays_down() -> None:
    """A persistent DB fault for one user is isolated; the batch survives."""
    down_job = InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"down")
    ok_job = InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"ok")
    session_factory = _FakeSessionFactory()
    down_attempts = {"n": 0}

    async def fake_generate(_session: object, *, job: InsightGenerationJob, as_of: object) -> int:
        if job.user_id == down_job.user_id:
            down_attempts["n"] += 1
            raise _killed_connection_error()
        return 7

    with (
        patch(
            "app.workers.analytics.list_insight_generation_jobs",
            new=AsyncMock(return_value=[down_job, ok_job]),
        ),
        patch("app.workers.analytics.generate_insights_for_job", side_effect=fake_generate),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()),
        patch(
            "app.workers.analytics.count_consecutive_user_insight_failures",
            new=AsyncMock(return_value=0),
        ),
        patch("app.workers.analytics.settings.WORKER_TRANSIENT_MAX_RETRIES", 2),
        patch("app.workers.analytics.settings.WORKER_TRANSIENT_RETRY_BACKOFF_SECONDS", 0),
    ):
        summary = await run_insights_once(
            as_of=datetime(2026, 5, 12, tzinfo=UTC),
            session_factory=session_factory,
        )

    # The down user exhausted its retry budget (1 initial + 2 retries) ...
    assert down_attempts["n"] == 3
    # ... but the run completed and the healthy user was still processed.
    assert summary.eligible_users == 2
    assert summary.processed_users == 1
    assert summary.failed_users == 1
    assert summary.generated_insights == 7


# --------------------------------------------------------------------------- #
# Redis connection faults (on-demand regenerate cooldown / post-batch debounce)#
# --------------------------------------------------------------------------- #


class _FakeRedis:
    def __init__(self, *, fail_on_set: bool = False) -> None:
        self._fail_on_set = fail_on_set
        self.closed = False

    async def set(self, *_args: object, **_kwargs: object) -> bool:
        if self._fail_on_set:
            from redis.exceptions import ConnectionError as RedisConnectionError

            raise RedisConnectionError("connection reset by peer")
        return True

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_regenerate_slot_fails_open_when_redis_set_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A Redis error while checking the hourly cooldown fails open (allow)."""
    fake = _FakeRedis(fail_on_set=True)

    with (
        patch("redis.asyncio.Redis.from_url", return_value=fake),
        caplog.at_level("WARNING", logger="app.services.insight_worker_service"),
    ):
        allowed = await try_acquire_regenerate_slot(user_id=uuid.uuid4())

    assert allowed is True
    assert fake.closed is True  # client still cleaned up
    assert "failing open" in caplog.text


@pytest.mark.asyncio
async def test_post_batch_skips_regeneration_when_redis_down() -> None:
    """A Redis outage skips the opportunistic post-batch run without crashing."""
    fake = _FakeRedis(fail_on_set=True)

    with (
        patch("redis.asyncio.Redis.from_url", return_value=fake),
        patch(
            "app.services.insight_worker_service.run_insight_regeneration_background",
            new=AsyncMock(),
        ) as background,
    ):
        # Must not raise into the caller (the bulk-import endpoint).
        await schedule_post_batch_insight_regeneration(user_id=uuid.uuid4())

    background.assert_not_awaited()
    assert fake.closed is True

"""Tests for `app.services.health_service` — Issue #70 (CQR-5).

Targets the internal probe functions that were previously bypassed by
`test_health.py` (which mocked the public `check_readiness` aggregator).

- `_probe_postgres` returns OK when the engine yields a working
  connection and `SELECT 1` succeeds.
- `_probe_postgres` returns DOWN with `detail=type(exc).__name__` when
  the connection raises `OperationalError` (Postgres is down /
  unreachable / wrong credentials). Logs only the exception class name
  — never the SQLAlchemy error message, which can leak DSN/password
  fragments (ADR-0007).
- `_probe_redis` returns OK when `Redis.from_url(...).ping()` succeeds.
- `_probe_redis` returns DOWN when ping raises `redis.ConnectionError`.
- `_probe_redis` closes the client even when ping fails (no leak).
- `check_readiness` aggregates: ready=True iff *all* components are OK.
- `check_liveness` is process-only and does not perform any I/O.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import OperationalError

from app.services.health_service import (
    ComponentStatus,
    _probe_postgres,
    _probe_redis,
    check_liveness,
    check_readiness,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_async_engine(execute_side_effect: object | None = None) -> MagicMock:
    """Build a mock async engine whose `connect()` is an async context
    manager yielding a connection with a pre-canned `execute` behaviour.

    `execute_side_effect=None` → execute is an `AsyncMock()` returning a
    truthy result (happy path).
    `execute_side_effect=Exception(...)` → execute raises.
    """
    conn = MagicMock()
    conn.execute = AsyncMock(side_effect=execute_side_effect)

    @asynccontextmanager
    async def _connect() -> AsyncIterator[object]:
        yield conn

    engine = MagicMock()
    engine.connect = _connect
    return engine


def _make_async_engine_failing_to_connect(exc: BaseException) -> MagicMock:
    """Engine whose `async with engine.connect()` itself raises before
    yielding (e.g. immediate OperationalError on TCP)."""

    @asynccontextmanager
    async def _connect() -> AsyncIterator[object]:
        if True:  # pragma: no branch - always raises
            raise exc
        yield  # pragma: no cover - unreachable, present so the function is a generator

    engine = MagicMock()
    engine.connect = _connect
    return engine


# ---------------------------------------------------------------------------
# check_liveness
# ---------------------------------------------------------------------------


def test_check_liveness_returns_static_payload() -> None:
    with patch("app.services.health_service.settings") as s:
        s.APP_VERSION = "9.9.9"
        result = check_liveness()
    assert result == {"status": "ok", "version": "9.9.9"}


# ---------------------------------------------------------------------------
# _probe_postgres
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_probe_postgres_ok() -> None:
    engine = _make_async_engine()
    with patch("app.services.health_service.engine", engine):
        result = await _probe_postgres()

    assert result.name == "postgres"
    assert result.status == ComponentStatus.OK
    assert result.detail == ""


@pytest.mark.asyncio
async def test_probe_postgres_operational_error_returns_down(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Postgres is unreachable — OperationalError raised when opening
    the connection. Result: DOWN with `detail=OperationalError`. Log
    must mention only the class name, not the SQLAlchemy detail message
    (which can leak DSN/password fragments)."""
    err = OperationalError("SELECT 1", {}, RuntimeError("connection refused"))
    engine = _make_async_engine_failing_to_connect(err)

    with (
        patch("app.services.health_service.engine", engine),
        caplog.at_level(logging.WARNING, logger="app.services.health_service"),
    ):
        result = await _probe_postgres()

    assert result.name == "postgres"
    assert result.status == ComponentStatus.DOWN
    assert result.detail == "OperationalError"

    record = next(r for r in caplog.records if "postgres" in r.getMessage())
    assert "OperationalError" in record.getMessage()
    assert "connection refused" not in record.getMessage()
    assert "SELECT 1" not in record.getMessage()


@pytest.mark.asyncio
async def test_probe_postgres_execute_failure_returns_down() -> None:
    """Connection opens but `SELECT 1` itself fails (e.g. read-only DB
    in failover, query timeout)."""
    engine = _make_async_engine(execute_side_effect=TimeoutError("query timed out"))

    with patch("app.services.health_service.engine", engine):
        result = await _probe_postgres()

    assert result.status == ComponentStatus.DOWN
    assert result.detail == "TimeoutError"


# ---------------------------------------------------------------------------
# _probe_redis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_probe_redis_ok() -> None:
    fake_client = MagicMock()
    fake_client.ping = AsyncMock(return_value=True)
    fake_client.aclose = AsyncMock()

    with (
        patch("app.services.health_service.settings") as s,
        patch("app.services.health_service.Redis.from_url", return_value=fake_client) as from_url,
    ):
        s.REDIS_URL = "redis://redis:6379/0"
        result = await _probe_redis()

    from_url.assert_called_once_with("redis://redis:6379/0", socket_connect_timeout=2)
    fake_client.ping.assert_awaited_once()
    fake_client.aclose.assert_awaited_once()
    assert result.name == "redis"
    assert result.status == ComponentStatus.OK


@pytest.mark.asyncio
async def test_probe_redis_connection_error_returns_down(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Redis is unreachable — ConnectionError on ping."""
    fake_client = MagicMock()
    fake_client.ping = AsyncMock(side_effect=RedisConnectionError("Connection refused"))
    fake_client.aclose = AsyncMock()

    with (
        patch("app.services.health_service.settings") as s,
        patch("app.services.health_service.Redis.from_url", return_value=fake_client),
        caplog.at_level(logging.WARNING, logger="app.services.health_service"),
    ):
        s.REDIS_URL = "redis://redis:6379/0"
        result = await _probe_redis()

    assert result.name == "redis"
    assert result.status == ComponentStatus.DOWN
    assert result.detail == "ConnectionError"

    record = next(r for r in caplog.records if "redis" in r.getMessage())
    assert "ConnectionError" in record.getMessage()


@pytest.mark.asyncio
async def test_probe_redis_timeout_returns_down() -> None:
    """Slow Redis — TimeoutError on ping."""
    fake_client = MagicMock()
    fake_client.ping = AsyncMock(side_effect=TimeoutError("ping timed out"))
    fake_client.aclose = AsyncMock()

    with (
        patch("app.services.health_service.settings") as s,
        patch("app.services.health_service.Redis.from_url", return_value=fake_client),
    ):
        s.REDIS_URL = "redis://redis:6379/0"
        result = await _probe_redis()

    assert result.status == ComponentStatus.DOWN
    assert result.detail == "TimeoutError"


@pytest.mark.asyncio
async def test_probe_redis_from_url_failure_returns_down() -> None:
    """If `Redis.from_url` itself raises (e.g. malformed URL), the
    probe must still return DOWN cleanly rather than propagating."""
    with (
        patch("app.services.health_service.settings") as s,
        patch(
            "app.services.health_service.Redis.from_url",
            side_effect=ValueError("bad URL"),
        ),
    ):
        s.REDIS_URL = "not-a-url"
        result = await _probe_redis()

    assert result.status == ComponentStatus.DOWN
    assert result.detail == "ValueError"


# ---------------------------------------------------------------------------
# check_readiness — aggregation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_readiness_all_ok() -> None:
    pg_ok = MagicMock()
    pg_ok.status = ComponentStatus.OK
    pg_ok.name = "postgres"
    redis_ok = MagicMock()
    redis_ok.status = ComponentStatus.OK
    redis_ok.name = "redis"

    with (
        patch(
            "app.services.health_service._probe_postgres",
            new_callable=AsyncMock,
            return_value=pg_ok,
        ),
        patch(
            "app.services.health_service._probe_redis",
            new_callable=AsyncMock,
            return_value=redis_ok,
        ),
    ):
        report = await check_readiness()

    assert report.ready is True
    assert report.status == "ready"
    assert [c.name for c in report.components] == ["postgres", "redis"]


@pytest.mark.asyncio
async def test_check_readiness_postgres_down_marks_not_ready() -> None:
    pg_down = MagicMock()
    pg_down.status = ComponentStatus.DOWN
    pg_down.name = "postgres"
    redis_ok = MagicMock()
    redis_ok.status = ComponentStatus.OK
    redis_ok.name = "redis"

    with (
        patch(
            "app.services.health_service._probe_postgres",
            new_callable=AsyncMock,
            return_value=pg_down,
        ),
        patch(
            "app.services.health_service._probe_redis",
            new_callable=AsyncMock,
            return_value=redis_ok,
        ),
    ):
        report = await check_readiness()

    assert report.ready is False
    assert report.status == "not_ready"


@pytest.mark.asyncio
async def test_check_readiness_redis_down_marks_not_ready() -> None:
    pg_ok = MagicMock()
    pg_ok.status = ComponentStatus.OK
    pg_ok.name = "postgres"
    redis_down = MagicMock()
    redis_down.status = ComponentStatus.DOWN
    redis_down.name = "redis"

    with (
        patch(
            "app.services.health_service._probe_postgres",
            new_callable=AsyncMock,
            return_value=pg_ok,
        ),
        patch(
            "app.services.health_service._probe_redis",
            new_callable=AsyncMock,
            return_value=redis_down,
        ),
    ):
        report = await check_readiness()

    assert report.ready is False
    assert report.status == "not_ready"


@pytest.mark.asyncio
async def test_check_readiness_both_down_marks_not_ready() -> None:
    pg_down = MagicMock()
    pg_down.status = ComponentStatus.DOWN
    pg_down.name = "postgres"
    redis_down = MagicMock()
    redis_down.status = ComponentStatus.DOWN
    redis_down.name = "redis"

    with (
        patch(
            "app.services.health_service._probe_postgres",
            new_callable=AsyncMock,
            return_value=pg_down,
        ),
        patch(
            "app.services.health_service._probe_redis",
            new_callable=AsyncMock,
            return_value=redis_down,
        ),
    ):
        report = await check_readiness()

    assert report.ready is False
    assert report.status == "not_ready"

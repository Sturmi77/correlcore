from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.insight_worker_service import (
    InsightGenerationJob,
    generate_insights_for_job,
    list_insight_generation_jobs,
    regenerate_insights_for_user,
)
from app.workers.analytics import run_daily_jobs_once, run_insights_once


def _scalars_result(values: list[object]) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _first_result(value: tuple[object, ...] | None) -> MagicMock:
    result = MagicMock()
    result.first.return_value = value
    return result


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


class _AsyncContext:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *_exc: object) -> None:
        return None


@pytest.mark.asyncio
async def test_list_insight_generation_jobs_filters_eligible_users() -> None:
    user_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([user_id]),
            _first_result((b"wrapped-dek", None)),
        ]
    )

    with patch(
        "app.services.insight_worker_service.bind_rls_current_user", new=AsyncMock()
    ) as bind_rls:
        jobs = await list_insight_generation_jobs(db)

    assert jobs == [InsightGenerationJob(user_id=user_id, wrapped_dek=b"wrapped-dek")]
    bind_rls.assert_awaited_once_with(db, user_id)
    stmt = db.execute.await_args_list[0].args[0]
    where_sql = str(stmt.whereclause)
    assert "users.is_active IS true" in where_sql
    assert "users.is_verified IS true" in where_sql
    user_scoped_stmt = db.execute.await_args_list[1].args[0]
    assert "user_encryption_keys" in str(user_scoped_stmt)
    assert "user_preferences" in str(user_scoped_stmt)


@pytest.mark.asyncio
async def test_generate_insights_for_job_binds_and_resets_user_dek() -> None:
    db = MagicMock()
    db.begin_nested.return_value = _AsyncContext()
    job = InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"wrapped-dek")

    with (
        patch("app.services.insight_worker_service.unwrap_dek", return_value=b"dek") as unwrap,
        patch(
            "app.services.insight_worker_service.set_current_user_dek", return_value="token"
        ) as bind,
        patch("app.services.insight_worker_service.reset_current_user_dek") as reset,
        patch(
            "app.services.insight_worker_service.bind_rls_current_user", new=AsyncMock()
        ) as bind_rls,
        patch(
            "app.services.insight_worker_service.generate_and_store_insights",
            new=AsyncMock(return_value=[object(), object()]),
        ) as generate,
        patch(
            "app.services.insight_worker_service.recompute_tag_vectors_and_clusters",
            new=AsyncMock(),
        ) as recompute,
    ):
        count = await generate_insights_for_job(
            db,
            job=job,
            as_of=datetime(2026, 5, 12, tzinfo=UTC).date(),
        )

    assert count == 2
    unwrap.assert_called_once_with(b"wrapped-dek")
    bind.assert_called_once_with(job.user_id, b"dek")
    bind_rls.assert_awaited_once_with(db, job.user_id)
    generate.assert_awaited_once()
    recompute.assert_awaited_once()
    reset.assert_called_once_with("token")


@pytest.mark.asyncio
async def test_generate_insights_for_job_keeps_insights_when_tag_vectors_fail() -> None:
    db = MagicMock()
    db.begin_nested.return_value = _AsyncContext()
    job = InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"wrapped-dek")

    with (
        patch("app.services.insight_worker_service.unwrap_dek", return_value=b"dek"),
        patch("app.services.insight_worker_service.set_current_user_dek", return_value="token"),
        patch("app.services.insight_worker_service.reset_current_user_dek") as reset,
        patch("app.services.insight_worker_service.bind_rls_current_user", new=AsyncMock()),
        patch(
            "app.services.insight_worker_service.generate_and_store_insights",
            new=AsyncMock(return_value=[object(), object()]),
        ),
        patch(
            "app.services.insight_worker_service.recompute_tag_vectors_and_clusters",
            new=AsyncMock(side_effect=RuntimeError("vector failure")),
        ) as recompute,
    ):
        count = await generate_insights_for_job(
            db,
            job=job,
            as_of=datetime(2026, 5, 12, tzinfo=UTC).date(),
        )

    assert count == 2
    recompute.assert_awaited_once()
    reset.assert_called_once_with("token")


@pytest.mark.asyncio
async def test_generate_insights_for_job_resets_dek_on_engine_failure() -> None:
    db = MagicMock()
    job = InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"wrapped-dek")

    with (
        patch("app.services.insight_worker_service.unwrap_dek", return_value=b"dek"),
        patch("app.services.insight_worker_service.set_current_user_dek", return_value="token"),
        patch("app.services.insight_worker_service.reset_current_user_dek") as reset,
        patch("app.services.insight_worker_service.bind_rls_current_user", new=AsyncMock()),
        patch(
            "app.services.insight_worker_service.generate_and_store_insights",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch(
            "app.services.insight_worker_service.recompute_tag_vectors_and_clusters",
            new=AsyncMock(),
        ),
        pytest.raises(RuntimeError),
    ):
        await generate_insights_for_job(
            db,
            job=job,
            as_of=datetime(2026, 5, 12, tzinfo=UTC).date(),
        )

    reset.assert_called_once_with("token")


@pytest.mark.asyncio
async def test_run_insights_once_isolates_per_user_failures() -> None:
    jobs = [
        InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"one"),
        InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"two"),
    ]
    session_factory = _FakeSessionFactory()

    async def fake_generate(_session: object, *, job: InsightGenerationJob, as_of: object) -> int:
        if job.user_id == jobs[0].user_id:
            return 3
        raise RuntimeError("bad dek")

    with (
        patch(
            "app.workers.analytics.list_insight_generation_jobs", new=AsyncMock(return_value=jobs)
        ),
        patch("app.workers.analytics.generate_insights_for_job", side_effect=fake_generate),
    ):
        summary = await run_insights_once(
            as_of=datetime(2026, 5, 12, tzinfo=UTC),
            session_factory=session_factory,
        )

    assert summary.eligible_users == 2
    assert summary.processed_users == 1
    assert summary.failed_users == 1
    assert summary.generated_insights == 3
    assert session_factory.sessions[1].commit.await_count == 1
    assert session_factory.sessions[2].rollback.await_count == 1


@pytest.mark.asyncio
async def test_regenerate_insights_for_user_returns_pipeline_result() -> None:
    user_id = uuid.uuid4()
    db = MagicMock()
    db.begin_nested.return_value = _AsyncContext()
    job = InsightGenerationJob(user_id=user_id, wrapped_dek=b"wrapped-dek")

    with (
        patch(
            "app.services.insight_worker_service._analytics_enabled",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.insight_worker_service.load_insight_generation_job",
            new=AsyncMock(return_value=job),
        ),
        patch("app.services.insight_worker_service.unwrap_dek", return_value=b"dek"),
        patch("app.services.insight_worker_service.set_current_user_dek", return_value="token"),
        patch("app.services.insight_worker_service.reset_current_user_dek"),
        patch("app.services.insight_worker_service.bind_rls_current_user", new=AsyncMock()),
        patch(
            "app.services.insight_worker_service.generate_and_store_insights",
            new=AsyncMock(return_value=[object(), object(), object()]),
        ),
        patch(
            "app.services.insight_worker_service.recompute_tag_vectors_and_clusters",
            new=AsyncMock(
                return_value=MagicMock(status="ok"),
            ),
        ),
    ):
        result = await regenerate_insights_for_user(
            db,
            user_id=user_id,
            trigger_source="user_regenerate",
        )

    assert result.insight_count == 3
    assert result.tag_clusters_status == "ok"
    assert result.trigger_source == "user_regenerate"


@pytest.mark.asyncio
async def test_run_daily_jobs_once_runs_cleanup_then_insights() -> None:
    calls: list[str] = []

    async def fake_cleanup(*, session_factory: Callable[[], object]) -> tuple[int, int]:
        calls.append("cleanup")
        return 1, 2

    async def fake_insights(*, as_of: datetime, session_factory: Callable[[], object]) -> object:
        calls.append(f"insights:{as_of.date().isoformat()}")
        return MagicMock(generated_insights=4)

    with (
        patch("app.workers.analytics.run_cleanup_once", side_effect=fake_cleanup),
        patch("app.workers.analytics.run_insights_once", side_effect=fake_insights),
    ):
        summary = await run_daily_jobs_once(now=datetime(2026, 5, 12, tzinfo=UTC))

    assert calls == ["cleanup", "insights:2026-05-12"]
    assert summary.deleted_unverified_accounts == 1
    assert summary.deleted_sync_conflicts == 2
    assert summary.insight_run.generated_insights == 4

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.worker_run import WorkerTriggerSource
from app.services.insight_engine import InsightLockTimeoutError
from app.services.insight_worker_service import (
    InsightGenerationJob,
    generate_insights_for_job,
    list_insight_generation_jobs,
    regenerate_insights_for_user,
)
from app.workers.analytics import (
    CleanupRunSummary,
    main,
    run_daily_jobs_once,
    run_insights_once,
)


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
async def test_list_insight_generation_jobs_isolates_per_user_failures() -> None:
    """#752 (Bulkhead): one user's lookup failing must not drop every other user."""
    bad_user_id = uuid.uuid4()
    good_user_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([bad_user_id, good_user_id]),
            _first_result((b"wrapped-dek", None)),
        ]
    )

    async def _bind_rls(_db: object, user_id: uuid.UUID) -> None:
        if user_id == bad_user_id:
            raise RuntimeError("boom")

    with patch(
        "app.services.insight_worker_service.bind_rls_current_user",
        new=AsyncMock(side_effect=_bind_rls),
    ):
        jobs = await list_insight_generation_jobs(db)

    assert jobs == [InsightGenerationJob(user_id=good_user_id, wrapped_dek=b"wrapped-dek")]


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
async def test_generate_insights_for_job_logs_and_propagates_lock_contention() -> None:
    """Contention is distinct from an unexpected per-user worker failure."""

    db = MagicMock()
    job = InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"wrapped-dek")

    with (
        patch("app.services.insight_worker_service.unwrap_dek", return_value=b"dek"),
        patch("app.services.insight_worker_service.set_current_user_dek", return_value="token"),
        patch("app.services.insight_worker_service.reset_current_user_dek") as reset,
        patch(
            "app.services.insight_worker_service.bind_rls_current_user",
            new=AsyncMock(),
        ),
        patch(
            "app.services.insight_worker_service.generate_and_store_insights",
            new=AsyncMock(side_effect=InsightLockTimeoutError("held")),
        ),
        patch("app.services.insight_worker_service.logger.info") as info,
    ):
        with pytest.raises(InsightLockTimeoutError):
            await generate_insights_for_job(
                db,
                job=job,
                as_of=datetime(2026, 5, 12, tzinfo=UTC).date(),
            )

    info.assert_called_once()
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
        patch(
            "app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())
        ) as start_run,
        patch("app.workers.analytics.finish_run", new=AsyncMock()) as finish_run,
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
    assert start_run.await_count == 3
    assert finish_run.await_count == 3


@pytest.mark.asyncio
async def test_run_insights_once_times_out_slow_user_and_continues() -> None:
    """#753 (I): a hung per-user job is bounded and does not block the batch."""
    jobs = [
        InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"slow"),
        InsightGenerationJob(user_id=uuid.uuid4(), wrapped_dek=b"fast"),
    ]
    session_factory = _FakeSessionFactory()

    async def fake_generate(_session: object, *, job: InsightGenerationJob, as_of: object) -> int:
        if job.user_id == jobs[0].user_id:
            await asyncio.sleep(10)
            return 99
        return 2

    with (
        patch(
            "app.workers.analytics.list_insight_generation_jobs", new=AsyncMock(return_value=jobs)
        ),
        patch("app.workers.analytics.generate_insights_for_job", side_effect=fake_generate),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()),
        patch("app.workers.analytics.settings.WORKER_JOB_TIMEOUT_SECONDS", 0.01),
    ):
        summary = await run_insights_once(
            as_of=datetime(2026, 5, 12, tzinfo=UTC),
            session_factory=session_factory,
        )

    assert summary.eligible_users == 2
    assert summary.processed_users == 1
    assert summary.failed_users == 1
    assert summary.generated_insights == 2


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
        patch(
            "app.services.insight_worker_service.bind_rls_current_user", new=AsyncMock()
        ) as bind_rls,
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
        patch(
            "app.services.worker_run_service.start_run",
            new=AsyncMock(return_value=uuid.uuid4()),
        ),
        patch("app.services.worker_run_service.finish_run", new=AsyncMock()),
    ):
        result = await regenerate_insights_for_user(
            db,
            user_id=user_id,
            trigger_source="user_regenerate",
        )

    assert result.insight_count == 3
    assert result.tag_clusters_status == "ok"
    assert result.trigger_source == "user_regenerate"
    # Fresh post-batch sessions have no request GUC; bind before DEK/pref reads.
    assert bind_rls.await_args_list[0].args == (db, user_id)


@pytest.mark.asyncio
async def test_run_daily_jobs_once_runs_cleanup_then_insights() -> None:
    calls: list[str] = []

    async def fake_cleanup(**_kwargs: object) -> CleanupRunSummary:
        calls.append("cleanup")
        return CleanupRunSummary(1, 2)

    async def fake_insights(**kwargs: object) -> object:
        as_of = kwargs["as_of"]
        assert isinstance(as_of, datetime)
        calls.append(f"insights:{as_of.date().isoformat()}")
        return MagicMock(
            eligible_users=1,
            processed_users=1,
            failed_users=0,
            generated_insights=4,
        )

    with (
        patch("app.workers.analytics.run_cleanup_once", side_effect=fake_cleanup),
        patch("app.workers.analytics.run_insights_once", side_effect=fake_insights),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()),
    ):
        summary = await run_daily_jobs_once(now=datetime(2026, 5, 12, tzinfo=UTC))

    assert calls == ["cleanup", "insights:2026-05-12"]
    assert summary.deleted_unverified_accounts == 1
    assert summary.deleted_sync_conflicts == 2
    assert summary.insight_run.generated_insights == 4
    # Tuesday is not the weekly digest slot.
    assert summary.digest_run is None


@pytest.mark.asyncio
async def test_run_daily_jobs_once_marks_cleanup_partial_failure() -> None:
    """A bulkhead-isolated cleanup error must remain visible on bundle telemetry."""

    cleanup_run = CleanupRunSummary(
        deleted_unverified_accounts=0,
        deleted_sync_conflicts=2,
        step_errors=(("unverified_accounts", "database timeout"),),
    )

    with (
        patch(
            "app.workers.analytics.run_cleanup_once",
            new=AsyncMock(return_value=cleanup_run),
        ),
        patch(
            "app.workers.analytics.run_insights_once",
            new=AsyncMock(return_value=_insight_run_mock()),
        ),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()) as finish_run,
    ):
        summary = await run_daily_jobs_once(now=datetime(2026, 5, 12, tzinfo=UTC))

    assert summary.cleanup_step_errors == cleanup_run.step_errors
    assert finish_run.await_args.kwargs["status"].name == "FAILED"
    assert finish_run.await_args.kwargs["result"]["cleanup_failed_steps"] == ["unverified_accounts"]
    assert finish_run.await_args.kwargs["error_message"] == "unverified_accounts: database timeout"


def _insight_run_mock() -> MagicMock:
    return MagicMock(
        eligible_users=1,
        processed_users=1,
        failed_users=0,
        generated_insights=4,
    )


@pytest.mark.asyncio
async def test_run_daily_jobs_once_generates_digest_on_weekly_slot() -> None:
    """On the digest weekday the daily bundle also generates the weekly digest."""
    from app.workers.digest import DigestRunSummary

    digest_summary = DigestRunSummary(
        eligible_users=2,
        processed_users=2,
        skipped_users=0,
        failed_users=0,
    )
    digest_mock = AsyncMock(return_value=digest_summary)

    with (
        patch(
            "app.workers.analytics.run_cleanup_once",
            new=AsyncMock(return_value=CleanupRunSummary(0, 0)),
        ),
        patch(
            "app.workers.analytics.run_insights_once",
            new=AsyncMock(return_value=_insight_run_mock()),
        ),
        patch("app.workers.analytics.run_digest_once", new=digest_mock),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()),
    ):
        # 2026-05-17 is a Sunday.
        summary = await run_daily_jobs_once(now=datetime(2026, 5, 17, 3, tzinfo=UTC))

    digest_mock.assert_awaited_once()
    assert summary.digest_run is digest_summary


@pytest.mark.asyncio
async def test_run_daily_jobs_once_skips_digest_off_slot() -> None:
    """Off the digest weekday the daily bundle never touches digest generation."""
    digest_mock = AsyncMock()

    with (
        patch(
            "app.workers.analytics.run_cleanup_once",
            new=AsyncMock(return_value=CleanupRunSummary(0, 0)),
        ),
        patch(
            "app.workers.analytics.run_insights_once",
            new=AsyncMock(return_value=_insight_run_mock()),
        ),
        patch("app.workers.analytics.run_digest_once", new=digest_mock),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()),
    ):
        # 2026-05-16 is a Saturday.
        summary = await run_daily_jobs_once(now=datetime(2026, 5, 16, 3, tzinfo=UTC))

    digest_mock.assert_not_awaited()
    assert summary.digest_run is None


@pytest.mark.asyncio
async def test_run_daily_jobs_once_isolates_digest_failure() -> None:
    """A digest failure is logged and does not fail the daily bundle."""
    with (
        patch(
            "app.workers.analytics.run_cleanup_once",
            new=AsyncMock(return_value=CleanupRunSummary(0, 0)),
        ),
        patch(
            "app.workers.analytics.run_insights_once",
            new=AsyncMock(return_value=_insight_run_mock()),
        ),
        patch(
            "app.workers.analytics.run_digest_once",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch("app.workers.analytics.start_run", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.workers.analytics.finish_run", new=AsyncMock()) as finish_run,
    ):
        summary = await run_daily_jobs_once(now=datetime(2026, 5, 17, 3, tzinfo=UTC))

    # Daily bundle still records success; digest failure is isolated.
    assert summary.digest_run is None
    assert finish_run.await_args.kwargs["status"].name == "SUCCEEDED"


@pytest.mark.parametrize(
    ("argv", "expected_source"),
    [
        (["analytics", "--once"], WorkerTriggerSource.CLI_ONCE),
        (["analytics", "--once", "--source", "scheduled"], WorkerTriggerSource.SCHEDULED),
    ],
)
def test_analytics_once_cli_records_explicit_trigger_source(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    expected_source: WorkerTriggerSource,
) -> None:
    """Cron can identify itself without changing manual --once attribution."""

    run_once = AsyncMock()
    monkeypatch.setattr("sys.argv", argv)

    with patch("app.workers.analytics.run_daily_jobs_once", new=run_once):
        main()

    run_once.assert_awaited_once_with(trigger_source=expected_source)

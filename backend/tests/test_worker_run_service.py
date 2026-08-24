"""Unit tests for worker run telemetry helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.worker_run import WorkerJobKind, WorkerRun, WorkerRunStatus, WorkerTriggerSource
from app.services import worker_run_service
from tests.conftest import make_db_session_with_results


class _SessionCtx:
    def __init__(self, session: MagicMock) -> None:
        self._session = session

    async def __aenter__(self) -> MagicMock:
        return self._session

    async def __aexit__(self, *_exc: object) -> None:
        return None


@pytest.mark.asyncio
async def test_start_and_finish_run_round_trip() -> None:
    run_id = uuid.uuid4()
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.get = AsyncMock(
        return_value=WorkerRun(
            id=run_id,
            worker_name="analytics",
            job_kind=WorkerJobKind.INSIGHTS,
            trigger_source=WorkerTriggerSource.ADMIN_TRIGGER,
            status=WorkerRunStatus.RUNNING,
            started_at=datetime.now(UTC),
            result={},
        )
    )
    session.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )
    )

    created: list[WorkerRun] = []

    def _add(obj: WorkerRun) -> None:
        obj.id = run_id
        created.append(obj)

    session.add.side_effect = _add

    with patch(
        "app.services.worker_run_service.AsyncSessionLocal",
        side_effect=lambda: _SessionCtx(session),
    ):
        started = await worker_run_service.start_run(
            job_kind=WorkerJobKind.INSIGHTS,
            trigger_source=WorkerTriggerSource.ADMIN_TRIGGER,
        )
        assert started == run_id
        await worker_run_service.finish_run(
            run_id,
            status=WorkerRunStatus.SUCCEEDED,
            result={"generated_insights": 4},
        )

    assert created[0].job_kind == WorkerJobKind.INSIGHTS
    assert session.get.await_args.args[1] == run_id
    assert session.commit.await_count >= 2


def _fake_succeeded_run(job_kind: WorkerJobKind, *, finished_at: datetime) -> WorkerRun:
    return WorkerRun(
        id=uuid.uuid4(),
        worker_name="analytics",
        job_kind=job_kind,
        trigger_source=WorkerTriggerSource.SCHEDULED,
        status=WorkerRunStatus.SUCCEEDED,
        started_at=finished_at,
        finished_at=finished_at,
        scope_user_id=None,
        result={},
    )


@pytest.mark.asyncio
async def test_latest_successful_system_runs_returns_one_per_kind() -> None:
    """Queries run in MONITORED_KINDS order; each kind gets its own row (#756)."""

    bundle_run = _fake_succeeded_run(
        WorkerJobKind.DAILY_BUNDLE, finished_at=datetime(2026, 8, 20, 3, 5, tzinfo=UTC)
    )
    insights_run = _fake_succeeded_run(
        WorkerJobKind.INSIGHTS, finished_at=datetime(2026, 8, 20, 3, 3, tzinfo=UTC)
    )
    # No successful DIGEST run yet (e.g. fresh install before first Sunday slot).
    db = make_db_session_with_results(bundle_run, insights_run, None)

    result = await worker_run_service.latest_successful_system_runs(db)

    assert result[WorkerJobKind.DAILY_BUNDLE] is bundle_run
    assert result[WorkerJobKind.INSIGHTS] is insights_run
    assert result[WorkerJobKind.DIGEST] is None
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_latest_successful_system_runs_filters_by_status_in_query() -> None:
    """Each per-kind query must filter out failed or incomplete system work,
    not just return the latest run regardless of outcome.
    """

    db = make_db_session_with_results(None, None, None)

    await worker_run_service.latest_successful_system_runs(db, kinds=(WorkerJobKind.DAILY_BUNDLE,))

    assert db.execute.await_count == 1
    compiled = str(db.execute.await_args.args[0])
    compiled_lower = compiled.lower()
    assert "status" in compiled_lower
    assert "scope_user_id" in compiled_lower
    assert "finished_at" in compiled_lower
    assert "result" in compiled_lower
    assert "order by worker_runs.finished_at desc" in compiled_lower
    assert set(db.execute.await_args.args[0].compile().params.values()) >= {
        "eligible_users",
        "failed_users",
    }


def _status_rows(statuses: list[WorkerRunStatus]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = [(status,) for status in statuses]
    return result


@pytest.mark.asyncio
async def test_count_consecutive_user_insight_failures_counts_current_streak() -> None:
    """#758 (L): count FAILED runs newer than the last SUCCEEDED one."""
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_status_rows(
            [
                WorkerRunStatus.FAILED,
                WorkerRunStatus.FAILED,
                WorkerRunStatus.SUCCEEDED,
                WorkerRunStatus.FAILED,
            ]
        )
    )

    streak = await worker_run_service.count_consecutive_user_insight_failures(
        db, user_id=uuid.uuid4()
    )

    assert streak == 2
    stmt = str(db.execute.await_args.args[0])
    assert "worker_runs.job_kind" in stmt
    assert "order by worker_runs.started_at desc" in stmt.lower()


@pytest.mark.asyncio
async def test_count_consecutive_user_insight_failures_zero_when_latest_succeeded() -> None:
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_status_rows([WorkerRunStatus.SUCCEEDED, WorkerRunStatus.FAILED])
    )

    streak = await worker_run_service.count_consecutive_user_insight_failures(
        db, user_id=uuid.uuid4()
    )

    assert streak == 0


@pytest.mark.asyncio
async def test_count_consecutive_user_insight_failures_zero_without_history() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=_status_rows([]))

    streak = await worker_run_service.count_consecutive_user_insight_failures(
        db, user_id=uuid.uuid4()
    )

    assert streak == 0

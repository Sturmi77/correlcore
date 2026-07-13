"""Unit tests for worker run telemetry helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.worker_run import WorkerJobKind, WorkerRun, WorkerRunStatus, WorkerTriggerSource
from app.services import worker_run_service


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

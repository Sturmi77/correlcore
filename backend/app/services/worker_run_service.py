"""Persist and query analytics worker run telemetry."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.worker_run import (
    WorkerJobKind,
    WorkerRun,
    WorkerRunStatus,
    WorkerTriggerSource,
)

logger = logging.getLogger(__name__)

DEFAULT_WORKER_NAME = "analytics"
GLOBAL_RETENTION = 100
PER_USER_RETENTION = 20
MAX_ERROR_LEN = 2000


def _as_trigger(value: str | WorkerTriggerSource) -> WorkerTriggerSource:
    if isinstance(value, WorkerTriggerSource):
        return value
    return WorkerTriggerSource(value)


def _as_kind(value: str | WorkerJobKind) -> WorkerJobKind:
    if isinstance(value, WorkerJobKind):
        return value
    return WorkerJobKind(value)


def _truncate_error(message: str | None) -> str | None:
    if message is None:
        return None
    text = message.strip()
    if len(text) <= MAX_ERROR_LEN:
        return text
    return text[: MAX_ERROR_LEN - 1] + "…"


async def start_run(
    *,
    job_kind: str | WorkerJobKind,
    trigger_source: str | WorkerTriggerSource,
    scope_user_id: uuid.UUID | None = None,
    worker_name: str = DEFAULT_WORKER_NAME,
) -> uuid.UUID | None:
    """Insert a running worker_runs row and return its id.

    Returns ``None`` when persistence fails so callers can continue the job.
    """

    try:
        async with AsyncSessionLocal() as db:
            run = WorkerRun(
                worker_name=worker_name,
                job_kind=_as_kind(job_kind),
                trigger_source=_as_trigger(trigger_source),
                status=WorkerRunStatus.RUNNING,
                scope_user_id=scope_user_id,
                result={},
            )
            db.add(run)
            await db.flush()
            run_id = run.id
            await _enforce_retention(db, scope_user_id=scope_user_id)
            await db.commit()
            return run_id
    except Exception:
        logger.exception("worker_runs.start_failed")
        return None


async def finish_run(
    run_id: uuid.UUID | None,
    *,
    status: str | WorkerRunStatus = WorkerRunStatus.SUCCEEDED,
    result: Mapping[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    """Mark a worker run finished with optional result payload."""

    if run_id is None:
        return

    try:
        async with AsyncSessionLocal() as db:
            run = await db.get(WorkerRun, run_id)
            if run is None:
                logger.warning("worker_runs.finish_missing", extra={"run_id": str(run_id)})
                return
            run.status = status if isinstance(status, WorkerRunStatus) else WorkerRunStatus(status)
            run.finished_at = datetime.now(UTC)
            run.result = dict(result or {})
            run.error_message = _truncate_error(error_message)
            await db.commit()
    except Exception:
        logger.exception("worker_runs.finish_failed", extra={"run_id": str(run_id)})


async def _enforce_retention(
    db: AsyncSession,
    *,
    scope_user_id: uuid.UUID | None,
) -> None:
    """Keep the newest N global runs and newest N per scoped user."""

    keep = PER_USER_RETENTION if scope_user_id is not None else GLOBAL_RETENTION
    stmt = select(WorkerRun.id).order_by(WorkerRun.started_at.desc())
    if scope_user_id is not None:
        stmt = stmt.where(WorkerRun.scope_user_id == scope_user_id)
    else:
        stmt = stmt.where(WorkerRun.scope_user_id.is_(None))
    result = await db.execute(stmt.offset(keep))
    stale_ids = list(result.scalars().all())
    if not stale_ids:
        return
    await db.execute(delete(WorkerRun).where(WorkerRun.id.in_(stale_ids)))


async def list_worker_runs(
    db: AsyncSession,
    *,
    limit: int = 20,
    scope_user_id: uuid.UUID | None = None,
    scope: str = "all",
) -> list[WorkerRun]:
    """Return recent worker runs, newest first."""

    limit = max(1, min(limit, 100))
    stmt = select(WorkerRun).order_by(WorkerRun.started_at.desc()).limit(limit)
    if scope == "me" and scope_user_id is not None:
        stmt = stmt.where(WorkerRun.scope_user_id == scope_user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def latest_worker_runs(
    db: AsyncSession,
    *,
    scope_user_id: uuid.UUID | None = None,
) -> dict[str, WorkerRun | None]:
    """Return latest run cards: daily_bundle, fleet insights, current-user insights."""

    async def _latest(
        *,
        job_kind: WorkerJobKind,
        scoped: uuid.UUID | None | object = ...,
    ) -> WorkerRun | None:
        stmt = (
            select(WorkerRun)
            .where(WorkerRun.job_kind == job_kind)
            .order_by(WorkerRun.started_at.desc())
            .limit(1)
        )
        if scoped is not ...:
            if scoped is None:
                stmt = stmt.where(WorkerRun.scope_user_id.is_(None))
            else:
                stmt = stmt.where(WorkerRun.scope_user_id == scoped)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    return {
        "daily_bundle": await _latest(job_kind=WorkerJobKind.DAILY_BUNDLE),
        "fleet_insights": await _latest(
            job_kind=WorkerJobKind.INSIGHTS,
            scoped=None,
        ),
        "user_insights": (
            await _latest(job_kind=WorkerJobKind.USER_INSIGHTS, scoped=scope_user_id)
            if scope_user_id is not None
            else None
        ),
    }


async def latest_successful_insight_run_at(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> datetime | None:
    """Return the completed time of this user's latest successful generation.

    Unlike ``Insight.generated_at``, this is refreshed when a run succeeds
    with zero candidates.  It is deliberately scoped to ``USER_INSIGHTS`` so
    a global worker heartbeat cannot make an individual user's stale feed look
    fresh when their generation failed.
    """

    result = await db.execute(
        select(WorkerRun.finished_at)
        .where(
            WorkerRun.scope_user_id == user_id,
            WorkerRun.job_kind == WorkerJobKind.USER_INSIGHTS,
            WorkerRun.status == WorkerRunStatus.SUCCEEDED,
            WorkerRun.finished_at.is_not(None),
        )
        .order_by(WorkerRun.finished_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()

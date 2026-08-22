"""Background worker entrypoint for scheduled maintenance and analytics jobs."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.worker_run import WorkerJobKind, WorkerRunStatus, WorkerTriggerSource
from app.services.cleanup_service import cleanup_unverified_accounts
from app.services.insight_worker_service import (
    generate_insights_for_job,
    list_insight_generation_jobs,
)
from app.services.sync_conflict_service import cleanup_stale_sync_conflicts
from app.services.worker_run_service import finish_run, start_run
from app.workers.digest import DigestRunSummary, run_digest_once

logger = logging.getLogger(__name__)

CleanupSleep = Callable[[float], Awaitable[None]]
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

# Weekly insight digest runs as part of the daily bundle on this weekday
# (Monday=0 … Sunday=6). It piggybacks on the daily 03:00 UTC slot so no
# separate scheduler or container is needed; the per-user ``digest_enabled``
# preference remains the only opt-in (#738).
DIGEST_WEEKDAY = 6  # Sunday


def is_weekly_digest_slot(now: datetime | None = None) -> bool:
    """Return True when the daily run should also generate weekly digests."""

    return (now or datetime.now(UTC)).weekday() == DIGEST_WEEKDAY


@dataclass(frozen=True)
class InsightRunSummary:
    """Aggregated result for one scheduled insight-generation run."""

    eligible_users: int
    processed_users: int
    failed_users: int
    generated_insights: int


@dataclass(frozen=True)
class CleanupRunSummary:
    """Aggregated result for retention cleanup, including isolated failures."""

    deleted_unverified_accounts: int
    deleted_sync_conflicts: int
    step_errors: tuple[tuple[str, str], ...] = ()

    @property
    def has_errors(self) -> bool:
        """Return whether at least one cleanup step failed."""

        return bool(self.step_errors)

    @property
    def error_message(self) -> str | None:
        """Return a compact telemetry message for isolated step failures."""

        if not self.step_errors:
            return None
        return "; ".join(f"{step}: {error}" for step, error in self.step_errors)


@dataclass(frozen=True)
class DailyRunSummary:
    """Aggregated result for all daily worker jobs."""

    deleted_unverified_accounts: int
    deleted_sync_conflicts: int
    insight_run: InsightRunSummary
    digest_run: DigestRunSummary | None = None
    cleanup_step_errors: tuple[tuple[str, str], ...] = ()


def seconds_until_next_cleanup(now: datetime | None = None) -> float:
    """Return seconds until the next 03:00 UTC cleanup slot."""
    current = now or datetime.now(UTC)
    run_at = datetime.combine(current.date(), time(hour=3, tzinfo=UTC))
    if run_at <= current:
        run_at += timedelta(days=1)
    return (run_at - current).total_seconds()


async def run_cleanup_once(
    *,
    session_factory: SessionFactory = AsyncSessionLocal,
    trigger_source: str | WorkerTriggerSource = WorkerTriggerSource.SCHEDULED,
    record_run: bool = True,
) -> CleanupRunSummary:
    """Run retention cleanups and return counts plus isolated step errors."""

    run_id = None
    if record_run:
        run_id = await start_run(
            job_kind=WorkerJobKind.CLEANUP,
            trigger_source=trigger_source,
        )
    deleted_accounts = 0
    deleted_conflicts = 0
    step_errors: dict[str, str] = {}
    try:
        async with session_factory() as session:
            # #752 (Bulkhead): each retention step runs in its own SAVEPOINT.
            # Previously both ran in one implicit transaction — a failure in
            # either aborted both and rolled back everything, even the parts
            # that had already succeeded. Now a failing step is isolated,
            # logged, and skipped; the other step and its results survive.
            try:
                async with session.begin_nested():
                    cleanup_result = await cleanup_unverified_accounts(session)
                deleted_accounts = cleanup_result.deleted_count
                # #752 (Bulkhead): individual account deletes are isolated in
                # their own SAVEPOINTs inside cleanup_unverified_accounts, so a
                # per-user failure does not raise here. Surface those isolated
                # failures as a step error so a batch where every delete fails
                # is recorded as FAILED instead of a healthy no-op run.
                if cleanup_result.has_failures:
                    step_errors["unverified_accounts"] = (
                        f"{len(cleanup_result.failed_user_ids)} account delete(s) failed"
                    )
                    logger.error(
                        "unverified account cleanup had isolated per-user failures",
                        extra={"failed_count": len(cleanup_result.failed_user_ids)},
                    )
            except Exception as exc:
                step_errors["unverified_accounts"] = str(exc)
                logger.exception("unverified account cleanup step failed")

            try:
                async with session.begin_nested():
                    deleted_conflicts = await cleanup_stale_sync_conflicts(session)
            except Exception as exc:
                step_errors["sync_conflicts"] = str(exc)
                logger.exception("sync conflict cleanup step failed")

            await session.commit()

        summary = CleanupRunSummary(
            deleted_unverified_accounts=deleted_accounts,
            deleted_sync_conflicts=deleted_conflicts,
            step_errors=tuple(step_errors.items()),
        )
        result = {
            "deleted_unverified_accounts": deleted_accounts,
            "deleted_sync_conflicts": deleted_conflicts,
        }
        if record_run:
            await finish_run(
                run_id,
                status=WorkerRunStatus.FAILED if summary.has_errors else WorkerRunStatus.SUCCEEDED,
                result=result,
                error_message=summary.error_message,
            )
        return summary
    except Exception as exc:
        if record_run:
            await finish_run(
                run_id,
                status=WorkerRunStatus.FAILED,
                error_message=str(exc),
            )
        raise


async def run_insights_once(
    *,
    as_of: datetime | None = None,
    session_factory: SessionFactory = AsyncSessionLocal,
    trigger_source: str | WorkerTriggerSource = WorkerTriggerSource.SCHEDULED,
) -> InsightRunSummary:
    """Run scheduled M3 insight generation for all eligible users.

    Each user is processed in a separate transaction so a bad DEK or a data
    issue for one account cannot poison the rest of the batch.
    """

    generated_for_date = (as_of or datetime.now(UTC)).date()
    run_id = await start_run(
        job_kind=WorkerJobKind.INSIGHTS,
        trigger_source=trigger_source,
    )
    try:
        async with session_factory() as session:
            jobs = await list_insight_generation_jobs(session)

        processed = 0
        failed = 0
        generated = 0
        for job in jobs:
            async with session_factory() as session:
                try:
                    # #753 (I): a pathological single user (huge history,
                    # hung query, runaway computation) must not stall every
                    # subsequent user for the rest of the night — the loop
                    # is otherwise sequential.
                    generated += await asyncio.wait_for(
                        generate_insights_for_job(
                            session,
                            job=job,
                            as_of=generated_for_date,
                        ),
                        timeout=settings.WORKER_JOB_TIMEOUT_SECONDS,
                    )
                    await session.commit()
                    processed += 1
                except TimeoutError:
                    # Cancelling the coroutine does not itself stop an
                    # in-flight Postgres statement. The 30-second
                    # ``statement_timeout`` configured in db/session.py is
                    # the second line of defense that releases that connection
                    # even when driver-side cancellation is delayed.
                    await session.rollback()
                    failed += 1
                    logger.exception(
                        "insight generation timed out",
                        extra={
                            "user_id": str(job.user_id),
                            "timeout_seconds": settings.WORKER_JOB_TIMEOUT_SECONDS,
                        },
                    )
                except Exception:
                    await session.rollback()
                    failed += 1
                    logger.exception(
                        "insight generation failed",
                        extra={"user_id": str(job.user_id)},
                    )

        summary = InsightRunSummary(
            eligible_users=len(jobs),
            processed_users=processed,
            failed_users=failed,
            generated_insights=generated,
        )
        logger.info(
            "insight generation completed",
            extra={
                "eligible_users": summary.eligible_users,
                "processed_users": summary.processed_users,
                "failed_users": summary.failed_users,
                "generated_insights": summary.generated_insights,
            },
        )
        await finish_run(
            run_id,
            status=WorkerRunStatus.SUCCEEDED,
            result={
                "eligible_users": summary.eligible_users,
                "processed_users": summary.processed_users,
                "failed_users": summary.failed_users,
                "generated_insights": summary.generated_insights,
                "generated_for_date": generated_for_date.isoformat(),
            },
        )
        return summary
    except Exception as exc:
        await finish_run(
            run_id,
            status=WorkerRunStatus.FAILED,
            error_message=str(exc),
        )
        raise


async def run_daily_jobs_once(
    *,
    now: datetime | None = None,
    session_factory: SessionFactory = AsyncSessionLocal,
    trigger_source: str | WorkerTriggerSource = WorkerTriggerSource.SCHEDULED,
) -> DailyRunSummary:
    """Run the daily worker bundle once."""

    current = now or datetime.now(UTC)
    run_id = await start_run(
        job_kind=WorkerJobKind.DAILY_BUNDLE,
        trigger_source=trigger_source,
    )
    try:
        # Nested cleanup/insights runs are recorded separately; skip duplicate
        # cleanup-only row when it is part of the bundle by recording cleanup
        # outcomes only on the daily_bundle + insights rows.
        cleanup_run = await run_cleanup_once(
            session_factory=session_factory,
            trigger_source=trigger_source,
            record_run=False,
        )
        insight_run = await run_insights_once(
            as_of=current,
            session_factory=session_factory,
            trigger_source=trigger_source,
        )
        # Weekly digest piggybacks on the daily bundle (#738): generate it right
        # after fresh insights on the digest weekday. It records its own DIGEST
        # run row, so a digest failure is isolated from the daily bundle result.
        digest_run: DigestRunSummary | None = None
        if is_weekly_digest_slot(current):
            try:
                digest_run = await run_digest_once(
                    as_of=current,
                    trigger_source=trigger_source,
                )
            except Exception:
                logger.exception("weekly digest generation failed")
        summary = DailyRunSummary(
            deleted_unverified_accounts=cleanup_run.deleted_unverified_accounts,
            deleted_sync_conflicts=cleanup_run.deleted_sync_conflicts,
            insight_run=insight_run,
            digest_run=digest_run,
            cleanup_step_errors=cleanup_run.step_errors,
        )
        result: dict[str, object] = {
            "deleted_unverified_accounts": cleanup_run.deleted_unverified_accounts,
            "deleted_sync_conflicts": cleanup_run.deleted_sync_conflicts,
            "eligible_users": insight_run.eligible_users,
            "processed_users": insight_run.processed_users,
            "failed_users": insight_run.failed_users,
            "generated_insights": insight_run.generated_insights,
        }
        if cleanup_run.has_errors:
            result["cleanup_failed_steps"] = [step for step, _ in cleanup_run.step_errors]
        if digest_run is not None:
            result["digest_eligible_users"] = digest_run.eligible_users
            result["digest_processed_users"] = digest_run.processed_users
        await finish_run(
            run_id,
            # Cleanup's per-step bulkhead intentionally lets later work
            # continue, but a partial cleanup must not look healthy in the
            # daily bundle telemetry (#762 Codex finding).
            status=WorkerRunStatus.FAILED if cleanup_run.has_errors else WorkerRunStatus.SUCCEEDED,
            result=result,
            error_message=cleanup_run.error_message,
        )
        return summary
    except Exception as exc:
        await finish_run(
            run_id,
            status=WorkerRunStatus.FAILED,
            error_message=str(exc),
        )
        raise


async def run_worker(*, sleep: CleanupSleep = asyncio.sleep) -> None:
    """Run scheduled worker jobs forever."""
    logger.info("correlcore worker started")
    while True:
        delay = seconds_until_next_cleanup()
        logger.info("next daily worker run scheduled", extra={"delay_seconds": delay})
        await sleep(delay)
        await run_daily_jobs_once(trigger_source=WorkerTriggerSource.SCHEDULED)


def _parse_worker_cli(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse one-shot worker options used by cron and manual invocations."""
    parser = argparse.ArgumentParser(description="CorrelCore analytics worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the daily worker bundle once and exit (cleanup + insights)",
    )
    parser.add_argument(
        "--source",
        choices=[source.value for source in WorkerTriggerSource],
        help=(
            "Recorded trigger source for --once; defaults to cli_once so "
            "manual invocations remain distinguishable from scheduled runs"
        ),
    )
    return parser.parse_args(argv)


def main() -> None:
    """CLI entrypoint used by Docker Compose."""
    args = _parse_worker_cli()
    logging.basicConfig(level=logging.INFO)
    if args.once:
        trigger_source = (
            WorkerTriggerSource(args.source) if args.source else WorkerTriggerSource.CLI_ONCE
        )
        asyncio.run(run_daily_jobs_once(trigger_source=trigger_source))
        return
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

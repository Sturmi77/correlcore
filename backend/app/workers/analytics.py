"""Background worker entrypoint for scheduled maintenance and analytics jobs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.cleanup_service import cleanup_unverified_accounts
from app.services.insight_worker_service import (
    generate_insights_for_job,
    list_insight_generation_jobs,
)
from app.services.sync_conflict_service import cleanup_stale_sync_conflicts

logger = logging.getLogger(__name__)

CleanupSleep = Callable[[float], Awaitable[None]]
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(frozen=True)
class InsightRunSummary:
    """Aggregated result for one scheduled insight-generation run."""

    eligible_users: int
    processed_users: int
    failed_users: int
    generated_insights: int


@dataclass(frozen=True)
class DailyRunSummary:
    """Aggregated result for all daily worker jobs."""

    deleted_unverified_accounts: int
    deleted_sync_conflicts: int
    insight_run: InsightRunSummary


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
) -> tuple[int, int]:
    """Run retention cleanups in one transaction and return deleted row counts."""
    async with session_factory() as session:
        try:
            deleted_accounts = await cleanup_unverified_accounts(session)
            deleted_conflicts = await cleanup_stale_sync_conflicts(session)
            await session.commit()
            return deleted_accounts, deleted_conflicts
        except Exception:
            await session.rollback()
            logger.exception("daily retention cleanup failed")
            raise


async def run_insights_once(
    *,
    as_of: datetime | None = None,
    session_factory: SessionFactory = AsyncSessionLocal,
) -> InsightRunSummary:
    """Run scheduled M3 insight generation for all eligible users.

    Each user is processed in a separate transaction so a bad DEK or a data
    issue for one account cannot poison the rest of the batch.
    """

    generated_for_date = (as_of or datetime.now(UTC)).date()
    async with session_factory() as session:
        jobs = await list_insight_generation_jobs(session)

    processed = 0
    failed = 0
    generated = 0
    for job in jobs:
        async with session_factory() as session:
            try:
                generated += await generate_insights_for_job(
                    session,
                    job=job,
                    as_of=generated_for_date,
                )
                await session.commit()
                processed += 1
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
    return summary


async def run_daily_jobs_once(
    *,
    now: datetime | None = None,
    session_factory: SessionFactory = AsyncSessionLocal,
) -> DailyRunSummary:
    """Run the daily worker bundle once."""

    current = now or datetime.now(UTC)
    deleted_accounts, deleted_conflicts = await run_cleanup_once(session_factory=session_factory)
    insight_run = await run_insights_once(as_of=current, session_factory=session_factory)
    return DailyRunSummary(
        deleted_unverified_accounts=deleted_accounts,
        deleted_sync_conflicts=deleted_conflicts,
        insight_run=insight_run,
    )


async def run_worker(*, sleep: CleanupSleep = asyncio.sleep) -> None:
    """Run scheduled worker jobs forever."""
    logger.info("correlcore worker started")
    while True:
        delay = seconds_until_next_cleanup()
        logger.info("next daily worker run scheduled", extra={"delay_seconds": delay})
        await sleep(delay)
        await run_daily_jobs_once()


def main() -> None:
    """CLI entrypoint used by Docker Compose."""
    import argparse

    parser = argparse.ArgumentParser(description="CorrelCore analytics worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the daily worker bundle once and exit (cleanup + insights)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.once:
        asyncio.run(run_daily_jobs_once())
        return
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

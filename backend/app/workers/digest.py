"""Weekly insight digest worker (#147).

No in-process APScheduler is wired today. Run manually or from cron:

    python -m app.workers.digest --once

Suggested cron (Sunday ~17:00 UTC):

    0 17 * * 0 cd /app/backend && uv run python -m app.workers.digest --once
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.user import User
from app.models.user_preference import UserPreference
from app.models.worker_run import WorkerJobKind, WorkerRunStatus, WorkerTriggerSource
from app.services.insight_digest import (
    DigestNotAvailableError,
    get_latest_weekly_digest,
    store_weekly_digest,
)
from app.services.worker_run_service import finish_run, start_run

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DigestRunSummary:
    eligible_users: int
    processed_users: int
    skipped_users: int
    failed_users: int


def seconds_until_next_digest(now: datetime | None = None) -> float:
    """Return seconds until the next Sunday 17:00 UTC digest slot."""

    current = now or datetime.now(UTC)
    days_ahead = (6 - current.weekday()) % 7
    run_at = datetime.combine(
        current.date() + timedelta(days=days_ahead),
        time(hour=17, tzinfo=UTC),
    )
    if run_at <= current:
        run_at += timedelta(days=7)
    return (run_at - current).total_seconds()


async def _list_digest_user_ids(db: AsyncSession) -> list:
    result = await db.execute(
        select(User.id)
        .outerjoin(UserPreference, UserPreference.user_id == User.id)
        .where(
            User.is_active.is_(True),
            User.is_verified.is_(True),
            or_(UserPreference.analytics_enabled.is_(True), UserPreference.user_id.is_(None)),
            or_(UserPreference.digest_enabled.is_(True), UserPreference.user_id.is_(None)),
        )
        .order_by(User.id.asc())
    )
    return list(result.scalars().all())


async def run_digest_once(
    *,
    as_of: datetime | None = None,
    trigger_source: str | WorkerTriggerSource = WorkerTriggerSource.SCHEDULED,
) -> DigestRunSummary:
    """Generate and store weekly digests for all eligible users."""

    current = as_of or datetime.now(UTC)
    run_id = await start_run(
        job_kind=WorkerJobKind.DIGEST,
        trigger_source=trigger_source,
    )
    processed = 0
    skipped = 0
    failed = 0
    try:
        async with AsyncSessionLocal() as session:
            user_ids = await _list_digest_user_ids(session)

        for user_id in user_ids:
            async with AsyncSessionLocal() as session:
                try:
                    await bind_rls_current_user(session, user_id)
                    digest = await get_latest_weekly_digest(session, user_id=user_id, as_of=current)
                    await store_weekly_digest(session, user_id=user_id, digest=digest)
                    await session.commit()
                    processed += 1
                except DigestNotAvailableError:
                    await session.rollback()
                    skipped += 1
                except Exception:
                    await session.rollback()
                    failed += 1
                    logger.exception("digest generation failed", extra={"user_id": str(user_id)})

        summary = DigestRunSummary(
            eligible_users=len(user_ids),
            processed_users=processed,
            skipped_users=skipped,
            failed_users=failed,
        )
        await finish_run(
            run_id,
            status=WorkerRunStatus.SUCCEEDED,
            result={
                "eligible_users": summary.eligible_users,
                "processed_users": summary.processed_users,
                "skipped_users": summary.skipped_users,
                "failed_users": summary.failed_users,
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


async def run_digest_worker(*, sleep: asyncio.sleep = asyncio.sleep) -> None:
    """Run weekly digest generation forever on Sunday 17:00 UTC."""

    logger.info("correlcore digest worker started")
    while True:
        delay = seconds_until_next_digest()
        logger.info("next digest run scheduled", extra={"delay_seconds": delay})
        await sleep(delay)
        await run_digest_once(trigger_source=WorkerTriggerSource.SCHEDULED)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="CorrelCore weekly insight digest worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run digest generation once and exit",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.once:
        asyncio.run(run_digest_once(trigger_source=WorkerTriggerSource.CLI_ONCE))
        return
    asyncio.run(run_digest_worker())


if __name__ == "__main__":
    main()

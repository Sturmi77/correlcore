"""Background worker entrypoint for scheduled maintenance jobs.

M2 only needs the privacy-retention cleanup for unverified accounts. The
module name stays ``analytics`` because the Compose stacks already reserved
that worker slot for M2+ jobs.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, time, timedelta

from app.db.session import AsyncSessionLocal
from app.services.cleanup_service import cleanup_unverified_accounts

logger = logging.getLogger(__name__)

CleanupSleep = Callable[[float], Awaitable[None]]


def seconds_until_next_cleanup(now: datetime | None = None) -> float:
    """Return seconds until the next 03:00 UTC cleanup slot."""
    current = now or datetime.now(UTC)
    run_at = datetime.combine(current.date(), time(hour=3, tzinfo=UTC))
    if run_at <= current:
        run_at += timedelta(days=1)
    return (run_at - current).total_seconds()


async def run_cleanup_once() -> int:
    """Run the cleanup in its own transaction and return deleted rows."""
    async with AsyncSessionLocal() as session:
        try:
            deleted_count = await cleanup_unverified_accounts(session)
            await session.commit()
            return deleted_count
        except Exception:
            await session.rollback()
            logger.exception("unverified account cleanup failed")
            raise


async def run_worker(*, sleep: CleanupSleep = asyncio.sleep) -> None:
    """Run scheduled worker jobs forever."""
    logger.info("moodsync worker started")
    while True:
        delay = seconds_until_next_cleanup()
        logger.info("next unverified account cleanup scheduled", extra={"delay_seconds": delay})
        await sleep(delay)
        await run_cleanup_once()


def main() -> None:
    """CLI entrypoint used by Docker Compose."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

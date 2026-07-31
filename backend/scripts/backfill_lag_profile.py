#!/usr/bin/env python3
"""Backfill ``lag_profile`` on persisted lag insights (#488 Phase 1b).

Older insight rows may have ``method=lag`` without the ``lag_profile`` series
required by the Insight card mini-bars and lag heatmap. This script recomputes
the series from each user's entry history and patches matching JSONB payloads.

Usage::

    cd backend
    export APP_ENV=development
    export DATABASE_URL='postgresql+asyncpg://correlcore:correlcore@localhost:5432/correlcore'
    # …same secrets as the API…
    uv run --python 3.12 python scripts/backfill_lag_profile.py --dry-run
    uv run --python 3.12 python scripts/backfill_lag_profile.py
    uv run --python 3.12 python scripts/backfill_lag_profile.py --user-id <uuid>

In production containers ``scripts/`` is copied into the runtime image (#596).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid

from app.db.session import AsyncSessionLocal
from app.services.lag_profile_backfill_service import backfill_lag_profiles

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill lag_profile on persisted lag insights (#488)"
    )
    parser.add_argument(
        "--user-id",
        type=uuid.UUID,
        default=None,
        help="Limit backfill to a single user (default: all users with lag insights)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute updates inside a transaction and roll back",
    )
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()

    async with AsyncSessionLocal() as session:
        try:
            summary = await backfill_lag_profiles(session, user_id=args.user_id)
            if args.dry_run:
                await session.rollback()
                logger.info("Dry run — rolled back all changes")
            else:
                await session.commit()
                logger.info("Committed lag_profile backfill")
        except Exception:
            await session.rollback()
            logger.exception("lag_profile backfill failed")
            return 1

    logger.info(
        "Done: users=%s scanned=%s updated=%s skipped=%s unmatched=%s",
        summary.users_processed,
        summary.insights_scanned,
        summary.insights_updated,
        summary.insights_skipped,
        summary.insights_unmatched,
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))

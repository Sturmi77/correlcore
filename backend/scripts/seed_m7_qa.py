#!/usr/bin/env python3
"""Seed a deterministic M7 QA user with 90+ analytics-ready entries.

Usage (from ``backend/`` with Postgres running and migrations applied):

    uv run --python 3.12 --extra dev --extra analytics python scripts/seed_m7_qa.py
    uv run --python 3.12 --extra dev --extra analytics python scripts/seed_m7_qa.py --reset

Environment: ``DATABASE_URL``, ``SECRET_KEY``, ``ENCRYPTION_KEY`` (same as API).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime

from app.db.session import AsyncSessionLocal
from app.services.m7_qa_seed_service import (
    M7_QA_DEFAULT_DAYS,
    M7_QA_DEFAULT_DISPLAY_NAME,
    M7_QA_DEFAULT_EMAIL,
    M7_QA_DEFAULT_PASSWORD,
    format_seed_summary,
    seed_m7_qa_dataset,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed M7 QA analytics dataset")
    parser.add_argument("--email", default=M7_QA_DEFAULT_EMAIL, help="QA user email")
    parser.add_argument("--password", default=M7_QA_DEFAULT_PASSWORD, help="QA user password")
    parser.add_argument(
        "--display-name",
        default=M7_QA_DEFAULT_DISPLAY_NAME,
        help="Display name for a newly created user",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=M7_QA_DEFAULT_DAYS,
        help=f"Number of daily entries (minimum {90})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing entries, insights, and tag vectors for the QA user first",
    )
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()

    async with AsyncSessionLocal() as session:
        try:
            summary = await seed_m7_qa_dataset(
                session,
                email=args.email,
                password=args.password,
                display_name=args.display_name,
                day_count=args.days,
                end_date=datetime.now(UTC).date(),
                reset=args.reset,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("M7 QA seed failed")
            return 1

    print(format_seed_summary(summary))
    if not summary.has_lasso_or_lag:
        logger.warning(
            "No symptom_cluster (lasso/lag) insights were generated — "
            "check entry volume and tag/symptom patterns"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))

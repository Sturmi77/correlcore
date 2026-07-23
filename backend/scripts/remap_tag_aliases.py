#!/usr/bin/env python3
"""Remap historical entry_tags from curated defaults onto user COW overrides.

When a user edits a default tag, CorrelCore creates a copy-on-write override
with the same slug but a new ID. Older ``entry_tags`` can still point at the
default row, which previously produced duplicate heatmap/co-occurrence rows.

Query paths now canonicalize by slug, but this script also repairs the stored
links in a running database:

    cd backend
    export APP_ENV=development
    export DATABASE_URL='postgresql+asyncpg://correlcore:correlcore@localhost:5432/correlcore'
    # …same secrets as the API…
    uv run --python 3.12 python scripts/remap_tag_aliases.py
    uv run --python 3.12 python scripts/remap_tag_aliases.py --user-id <uuid>
    uv run --python 3.12 python scripts/remap_tag_aliases.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid

from app.db.session import AsyncSessionLocal
from app.services.tag_service import remap_all_tag_alias_entry_links

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remap default-tag entry_tags onto user override tag IDs"
    )
    parser.add_argument(
        "--user-id",
        type=uuid.UUID,
        default=None,
        help="Limit remapping to a single user (default: all users)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute remaps inside a transaction and roll back",
    )
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()

    async with AsyncSessionLocal() as session:
        try:
            changed = await remap_all_tag_alias_entry_links(session, user_id=args.user_id)
            if args.dry_run:
                await session.rollback()
                logger.info("Dry run: would remap %s entry_tag row(s)", changed)
            else:
                await session.commit()
                logger.info("Remapped %s entry_tag row(s)", changed)
        except Exception:
            await session.rollback()
            logger.exception("Tag alias remap failed")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))

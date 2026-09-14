#!/usr/bin/env python3
"""Backfill the tag system from historical ``entry_note_markers`` (#895).

Part of the #890 consolidation (Option 4 — one label system). After #893 removed
the note-marker capture UI and migration 047 seeded ``achievement`` as a default
tag, existing markers still live only in ``entry_note_markers``. This one-off
command converts them into tag links via the service layer (see
``app/services/marker_tag_backfill_service.py``) — reusing the tested tag
assignment/creation paths so copy-on-write overrides, the per-entry tag cap and
``sync_revision_log`` are all handled correctly, and hidden notes are excluded.

Idempotent: re-runs are a no-op. Run once after deploying #890/#893/047.

Usage::

    cd backend
    export APP_ENV=development
    export DATABASE_URL='postgresql+asyncpg://correlcore:correlcore@localhost:5432/correlcore'
    # …same secrets as the API…
    uv run --python 3.12 python scripts/backfill_marker_tags.py --dry-run
    uv run --python 3.12 python scripts/backfill_marker_tags.py
    uv run --python 3.12 python scripts/backfill_marker_tags.py --user-id <uuid>

In production containers ``scripts/`` is copied into the runtime image (#596).
Run migrations as the database owner / a BYPASSRLS role — the same role used for
migrations — so FORCE ROW LEVEL SECURITY on ``tags`` / ``entry_tags`` does not
silently drop writes.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid

from app.db.session import AsyncSessionLocal
from app.services.marker_tag_backfill_service import backfill_marker_tags

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill note markers → tag links via the service layer (#895)"
    )
    parser.add_argument(
        "--user-id",
        type=uuid.UUID,
        default=None,
        help="Limit backfill to a single user (default: all active verified users)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the backfill inside a transaction and roll back",
    )
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()

    async with AsyncSessionLocal() as session:
        try:
            summary = await backfill_marker_tags(session, user_id=args.user_id)
            if args.dry_run:
                await session.rollback()
                logger.info("Dry run — rolled back all changes")
            else:
                await session.commit()
                logger.info("Committed marker → tag backfill")
        except Exception:
            await session.rollback()
            logger.exception("marker → tag backfill failed")
            return 1

    logger.info(
        "Done: users=%s entries=%s predefined_links=%s custom_tags=%s custom_links=%s",
        summary.users_processed,
        summary.entries_updated,
        summary.predefined_links_added,
        summary.custom_tags_created,
        summary.custom_links_added,
    )
    logger.info(
        "Skipped: unsluggable=%s default_clash=%s hidden_target=%s over_cap=%s",
        summary.skipped_unsluggable,
        summary.skipped_default_clash,
        summary.skipped_hidden_target,
        summary.skipped_over_cap,
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))

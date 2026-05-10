"""Retention cleanup jobs for privacy-sensitive account lifecycle data."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


async def cleanup_unverified_accounts(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    retention_days: int | None = None,
) -> int:
    """Delete stale unverified accounts and return the deleted row count.

    The delete is intentionally scoped to ``is_verified = false`` and
    ``created_at < threshold``. Accounts exactly on the threshold remain for
    the next run, avoiding off-by-one deletes around scheduler clock drift.
    """
    effective_now = now or datetime.now(UTC)
    days = retention_days if retention_days is not None else settings.UNVERIFIED_CLEANUP_DAYS
    threshold = effective_now - timedelta(days=days)

    result = await db.execute(
        delete(User)
        .where(User.is_verified.is_(False))
        .where(User.created_at < threshold)
        .returning(User.id)
    )
    deleted_ids = [str(user_id) for user_id in result.scalars().all()]

    logger.info(
        "unverified account cleanup completed",
        extra={
            "deleted_count": len(deleted_ids),
            "user_ids": deleted_ids,
        },
    )
    return len(deleted_ids)

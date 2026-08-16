"""Retention cleanup jobs for privacy-sensitive account lifecycle data."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import bind_rls_current_user
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

    Production runs as ``correlcore_app`` under FORCE RLS. A bulk
    ``DELETE FROM users`` can see the parent rows (``users`` has no RLS) but
    cascaded child deletes (``user_encryption_keys``, …) are planned with the
    session GUC. With ``app.current_user_id`` unset, those children are
    invisible, the FK check still sees them, and the statement raises
    IntegrityError — the same class of failure as admin purge before #698.
    That exception aborts the daily worker bundle, so scheduled insight
    generation never runs for anyone that night. Bind each target before
    deleting so CASCADE can see their rows.
    """
    effective_now = now or datetime.now(UTC)
    days = retention_days if retention_days is not None else settings.UNVERIFIED_CLEANUP_DAYS
    threshold = effective_now - timedelta(days=days)

    listed = await db.execute(
        select(User.id).where(User.is_verified.is_(False)).where(User.created_at < threshold)
    )
    user_ids = list(listed.scalars().all())

    deleted_ids: list[str] = []
    for user_id in user_ids:
        await bind_rls_current_user(db, user_id)
        # Re-apply the retention predicates on DELETE. Postgres READ COMMITTED
        # waits for a concurrent verify_email row lock, then rechecks WHERE.
        # A bare ``DELETE … WHERE id = :id`` would wipe the account after a
        # successful verification in that window.
        result = await db.execute(
            delete(User)
            .where(User.id == user_id)
            .where(User.is_verified.is_(False))
            .where(User.created_at < threshold)
        )
        if result.rowcount:
            deleted_ids.append(str(user_id))

    logger.info(
        "unverified account cleanup completed",
        extra={
            "deleted_count": len(deleted_ids),
            "user_ids": deleted_ids,
        },
    )
    return len(deleted_ids)

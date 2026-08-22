"""Retention cleanup jobs for privacy-sensitive account lifecycle data."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import bind_rls_current_user
from app.models.user import User

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UnverifiedCleanupResult:
    """Outcome of an unverified-account cleanup pass.

    ``deleted_count`` counts the rows actually removed. ``failed_user_ids``
    carries the per-user deletes that raised and were isolated in their own
    SAVEPOINT — these must be surfaced to the caller so a batch where deletes
    silently fail is not recorded as a healthy run.
    """

    deleted_count: int
    failed_user_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_failures(self) -> bool:
        """Return whether at least one targeted account delete failed."""

        return bool(self.failed_user_ids)


async def cleanup_unverified_accounts(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    retention_days: int | None = None,
) -> UnverifiedCleanupResult:
    """Delete stale unverified accounts and return deleted count plus failures.

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

    # #752 (Bulkhead): each delete runs in its own SAVEPOINT so one user's
    # IntegrityError (the RLS/FK cascade failure class documented above)
    # only rolls back that one delete, not the whole cleanup transaction —
    # the remaining users, and the sync-conflict cleanup that follows in
    # the same transaction, still get a chance to run.
    deleted_ids: list[str] = []
    failed_ids: list[str] = []
    for user_id in user_ids:
        try:
            async with db.begin_nested():
                await bind_rls_current_user(db, user_id)
                # Re-apply the retention predicates on DELETE. Postgres READ
                # COMMITTED waits for a concurrent verify_email row lock, then
                # rechecks WHERE. A bare ``DELETE … WHERE id = :id`` would wipe
                # the account after a successful verification in that window
                # (#712 leftover from #709; still present after #762 SAVEPOINTs).
                result = await db.execute(
                    delete(User)
                    .where(User.id == user_id)
                    .where(User.is_verified.is_(False))
                    .where(User.created_at < threshold)
                )
            # CursorResult.rowcount is int at runtime; Result stubs vary, so
            # read it defensively for mypy without treating a raced 0-row
            # delete as a failure (the user verified or aged out of scope).
            deleted_rows = int(getattr(result, "rowcount", 0) or 0)
            if deleted_rows > 0:
                deleted_ids.append(str(user_id))
        except Exception:
            failed_ids.append(str(user_id))
            logger.exception(
                "unverified account cleanup failed for user",
                extra={"user_id": str(user_id)},
            )

    logger.info(
        "unverified account cleanup completed",
        extra={
            "deleted_count": len(deleted_ids),
            "user_ids": deleted_ids,
            "failed_count": len(failed_ids),
            "failed_user_ids": failed_ids,
        },
    )
    return UnverifiedCleanupResult(
        deleted_count=len(deleted_ids),
        failed_user_ids=tuple(failed_ids),
    )

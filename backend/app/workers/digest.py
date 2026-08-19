"""Weekly insight digest generation (#147, #738).

Scheduled generation runs as part of the daily analytics worker on the digest
weekday (see ``app.workers.analytics.is_weekly_digest_slot``) — there is no
separate scheduler, container, or compose profile. The per-user
``digest_enabled`` preference is the only opt-in.

For manual runs or one-off backfills:

    python -m app.workers.digest --once
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import reset_current_user_dek, set_current_user_dek, unwrap_dek
from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.user import User
from app.models.user_encryption_key import UserEncryptionKey
from app.models.user_preference import UserPreference
from app.models.worker_run import WorkerJobKind, WorkerRunStatus, WorkerTriggerSource
from app.services.insight_digest import (
    DigestNotAvailableError,
    compute_weekly_digest_for_user,
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


async def _list_digest_user_ids(db: AsyncSession) -> list[uuid.UUID]:
    """Return opted-in users. ``users`` has no RLS; preferences are FORCE-RLS.

    A single join against ``user_preferences`` with no GUC hides every pref
    row from ``correlcore_app``, so ``digest_enabled IS TRUE`` never matches
    and the weekly worker processes nobody. List candidates from ``users``,
    then bind each id before reading their preference row.
    """

    result = await db.execute(
        select(User.id)
        .where(
            User.is_active.is_(True),
            User.is_verified.is_(True),
        )
        .order_by(User.id.asc())
    )
    eligible: list[uuid.UUID] = []
    for user_id in result.scalars().all():
        await bind_rls_current_user(db, user_id)
        pref = (
            await db.execute(
                select(UserPreference.analytics_enabled, UserPreference.digest_enabled).where(
                    UserPreference.user_id == user_id
                )
            )
        ).first()
        if pref is None:
            # Opt-in: require an explicit preferences row with digest_enabled=true.
            # Migration 031 reset the legacy rows that carried true from the
            # pre-#398 default, so this now really does mean "user opted in".
            continue
        analytics_enabled, digest_enabled = pref
        if analytics_enabled is not True or digest_enabled is not True:
            continue
        eligible.append(user_id)
    return eligible


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
                dek_token = None
                try:
                    await bind_rls_current_user(session, user_id)
                    key_result = await session.execute(
                        select(UserEncryptionKey.wrapped_dek).where(
                            UserEncryptionKey.user_id == user_id
                        )
                    )
                    wrapped_dek = key_result.scalar_one_or_none()
                    if wrapped_dek is None:
                        skipped += 1
                        continue
                    dek_token = set_current_user_dek(user_id, unwrap_dek(wrapped_dek))
                    # Always recompute on worker runs (do not prefer a prior store).
                    digest = await compute_weekly_digest_for_user(
                        session,
                        user_id=user_id,
                        as_of=current,
                        require_enabled=False,
                    )
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
                finally:
                    if dek_token is not None:
                        reset_current_user_dek(dek_token)

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


def main() -> None:
    """Manual / backfill entrypoint. Scheduled runs live in the daily worker."""

    import argparse

    parser = argparse.ArgumentParser(
        description="CorrelCore weekly insight digest — one-off generation",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run digest generation once and exit (default; kept for compatibility)",
    )
    parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_digest_once(trigger_source=WorkerTriggerSource.CLI_ONCE))


if __name__ == "__main__":
    main()

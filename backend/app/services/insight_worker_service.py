"""Worker-facing orchestration helpers for M3 insight generation."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import date as date_type
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import reset_current_user_dek, set_current_user_dek, unwrap_dek
from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.user import User
from app.models.user_encryption_key import UserEncryptionKey
from app.models.user_preference import UserPreference
from app.services.insight_engine import InsightLockTimeoutError, generate_and_store_insights
from app.services.tag_cluster_service import recompute_tag_vectors_and_clusters

logger = logging.getLogger(__name__)

POST_BATCH_DEBOUNCE_SECONDS = 300
INSIGHT_REGENERATE_COOLDOWN_SECONDS = 3600


class AnalyticsDisabledError(Exception):
    """Raised when the user opted out of analytics processing."""


class InsightJobNotFoundError(Exception):
    """Raised when a user has no encryption key for insight generation."""


@dataclass(frozen=True)
class InsightGenerationJob:
    """Minimal per-user input needed by the analytics worker."""

    user_id: uuid.UUID
    wrapped_dek: bytes | memoryview


@dataclass(frozen=True)
class InsightPipelineResult:
    """Outcome of a full insight + tag-cluster regeneration run."""

    generated_for_date: date_type
    insight_count: int
    tag_clusters_status: Literal["ok", "insufficient_data"]
    trigger_source: str


async def list_insight_generation_jobs(db: AsyncSession) -> list[InsightGenerationJob]:
    """Return users eligible for scheduled insight generation.

    The query is intentionally narrow: only active, verified users with a
    wrapped DEK are included, and users who explicitly disabled analytics are
    skipped. Missing ``user_preferences`` rows default to opted-in until the
    preference endpoint exists.
    """

    result = await db.execute(
        select(User.id)
        .where(
            User.is_active.is_(True),
            User.is_verified.is_(True),
        )
        .order_by(User.id.asc())
    )
    user_ids = result.scalars().all()

    # #752 (Bulkhead): listing runs read-only per user, but any failing
    # statement still poisons the shared transaction until rolled back. A
    # SAVEPOINT per user keeps one bad lookup from wiping out every
    # subsequent user's eligibility check for the night.
    jobs: list[InsightGenerationJob] = []
    for user_id in user_ids:
        try:
            async with db.begin_nested():
                await bind_rls_current_user(db, user_id)
                job = await load_insight_generation_job(db, user_id=user_id)
            if job is not None:
                jobs.append(job)
        except Exception:
            logger.exception(
                "insight job listing failed for user",
                extra={"user_id": str(user_id)},
            )

    return jobs


async def load_insight_generation_job(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> InsightGenerationJob | None:
    """Return a generation job for one user when analytics is enabled and a DEK exists."""

    job_result = await db.execute(
        select(UserEncryptionKey.wrapped_dek, UserPreference.analytics_enabled)
        .outerjoin(UserPreference, UserPreference.user_id == UserEncryptionKey.user_id)
        .where(UserEncryptionKey.user_id == user_id)
    )
    row = job_result.first()
    if row is None:
        return None
    wrapped_dek, analytics_enabled = row
    if analytics_enabled is False:
        return None
    return InsightGenerationJob(user_id=user_id, wrapped_dek=wrapped_dek)


async def _analytics_enabled(db: AsyncSession, *, user_id: uuid.UUID) -> bool:
    preference_result = await db.execute(
        select(UserPreference.analytics_enabled).where(UserPreference.user_id == user_id)
    )
    enabled = preference_result.scalar_one_or_none()
    return enabled is not False


async def _run_insight_pipeline_for_job(
    db: AsyncSession,
    *,
    job: InsightGenerationJob,
    as_of: date_type,
) -> tuple[int, Literal["ok", "insufficient_data"]]:
    """Generate insights and recompute tag vectors for one user with DEK bound."""

    dek = unwrap_dek(job.wrapped_dek)
    token = set_current_user_dek(job.user_id, dek)
    tag_clusters_status: Literal["ok", "insufficient_data"] = "insufficient_data"
    try:
        await bind_rls_current_user(db, job.user_id)
        try:
            insights = await generate_and_store_insights(db, user_id=job.user_id, as_of=as_of)
        except InsightLockTimeoutError:
            # Lock contention is an expected, temporary outcome of overlapping
            # scheduled, post-batch and manual runs. Propagate it unchanged so
            # each caller can apply its own no-storm policy.
            logger.info(
                "insight generation deferred because another run holds the lock",
                extra={"user_id": str(job.user_id)},
            )
            raise
        try:
            async with db.begin_nested():
                clusters = await recompute_tag_vectors_and_clusters(
                    db, user_id=job.user_id, as_of=as_of
                )
                tag_clusters_status = clusters.status
        except Exception:
            logger.exception(
                "tag vector recompute failed after insight generation",
                extra={"user_id": str(job.user_id)},
            )
        return len(insights), tag_clusters_status
    finally:
        reset_current_user_dek(token)


async def generate_insights_for_job(
    db: AsyncSession,
    *,
    job: InsightGenerationJob,
    as_of: date_type,
) -> int:
    """Generate and store insights for one user with their DEK bound."""

    insight_count, _ = await _run_insight_pipeline_for_job(db, job=job, as_of=as_of)
    return insight_count


async def regenerate_insights_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type | None = None,
    trigger_source: str = "user_regenerate",
) -> InsightPipelineResult:
    """Regenerate insights and tag clusters for one user on demand."""

    from app.models.worker_run import WorkerJobKind, WorkerRunStatus
    from app.services.worker_run_service import finish_run, start_run

    # Background callers (post-batch) open a fresh session with no request GUC.
    # ``user_encryption_keys`` / ``user_preferences`` are FORCE RLS, so the
    # eligibility queries below return zero rows unless we bind first.
    await bind_rls_current_user(db, user_id)

    run_id = await start_run(
        job_kind=WorkerJobKind.USER_INSIGHTS,
        trigger_source=trigger_source,
        scope_user_id=user_id,
    )
    try:
        if not await _analytics_enabled(db, user_id=user_id):
            raise AnalyticsDisabledError(user_id)

        job = await load_insight_generation_job(db, user_id=user_id)
        if job is None:
            raise InsightJobNotFoundError(user_id)

        generated_for_date = as_of or datetime.now(UTC).date()
        insight_count, tag_clusters_status = await _run_insight_pipeline_for_job(
            db,
            job=job,
            as_of=generated_for_date,
        )
        logger.info(
            "insights.regenerated",
            extra={
                "user_id": str(user_id),
                "insight_count": insight_count,
                "tag_clusters_status": tag_clusters_status,
                "trigger_source": trigger_source,
            },
        )
        result = InsightPipelineResult(
            generated_for_date=generated_for_date,
            insight_count=insight_count,
            tag_clusters_status=tag_clusters_status,
            trigger_source=trigger_source,
        )
        await finish_run(
            run_id,
            status=WorkerRunStatus.SUCCEEDED,
            result={
                "generated_for_date": generated_for_date.isoformat(),
                "insight_count": insight_count,
                "tag_clusters_status": tag_clusters_status,
                "trigger_source": trigger_source,
            },
        )
        return result
    except Exception as exc:
        await finish_run(
            run_id,
            status=WorkerRunStatus.FAILED,
            error_message=str(exc),
            result={"trigger_source": trigger_source},
        )
        raise


async def try_acquire_regenerate_slot(*, user_id: uuid.UUID) -> bool:
    """Return True when the user may start a new on-demand regeneration.

    #759 (fault injection): the hourly cooldown is a best-effort rate limit,
    not a correctness guard — the endpoint also carries a slowapi per-minute
    limit. If Redis is unreachable we fail open (return True) so a Redis outage
    degrades gracefully to "no hourly cooldown" instead of 500-ing the manual
    regenerate endpoint.
    """

    from redis.asyncio import Redis
    from redis.exceptions import RedisError

    from app.core.config import settings

    try:
        client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    except RedisError:
        logger.warning(
            "regenerate cooldown check failing open: redis unavailable",
            extra={"user_id": str(user_id)},
        )
        return True
    try:
        key = f"insight:regenerate:{user_id}"
        return bool(await client.set(key, "1", nx=True, ex=INSIGHT_REGENERATE_COOLDOWN_SECONDS))
    except RedisError:
        logger.warning(
            "regenerate cooldown check failing open: redis error",
            extra={"user_id": str(user_id)},
        )
        return True
    finally:
        try:
            await client.aclose()
        except RedisError:
            pass


async def schedule_post_batch_insight_regeneration(*, user_id: uuid.UUID) -> None:
    """Debounced regeneration hook used after successful bulk entry import."""

    from redis.asyncio import Redis
    from redis.exceptions import RedisError

    from app.core.config import settings

    # #759 (fault injection): the debounce key stops overlapping bulk imports
    # from launching a regeneration storm. If Redis is unreachable we cannot
    # debounce safely, so we skip the opportunistic post-batch run rather than
    # risk that storm or crash the import request — the nightly scheduled run
    # (and any manual regenerate) still covers the user.
    try:
        client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    except RedisError:
        logger.warning(
            "post-batch regeneration skipped: redis unavailable",
            extra={"user_id": str(user_id)},
        )
        return
    try:
        debounce_key = f"insight:post_batch:{user_id}"
        acquired = await client.set(
            debounce_key,
            "1",
            nx=True,
            ex=POST_BATCH_DEBOUNCE_SECONDS,
        )
        if not acquired:
            return
    except RedisError:
        logger.warning(
            "post-batch regeneration skipped: redis error",
            extra={"user_id": str(user_id)},
        )
        return
    finally:
        try:
            await client.aclose()
        except RedisError:
            pass

    await run_insight_regeneration_background(
        user_id=user_id,
        trigger_source="post_batch",
    )


async def run_insight_regeneration_background(
    *,
    user_id: uuid.UUID,
    trigger_source: str,
) -> None:
    """Fire-and-forget regeneration used after bulk import."""

    async with AsyncSessionLocal() as session:
        try:
            await regenerate_insights_for_user(
                session,
                user_id=user_id,
                trigger_source=trigger_source,
            )
            await session.commit()
        except AnalyticsDisabledError:
            await session.rollback()
        except InsightLockTimeoutError:
            await session.rollback()
            # Keep the Redis debounce key: launching another post-batch run
            # immediately would collide with the same lock holder again.
            logger.info(
                "background insight regeneration deferred due to lock contention",
                extra={"user_id": str(user_id), "trigger_source": trigger_source},
            )
        except Exception:
            await session.rollback()
            logger.exception(
                "background insight regeneration failed",
                extra={"user_id": str(user_id), "trigger_source": trigger_source},
            )

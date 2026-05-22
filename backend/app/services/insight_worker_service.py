"""Worker-facing orchestration helpers for M3 insight generation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import reset_current_user_dek, set_current_user_dek, unwrap_dek
from app.db.session import bind_rls_current_user
from app.models.user import User
from app.models.user_encryption_key import UserEncryptionKey
from app.models.user_preference import UserPreference
from app.services.insight_engine import generate_and_store_insights


@dataclass(frozen=True)
class InsightGenerationJob:
    """Minimal per-user input needed by the analytics worker."""

    user_id: uuid.UUID
    wrapped_dek: bytes | memoryview


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

    jobs: list[InsightGenerationJob] = []
    for user_id in user_ids:
        await bind_rls_current_user(db, user_id)
        job_result = await db.execute(
            select(UserEncryptionKey.wrapped_dek, UserPreference.analytics_enabled)
            .outerjoin(UserPreference, UserPreference.user_id == UserEncryptionKey.user_id)
            .where(UserEncryptionKey.user_id == user_id)
        )
        row = job_result.first()
        if row is None:
            continue
        wrapped_dek, analytics_enabled = row
        if analytics_enabled is False:
            continue
        jobs.append(InsightGenerationJob(user_id=user_id, wrapped_dek=wrapped_dek))

    return jobs


async def generate_insights_for_job(
    db: AsyncSession,
    *,
    job: InsightGenerationJob,
    as_of: date_type,
) -> int:
    """Generate and store insights for one user with their DEK bound."""

    dek = unwrap_dek(job.wrapped_dek)
    token = set_current_user_dek(job.user_id, dek)
    try:
        await bind_rls_current_user(db, job.user_id)
        insights = await generate_and_store_insights(db, user_id=job.user_id, as_of=as_of)
    finally:
        reset_current_user_dek(token)
    return len(insights)

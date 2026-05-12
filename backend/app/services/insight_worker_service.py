"""Worker-facing orchestration helpers for M3 insight generation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date as date_type

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import reset_current_user_dek, set_current_user_dek, unwrap_dek
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
        select(User.id, UserEncryptionKey.wrapped_dek)
        .join(UserEncryptionKey, UserEncryptionKey.user_id == User.id)
        .outerjoin(UserPreference, UserPreference.user_id == User.id)
        .where(
            User.is_active.is_(True),
            User.is_verified.is_(True),
            or_(UserPreference.user_id.is_(None), UserPreference.analytics_enabled.is_(True)),
        )
        .order_by(User.id.asc())
    )
    return [
        InsightGenerationJob(user_id=user_id, wrapped_dek=wrapped_dek)
        for user_id, wrapped_dek in result.all()
    ]


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
        insights = await generate_and_store_insights(db, user_id=job.user_id, as_of=as_of)
    finally:
        reset_current_user_dek(token)
    return len(insights)

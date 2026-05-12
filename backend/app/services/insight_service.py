"""Read-only service helpers for M3 insights."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Insight

DEFAULT_INSIGHT_LIST_LIMIT = 50
MAX_INSIGHT_LIST_LIMIT = 200
DEFAULT_LATEST_INSIGHT_LIMIT = 10
MAX_LATEST_INSIGHT_LIMIT = 50


def _clamp_limit(limit: int, *, default: int, maximum: int) -> int:
    if limit <= 0:
        return default
    return min(limit, maximum)


async def list_insights(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = DEFAULT_INSIGHT_LIST_LIMIT,
) -> list[Insight]:
    """Return newest insight rows for a user."""

    limit = _clamp_limit(limit, default=DEFAULT_INSIGHT_LIST_LIMIT, maximum=MAX_INSIGHT_LIST_LIMIT)
    result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.generated_at.desc(), Insight.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_latest_insights(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = DEFAULT_LATEST_INSIGHT_LIMIT,
) -> list[Insight]:
    """Return the newest insight per analytical subject.

    A subject is the tuple of insight family, metric and optional target
    (metric/tag/weekday). Keeping this de-duplication in Python avoids
    Postgres-specific ``DISTINCT ON`` so service tests stay simple while the
    DB query remains owner-filtered and newest-first.
    """

    limit = _clamp_limit(
        limit,
        default=DEFAULT_LATEST_INSIGHT_LIMIT,
        maximum=MAX_LATEST_INSIGHT_LIMIT,
    )
    result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.generated_at.desc(), Insight.created_at.desc())
        .limit(MAX_INSIGHT_LIST_LIMIT)
    )

    latest: list[Insight] = []
    seen: set[tuple[object, ...]] = set()
    for insight in result.scalars().all():
        key = (
            insight.insight_type,
            insight.metric,
            insight.subject_type,
            insight.subject_id,
            insight.subject_label,
        )
        if key in seen:
            continue
        seen.add(key)
        latest.append(insight)
        if len(latest) >= limit:
            break
    return latest

"""Dashboard summary helpers for M3 insight confidence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from datetime import date as date_type
from math import log1p

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.insight_engine import confidence_tier_for_sample

_CONFIDENCE_ANCHORS: tuple[tuple[int, float], ...] = (
    (0, 0.05),
    (3, 0.20),
    (8, 0.40),
    (15, 0.65),
    (30, 0.90),
    (100, 1.00),
)


def insight_confidence_score(entry_count: int) -> float:
    """Map sample size to a smooth confidence score with diminishing returns."""

    if entry_count <= 0:
        return _CONFIDENCE_ANCHORS[0][1]
    if entry_count >= _CONFIDENCE_ANCHORS[-1][0]:
        return _CONFIDENCE_ANCHORS[-1][1]

    for (left_n, left_score), (right_n, right_score) in zip(
        _CONFIDENCE_ANCHORS,
        _CONFIDENCE_ANCHORS[1:],
        strict=True,
    ):
        if entry_count <= right_n:
            left_log = log1p(left_n)
            right_log = log1p(right_n)
            position = (log1p(entry_count) - left_log) / (right_log - left_log)
            return round(left_score + (right_score - left_score) * position, 4)

    return _CONFIDENCE_ANCHORS[-1][1]


async def get_dashboard_summary(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type | None = None,
) -> DashboardSummaryResponse:
    as_of = as_of or datetime.now(UTC).date()
    result = await db.execute(
        select(func.count(func.distinct(Entry.entry_date))).where(
            Entry.user_id == user_id,
            Entry.entry_date <= as_of,
        )
    )
    entry_count = int(result.scalar_one() or 0)
    return DashboardSummaryResponse(
        entry_count=entry_count,
        insight_tier=confidence_tier_for_sample(entry_count),
        confidence_score=insight_confidence_score(entry_count),
    )

"""Dashboard summary helpers for M3 insight confidence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from datetime import date as date_type
from math import log1p

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntrySlot
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    WeekdaySummaryItem,
    WorkContextSummaryItem,
)
from app.services.insight_engine import MIN_WEEKDAY_ENTRIES, confidence_tier_for_sample

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
    entry_count_result = await db.execute(
        select(func.count(func.distinct(Entry.entry_date))).where(
            Entry.user_id == user_id,
            Entry.entry_date <= as_of,
        )
    )
    entry_count = int(entry_count_result.scalar_one() or 0)

    work_context_result = await db.execute(
        select(
            Entry.work_context,
            func.count(func.distinct(Entry.entry_date)),
            func.avg(Entry.mood_score),
            func.avg(Entry.energy),
            func.avg(Entry.stress),
        )
        .where(
            Entry.user_id == user_id,
            Entry.entry_date <= as_of,
            Entry.slot == EntrySlot.DAY,
        )
        .group_by(Entry.work_context)
        .order_by(func.count(func.distinct(Entry.entry_date)).desc(), Entry.work_context)
    )
    work_context_summary = [
        WorkContextSummaryItem(
            work_context=row[0],
            entry_count=int(row[1] or 0),
            mood_avg=round(float(row[2]), 2) if row[2] is not None else None,
            energy_avg=round(float(row[3]), 2) if row[3] is not None else None,
            stress_avg=round(float(row[4]), 2) if row[4] is not None else None,
        )
        for row in work_context_result.all()
    ]

    weekday_summary: list[WeekdaySummaryItem] = []
    if entry_count >= MIN_WEEKDAY_ENTRIES:
        daily_subq = (
            select(
                Entry.entry_date,
                func.avg(Entry.mood_score).label("mood_score"),
            )
            .where(
                Entry.user_id == user_id,
                Entry.entry_date <= as_of,
                Entry.slot == EntrySlot.DAY,
            )
            .group_by(Entry.entry_date)
            .subquery()
        )
        weekday_expr = cast(func.extract("isodow", daily_subq.c.entry_date), Integer) - 1
        weekday_result = await db.execute(
            select(
                weekday_expr.label("weekday"),
                func.count(),
                func.avg(daily_subq.c.mood_score),
            )
            .select_from(daily_subq)
            .group_by(weekday_expr)
            .order_by(weekday_expr)
        )
        weekday_rows = weekday_result.all()
        if len(weekday_rows) >= 7:
            weekday_summary = [
                WeekdaySummaryItem(
                    weekday=int(row[0]),
                    entry_count=int(row[1] or 0),
                    mood_avg=round(float(row[2]), 2) if row[2] is not None else None,
                )
                for row in weekday_rows
            ]

    return DashboardSummaryResponse(
        entry_count=entry_count,
        insight_tier=confidence_tier_for_sample(entry_count),
        confidence_score=insight_confidence_score(entry_count),
        work_context_summary=work_context_summary,
        weekday_summary=weekday_summary,
    )

"""M5 habit statistics derived from tags and entry-tag assignments."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.insight import Insight
from app.models.tag import EntryTag, Tag
from app.schemas.habit import HabitListResponse, HabitStatsResponse, HabitWindow
from app.services.tag_service import active_tag_predicate

HABIT_WINDOWS: set[int] = {7, 14, 28, 90}
MIN_DAYS_FOR_ADHERENCE_DISPLAY = 7


class HabitNotFoundError(Exception):
    """Raised when a requested habit tag is not visible to the user."""


def _today() -> date_type:
    return datetime.now(UTC).date()


def _target_days(*, target_frequency: int, days_total: int) -> int:
    return min(days_total, math.ceil(target_frequency * days_total / 7))


def _adherence_rate(
    *,
    habit_type: str,
    days_tracked: int,
    target_days: int,
    days_total: int,
) -> float:
    if target_days <= 0:
        return 0.0
    if habit_type == "build":
        return round(min(100.0, (days_tracked / target_days) * 100), 1)

    if days_tracked <= target_days:
        return 100.0
    possible_overage = max(1, days_total - target_days)
    overage = min(possible_overage, days_tracked - target_days)
    return round(max(0.0, 100.0 * (1 - overage / possible_overage)), 1)


async def _latest_correlation(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> tuple[float | None, str | None]:
    result = await db.execute(
        select(Insight.effect_size, Insight.metric)
        .where(
            Insight.user_id == user_id,
            Insight.subject_type == "tag",
            Insight.subject_id == tag_id,
            Insight.effect_size.is_not(None),
        )
        .order_by(Insight.generated_at.desc())
        .limit(1)
    )
    row = result.one_or_none()
    if row is None:
        return None, None
    return row[0], row[1]


async def _tracked_dates_for_tag(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    start_date: date_type,
    end_date: date_type,
) -> set[date_type]:
    result = await db.execute(
        select(Entry.entry_date)
        .join(EntryTag, EntryTag.entry_id == Entry.id)
        .where(
            Entry.user_id == user_id,
            EntryTag.user_id == user_id,
            EntryTag.tag_id == tag_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= end_date,
        )
        .distinct()
    )
    return {row[0] for row in result.all()}


async def list_habit_tags(db: AsyncSession, *, user_id: uuid.UUID) -> list[Tag]:
    result = await db.execute(
        select(Tag)
        .where(
            active_tag_predicate(user_id),
            Tag.habit_type.in_(("build", "reduce")),
            Tag.target_frequency.is_not(None),
        )
        .order_by(Tag.category.asc(), Tag.slug.asc())
    )
    return list(result.scalars().all())


async def get_habit_stats(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    window: HabitWindow,
    as_of: date_type | None = None,
) -> HabitStatsResponse:
    end_date = as_of or _today()
    start_date = end_date - timedelta(days=window - 1)
    result = await db.execute(
        select(Tag).where(
            Tag.id == tag_id,
            active_tag_predicate(user_id),
            Tag.habit_type.in_(("build", "reduce")),
            Tag.target_frequency.is_not(None),
        )
    )
    tag = result.scalar_one_or_none()
    if tag is None or tag.target_frequency is None:
        raise HabitNotFoundError("habit not found")

    tracked_dates = await _tracked_dates_for_tag(
        db,
        user_id=user_id,
        tag_id=tag.id,
        start_date=start_date,
        end_date=end_date,
    )
    days_total = window
    target_days = _target_days(target_frequency=tag.target_frequency, days_total=days_total)
    days_tracked = len(tracked_dates)
    correlation_score, correlation_metric = await _latest_correlation(
        db, user_id=user_id, tag_id=tag.id
    )

    return HabitStatsResponse(
        tag_id=tag.id,
        habit_type=tag.habit_type,  # type: ignore[arg-type]
        target_frequency=tag.target_frequency,
        window=window,
        start_date=start_date,
        end_date=end_date,
        days_tracked=days_tracked,
        days_total=days_total,
        target_days=target_days,
        adherence_rate=_adherence_rate(
            habit_type=tag.habit_type,
            days_tracked=days_tracked,
            target_days=target_days,
            days_total=days_total,
        ),
        correlation_score=correlation_score,
        correlation_metric=correlation_metric,
    )


async def list_habit_stats(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    window: HabitWindow,
    as_of: date_type | None = None,
) -> HabitListResponse:
    tags = await list_habit_tags(db, user_id=user_id)
    habits = [
        await get_habit_stats(db, user_id=user_id, tag_id=tag.id, window=window, as_of=as_of)
        for tag in tags
    ]
    return HabitListResponse(habits=habits)

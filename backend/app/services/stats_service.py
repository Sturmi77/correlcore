"""M2 statistics for visualization endpoints."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag, TagCategory
from app.schemas.stats import (
    EntryStreakResponse,
    SymptomHeatmapDay,
    SymptomHeatmapResponse,
    SymptomHeatmapSymptom,
    TagHeatmapDay,
    TagHeatmapResponse,
    TagHeatmapTag,
    TimeseriesPoint,
    TimeseriesRange,
    TimeseriesResponse,
)
from app.services.tag_service import active_tag_predicate


def _today() -> date_type:
    return datetime.now(UTC).date()


def _round_avg(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _add_months(d: date_type, months: int) -> date_type:
    total = d.year * 12 + (d.month - 1) + months
    year = total // 12
    month = (total % 12) + 1
    return date(year, month, 1)


@dataclass(frozen=True)
class _Period:
    start: date_type
    end: date_type


def _periods_for_range(range_: TimeseriesRange, as_of: date_type) -> list[_Period]:
    if range_ == "week":
        start = as_of - timedelta(days=6)
        return [_Period(start + timedelta(days=i), start + timedelta(days=i)) for i in range(7)]
    if range_ == "month":
        start = as_of - timedelta(days=29)
        return [_Period(start + timedelta(days=i), start + timedelta(days=i)) for i in range(30)]
    if range_ == "quarter":
        start = as_of - timedelta(days=89)
        return [_Period(start + timedelta(days=i), start + timedelta(days=i)) for i in range(90)]

    first_this_month = date(as_of.year, as_of.month, 1)
    first = _add_months(first_this_month, -11)
    periods: list[_Period] = []
    for i in range(12):
        start = _add_months(first, i)
        next_month = _add_months(start, 1)
        end = min(next_month - timedelta(days=1), as_of)
        periods.append(_Period(start, end))
    return periods


async def get_timeseries(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    range_: TimeseriesRange,
    as_of: date_type | None = None,
) -> TimeseriesResponse:
    as_of = as_of or _today()
    periods = _periods_for_range(range_, as_of)
    start = periods[0].start

    result = await db.execute(
        select(Entry).where(
            Entry.user_id == user_id,
            Entry.entry_date >= start,
            Entry.entry_date <= as_of,
        )
    )
    entries = list(result.scalars().all())

    points: list[TimeseriesPoint] = []
    for period in periods:
        bucket = [e for e in entries if period.start <= e.entry_date <= period.end]
        points.append(
            TimeseriesPoint(
                period_start=period.start,
                period_end=period.end,
                entry_count=len(bucket),
                mood_avg=_round_avg([e.mood_score for e in bucket]),
                energy_avg=_round_avg([e.energy for e in bucket]),
                stress_avg=_round_avg([e.stress for e in bucket]),
            )
        )
    return TimeseriesResponse(range=range_, points=points)


async def get_tag_heatmap(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    start_date: date_type | None = None,
    end_date: date_type | None = None,
    category: TagCategory | None = None,
) -> TagHeatmapResponse:
    end_date = end_date or _today()
    start_date = start_date or (end_date - timedelta(days=364))

    stmt = (
        select(Tag, Entry.entry_date)
        .join(EntryTag, EntryTag.tag_id == Tag.id)
        .join(Entry, Entry.id == EntryTag.entry_id)
        .where(
            EntryTag.user_id == user_id,
            Entry.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= end_date,
            active_tag_predicate(user_id),
        )
        .order_by(Tag.category.asc(), Tag.slug.asc(), Entry.entry_date.asc())
    )
    if category is not None:
        stmt = stmt.where(Tag.category == category)

    result = await db.execute(stmt)
    counts: dict[uuid.UUID, dict[date_type, int]] = defaultdict(lambda: defaultdict(int))
    tag_meta: dict[uuid.UUID, Tag] = {}
    for tag, entry_date in result.all():
        tag_meta[tag.id] = tag
        counts[tag.id][entry_date] += 1

    tags: list[TagHeatmapTag] = []
    for tag_id, tag in sorted(
        tag_meta.items(), key=lambda item: (item[1].category.value, item[1].slug)
    ):
        days = [
            TagHeatmapDay(date=day, count=count)
            for day, count in sorted(counts[tag_id].items(), key=lambda item: item[0])
        ]
        tags.append(
            TagHeatmapTag(
                tag_id=tag.id,
                slug=tag.slug,
                name=tag.name,
                category=tag.category,
                color=tag.color,
                days=days,
            )
        )
    return TagHeatmapResponse(start_date=start_date, end_date=end_date, tags=tags)


async def get_symptom_heatmap(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    start_date: date_type | None = None,
    end_date: date_type | None = None,
) -> SymptomHeatmapResponse:
    """Return neutral daily symptom occurrence/intensity rows for Trends."""

    end_date = end_date or _today()
    start_date = start_date or (end_date - timedelta(days=364))

    stmt = (
        select(Symptom, Entry.entry_date, EntrySymptom.intensity)
        .join(EntrySymptom, EntrySymptom.symptom_id == Symptom.id)
        .join(Entry, Entry.id == EntrySymptom.entry_id)
        .where(
            EntrySymptom.user_id == user_id,
            Entry.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= end_date,
            (Symptom.is_default.is_(True)) | (Symptom.user_id == user_id),
        )
        .order_by(Symptom.slug.asc(), Entry.entry_date.asc())
    )

    result = await db.execute(stmt)
    counts: dict[uuid.UUID, dict[date_type, int]] = defaultdict(lambda: defaultdict(int))
    max_intensity: dict[uuid.UUID, dict[date_type, int]] = defaultdict(lambda: defaultdict(int))
    symptom_meta: dict[uuid.UUID, Symptom] = {}
    for symptom, entry_date, intensity in result.all():
        symptom_meta[symptom.id] = symptom
        counts[symptom.id][entry_date] += 1
        max_intensity[symptom.id][entry_date] = max(
            max_intensity[symptom.id][entry_date], intensity
        )

    symptoms: list[SymptomHeatmapSymptom] = []
    for symptom_id, symptom in sorted(symptom_meta.items(), key=lambda item: item[1].slug):
        days = [
            SymptomHeatmapDay(
                date=day,
                count=count,
                max_intensity=max_intensity[symptom_id][day],
            )
            for day, count in sorted(counts[symptom_id].items(), key=lambda item: item[0])
        ]
        symptoms.append(
            SymptomHeatmapSymptom(
                symptom_id=symptom.id,
                slug=symptom.slug,
                name=symptom.display_name,
                icon=symptom.icon,
                days=days,
            )
        )

    return SymptomHeatmapResponse(start_date=start_date, end_date=end_date, symptoms=symptoms)


async def get_entry_streak(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type | None = None,
) -> EntryStreakResponse:
    as_of = as_of or _today()
    result = await db.execute(
        select(Entry.entry_date)
        .where(Entry.user_id == user_id, Entry.entry_date <= as_of)
        .distinct()
        .order_by(Entry.entry_date.asc())
    )
    dates = [row[0] for row in result.all()]
    date_set = set(dates)

    current = 0
    cursor = as_of
    while cursor in date_set:
        current += 1
        cursor -= timedelta(days=1)

    longest = 0
    run = 0
    previous: date_type | None = None
    for day in dates:
        if previous is not None and day == previous + timedelta(days=1):
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        previous = day

    return EntryStreakResponse(
        current_streak=current,
        longest_streak=longest,
        total_entry_days=len(dates),
        last_entry_date=dates[-1] if dates else None,
        as_of=as_of,
    )

"""M2 statistics for visualization endpoints."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag, TagCategory
from app.models.user_preference import UserPreference
from app.schemas.stats import (
    COOCCURRENCE_RANGE_DAYS,
    EntryStreakResponse,
    SymptomHeatmapDay,
    SymptomHeatmapResponse,
    SymptomHeatmapSymptom,
    SymptomTagCooccurrenceCell,
    SymptomTagCooccurrenceResponse,
    SymptomTagCooccurrenceSymptomRef,
    TagCooccurrencePair,
    TagCooccurrenceRange,
    TagCooccurrenceResponse,
    TagCooccurrenceTagRef,
    TagHeatmapDay,
    TagHeatmapResponse,
    TagHeatmapTag,
    TimeseriesPoint,
    TimeseriesRange,
    TimeseriesResponse,
)
from app.services.symptom_analytics import (
    DailySymptomEntry,
    SymptomRef,
    TagRef,
    heatmap_symptom_tag_associations,
)
from app.services.tag_service import active_tag_predicate


def _today() -> date_type:
    return datetime.now(UTC).date()


def _round_avg(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _dedupe_daily_symptom_entries(entries: list[DailySymptomEntry]) -> list[DailySymptomEntry]:
    grouped: dict[date_type, list[DailySymptomEntry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.entry_date].append(entry)

    daily_entries: list[DailySymptomEntry] = []
    for entry_date, rows in sorted(grouped.items()):
        first = rows[0]
        daily_entries.append(
            DailySymptomEntry(
                entry_date=entry_date,
                mood_score=round(sum(row.mood_score for row in rows) / len(rows)),
                energy=round(sum(row.energy for row in rows) / len(rows)),
                stress=round(sum(row.stress for row in rows) / len(rows)),
                tag_ids=frozenset(tag_id for row in rows for tag_id in row.tag_ids),
                symptom_ids=frozenset(symptom_id for row in rows for symptom_id in row.symptom_ids),
                work_context=first.work_context,
            )
        )
    return daily_entries


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
    start = as_of - timedelta(days=364)
    return [_Period(start + timedelta(days=i), start + timedelta(days=i)) for i in range(365)]


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
            EntrySymptom.intensity > 0,
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


def _cooccurrence_window(
    range_: TagCooccurrenceRange,
    as_of: date_type,
) -> tuple[date_type, date_type]:
    days = COOCCURRENCE_RANGE_DAYS[range_]
    start = as_of - timedelta(days=days - 1)
    return start, as_of


async def _analytics_enabled(db: AsyncSession, *, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(UserPreference.analytics_enabled).where(UserPreference.user_id == user_id)
    )
    return result.scalar_one_or_none() is not False


def cooccurrence_range_to_timeseries(range_: TagCooccurrenceRange) -> TimeseriesRange:
    if range_ == "7d":
        return "week"
    if range_ == "90d":
        return "quarter"
    if range_ == "1y":
        return "year"
    return "month"


async def list_historical_tag_presence_dates_by_slug(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tag_slug: str,
    start_date: date_type,
    end_date: date_type,
) -> list[date_type]:
    """Distinct entry dates for a tag slug, including hidden/inactive tags.

    Used by Explore Events so inactive insight cards can still show historical
    presence windows. Co-occurrence analytics keep using ``active_tag_predicate``.
    """

    from sqlalchemy import func

    slug_key = tag_slug.casefold()
    stmt = (
        select(Entry.entry_date)
        .join(EntryTag, EntryTag.entry_id == Entry.id)
        .join(Tag, Tag.id == EntryTag.tag_id)
        .where(
            EntryTag.user_id == user_id,
            Entry.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= end_date,
            func.lower(Tag.slug) == slug_key,
        )
        .distinct()
        .order_by(Entry.entry_date.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_tag_presence_dates_by_slug(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tag_slug: str,
    start_date: date_type,
    end_date: date_type,
) -> list[date_type]:
    """Distinct entry dates where an active tag with the given slug was present."""

    from sqlalchemy import func

    slug_key = tag_slug.casefold()
    stmt = (
        select(Entry.entry_date)
        .join(EntryTag, EntryTag.entry_id == Entry.id)
        .join(Tag, Tag.id == EntryTag.tag_id)
        .where(
            EntryTag.user_id == user_id,
            Entry.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= end_date,
            func.lower(Tag.slug) == slug_key,
            active_tag_predicate(user_id),
        )
        .distinct()
        .order_by(Entry.entry_date.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_symptom_presence_dates(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    symptom_id: uuid.UUID | None,
    symptom_slug: str | None,
    start_date: date_type,
    end_date: date_type,
) -> list[date_type]:
    """Distinct entry dates where the symptom was present (intensity > 0)."""

    from sqlalchemy import func, or_

    if symptom_id is None and not symptom_slug:
        return []

    filters = [
        EntrySymptom.user_id == user_id,
        EntrySymptom.intensity > 0,
        Entry.user_id == user_id,
        Entry.entry_date >= start_date,
        Entry.entry_date <= end_date,
        (Symptom.is_default.is_(True)) | (Symptom.user_id == user_id),
    ]
    subject_filters = []
    if symptom_id is not None:
        subject_filters.append(Symptom.id == symptom_id)
    if symptom_slug:
        subject_filters.append(func.lower(Symptom.slug) == symptom_slug.casefold())
    filters.append(or_(*subject_filters))

    stmt = (
        select(Entry.entry_date)
        .join(EntrySymptom, EntrySymptom.entry_id == Entry.id)
        .join(Symptom, Symptom.id == EntrySymptom.symptom_id)
        .where(*filters)
        .distinct()
        .order_by(Entry.entry_date.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _tag_ref(tag: Tag) -> TagCooccurrenceTagRef:
    return TagCooccurrenceTagRef(
        tag_id=tag.id,
        slug=tag.slug,
        name=tag.name,
        category=tag.category,
        color=tag.color,
    )


async def get_tag_cooccurrence(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    range_: TagCooccurrenceRange,
    min_count: int = 2,
    as_of: date_type | None = None,
) -> TagCooccurrenceResponse:
    """Count tag pairs that appear together on the same entry within a range."""

    as_of = as_of or _today()
    start_date, end_date = _cooccurrence_window(range_, as_of)

    if not await _analytics_enabled(db, user_id=user_id):
        return TagCooccurrenceResponse(
            range=range_,
            start_date=start_date,
            end_date=end_date,
            min_count=min_count,
            pairs=[],
        )

    result = await db.execute(
        select(Entry.id, Tag)
        .join(EntryTag, EntryTag.entry_id == Entry.id)
        .join(Tag, Tag.id == EntryTag.tag_id)
        .where(
            Entry.user_id == user_id,
            EntryTag.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= end_date,
            active_tag_predicate(user_id),
        )
        .order_by(Entry.id.asc(), Tag.id.asc())
    )

    entry_tags: dict[uuid.UUID, dict[uuid.UUID, Tag]] = defaultdict(dict)
    for entry_id, tag in result.all():
        entry_tags[entry_id][tag.id] = tag

    tag_entry_counts: dict[uuid.UUID, int] = defaultdict(int)
    pair_counts: dict[tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
    tag_meta: dict[uuid.UUID, Tag] = {}

    for tags_by_id in entry_tags.values():
        tags = sorted(tags_by_id.values(), key=lambda item: item.id)
        for tag in tags:
            tag_entry_counts[tag.id] += 1
            tag_meta[tag.id] = tag
        for index, tag_a in enumerate(tags):
            for tag_b in tags[index + 1 :]:
                pair_counts[(tag_a.id, tag_b.id)] += 1

    pairs: list[TagCooccurrencePair] = []
    for (tag_a_id, tag_b_id), count in pair_counts.items():
        if count < min_count:
            continue
        entries_with_a = tag_entry_counts[tag_a_id]
        entries_with_b = tag_entry_counts[tag_b_id]
        pairs.append(
            TagCooccurrencePair(
                tag_a=_tag_ref(tag_meta[tag_a_id]),
                tag_b=_tag_ref(tag_meta[tag_b_id]),
                count=count,
                pct_of_a=round((count / entries_with_a) * 100, 1),
                pct_of_b=round((count / entries_with_b) * 100, 1),
            )
        )

    pairs.sort(key=lambda pair: (-pair.count, pair.tag_a.slug, pair.tag_b.slug))
    return TagCooccurrenceResponse(
        range=range_,
        start_date=start_date,
        end_date=end_date,
        min_count=min_count,
        pairs=pairs,
    )


def _symptom_ref(symptom: Symptom) -> SymptomTagCooccurrenceSymptomRef:
    return SymptomTagCooccurrenceSymptomRef(
        symptom_id=symptom.id,
        slug=symptom.slug,
        name=symptom.display_name,
        icon=symptom.icon,
    )


async def get_symptom_tag_cooccurrence(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    range_: TagCooccurrenceRange,
    min_count: int = 3,
    as_of: date_type | None = None,
) -> SymptomTagCooccurrenceResponse:
    """Return symptom x tag co-occurrence cells for the M7 Insights heatmap."""

    as_of = as_of or _today()
    start_date, end_date = _cooccurrence_window(range_, as_of)

    if not await _analytics_enabled(db, user_id=user_id):
        return SymptomTagCooccurrenceResponse(
            range=range_,
            start_date=start_date,
            end_date=end_date,
            min_count=min_count,
            cells=[],
        )

    entry_result = await db.execute(
        select(Entry).where(
            Entry.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= end_date,
        )
    )
    entries = list(entry_result.scalars().all())
    if not entries:
        return SymptomTagCooccurrenceResponse(
            range=range_,
            start_date=start_date,
            end_date=end_date,
            min_count=min_count,
            cells=[],
        )

    tag_result = await db.execute(
        select(EntryTag.entry_id, Tag)
        .join(Tag, Tag.id == EntryTag.tag_id)
        .join(Entry, Entry.id == EntryTag.entry_id)
        .where(
            EntryTag.user_id == user_id,
            Entry.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= end_date,
            active_tag_predicate(user_id),
        )
        .order_by(Entry.entry_date.asc(), Tag.slug.asc())
    )
    symptom_result = await db.execute(
        select(EntrySymptom.entry_id, Symptom)
        .join(Symptom, Symptom.id == EntrySymptom.symptom_id)
        .join(Entry, Entry.id == EntrySymptom.entry_id)
        .where(
            EntrySymptom.user_id == user_id,
            EntrySymptom.intensity > 0,
            Entry.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= end_date,
            (Symptom.is_default.is_(True)) | (Symptom.user_id == user_id),
        )
        .order_by(Entry.entry_date.asc(), Symptom.slug.asc())
    )

    raw_tag_ids_by_entry: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    tags_by_slug: dict[str, list[Tag]] = defaultdict(list)
    for entry_id, tag in tag_result.all():
        raw_tag_ids_by_entry[entry_id].add(tag.id)
        tags_by_slug[tag.slug].append(tag)

    canonical_tags_by_slug = {
        slug: sorted(tags, key=lambda item: (item.is_default, item.name.casefold(), str(item.id)))[
            0
        ]
        for slug, tags in tags_by_slug.items()
    }
    tag_aliases = {
        tag.id: canonical_tags_by_slug[tag.slug].id
        for tags in tags_by_slug.values()
        for tag in tags
    }
    tags_by_id = {tag.id: tag for tag in canonical_tags_by_slug.values()}
    tag_ids_by_entry = {
        entry_id: {tag_aliases.get(tag_id, tag_id) for tag_id in tag_ids}
        for entry_id, tag_ids in raw_tag_ids_by_entry.items()
    }

    symptom_ids_by_entry: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    symptoms_by_id: dict[uuid.UUID, Symptom] = {}
    for entry_id, symptom in symptom_result.all():
        symptom_ids_by_entry[entry_id].add(symptom.id)
        symptoms_by_id[symptom.id] = symptom

    daily_entries = _dedupe_daily_symptom_entries(
        [
            DailySymptomEntry(
                entry_date=entry.entry_date,
                mood_score=entry.mood_score,
                energy=entry.energy,
                stress=entry.stress,
                tag_ids=frozenset(tag_ids_by_entry.get(entry.id, set())),
                symptom_ids=frozenset(symptom_ids_by_entry.get(entry.id, set())),
                work_context=entry.work_context,
            )
            for entry in sorted(entries, key=lambda item: (item.entry_date, item.slot.value))
        ]
    )
    associations = heatmap_symptom_tag_associations(
        daily_entries,
        {
            symptom_id: SymptomRef(
                id=symptom.id,
                label=symptom.display_name,
                slug=symptom.slug,
            )
            for symptom_id, symptom in symptoms_by_id.items()
        },
        {
            tag_id: TagRef(id=tag.id, label=tag.name, slug=tag.slug)
            for tag_id, tag in tags_by_id.items()
        },
        min_tag_usages=min_count,
    )

    cells = [
        SymptomTagCooccurrenceCell(
            symptom=_symptom_ref(symptoms_by_id[association.symptom.id]),
            tag=_tag_ref(tags_by_id[association.tag.id]),
            phi=association.phi,
            jaccard=association.jaccard,
            lift=association.lift,
            co_count=association.co_count,
            symptom_count=association.symptom_count,
            tag_count=association.tag_count,
            total_count=association.total_count,
            p_value_corrected=association.p_corrected,
            confounder=(
                "work_context"
                if association.work_context_confounded
                else "weekday"
                if association.weekday_confounded
                else "calendar_context"
                if association.calendar_context_confounded
                else None
            ),
        )
        for association in associations
        if association.co_count >= min_count
    ]
    cells.sort(key=lambda cell: (-abs(cell.lift - 1.0), cell.symptom.slug, cell.tag.slug))
    return SymptomTagCooccurrenceResponse(
        range=range_,
        start_date=start_date,
        end_date=end_date,
        min_count=min_count,
        cells=cells,
    )

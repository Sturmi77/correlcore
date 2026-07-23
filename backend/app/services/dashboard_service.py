"""Dashboard summary helpers for M3 insight confidence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from datetime import date as date_type
from math import log1p

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntrySlot
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    WeekdaySummaryItem,
    WeekdayTopSignal,
    WorkContextSummaryItem,
)
from app.services.insight_engine import MIN_WEEKDAY_ENTRIES, confidence_tier_for_sample
from app.services.tag_service import analytics_tag_predicate, canonicalize_tags_by_slug

#: A weekday only gets a top signal once it is more than a one-off.
MIN_TOP_SIGNAL_COUNT = 2
MIN_TOP_SIGNAL_SHARE = 0.3

#: Ties resolve tag > symptom > work_context, then by label (#487).
_KIND_RANK: dict[str, int] = {"tag": 0, "symptom": 1, "work_context": 2}

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


def pick_top_signal(
    candidates: list[tuple[str, uuid.UUID | None, str, int]],
    weekday_entry_count: int,
) -> WeekdayTopSignal | None:
    """Choose the dominant signal for one weekday from ``(kind, id, label, count)``.

    Pure and separately testable. Ties resolve by kind (tag > symptom >
    work_context) then label, so the result is stable across runs.
    """

    if weekday_entry_count <= 0:
        return None

    best: tuple[str, uuid.UUID | None, str, int] | None = None
    for candidate in candidates:
        kind, _id, label, count = candidate
        if count < MIN_TOP_SIGNAL_COUNT:
            continue
        if count / weekday_entry_count < MIN_TOP_SIGNAL_SHARE:
            continue
        if best is None or (-count, _KIND_RANK[kind], label) < (
            -best[3],
            _KIND_RANK[best[0]],
            best[2],
        ):
            best = candidate

    if best is None:
        return None
    kind, signal_id, label, count = best
    return WeekdayTopSignal(
        kind=kind,  # type: ignore[arg-type]
        id=signal_id,
        label=label,
        count=count,
        share=round(count / weekday_entry_count, 3),
    )


async def _weekday_top_signals(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type,
    entries_per_weekday: dict[int, int],
) -> dict[int, WeekdayTopSignal]:
    """Most frequent tag / symptom / work context per weekday.

    Same window and slot filter as ``weekday_summary`` so the new field appears
    exactly when the mood bars do.
    """

    weekday_expr = cast(func.extract("isodow", Entry.entry_date), Integer) - 1
    base_filters = (
        Entry.user_id == user_id,
        Entry.entry_date <= as_of,
        Entry.slot == EntrySlot.DAY,
    )

    # Tags: count per (weekday, tag) but collapse copy-on-write overrides onto
    # the canonical row first — otherwise a renamed tag and its default twin
    # split the count and neither wins (#485).
    tag_rows = (
        await db.execute(
            select(weekday_expr.label("weekday"), Tag)
            .select_from(Entry)
            .join(EntryTag, EntryTag.entry_id == Entry.id)
            .join(Tag, Tag.id == EntryTag.tag_id)
            # Tags the user excluded from analytics must not surface on Home
            # either; the predicate also covers hidden copy-on-write overrides.
            .where(*base_filters, analytics_tag_predicate(user_id))
        )
    ).all()
    aliases, tags_by_id = canonicalize_tags_by_slug(row[1] for row in tag_rows)
    tag_counts: dict[tuple[int, uuid.UUID], int] = {}
    for weekday, tag in tag_rows:
        canonical_id = aliases.get(tag.id, tag.id)
        tag_counts[(int(weekday), canonical_id)] = (
            tag_counts.get((int(weekday), canonical_id), 0) + 1
        )

    # Select the ORM object, not Symptom.name: custom symptoms keep their label
    # encrypted in name_enc with name NULL (model CHECK constraint), so reading
    # the column yields None and the response fails validation. display_name
    # decrypts with the request-bound DEK.
    symptom_rows = (
        await db.execute(
            select(weekday_expr.label("weekday"), Symptom)
            .select_from(Entry)
            .join(EntrySymptom, EntrySymptom.entry_id == Entry.id)
            .join(Symptom, Symptom.id == EntrySymptom.symptom_id)
            # intensity 0 records "not present" — counting it would let an
            # explicitly absent symptom become the day's dominant signal.
            .where(*base_filters, EntrySymptom.intensity > 0)
        )
    ).all()
    symptom_counts: dict[tuple[int, uuid.UUID], int] = {}
    symptoms_by_id: dict[uuid.UUID, Symptom] = {}
    for weekday, symptom in symptom_rows:
        symptoms_by_id[symptom.id] = symptom
        key = (int(weekday), symptom.id)
        symptom_counts[key] = symptom_counts.get(key, 0) + 1

    context_rows = (
        await db.execute(
            select(weekday_expr.label("weekday"), Entry.work_context, func.count())
            .where(*base_filters, Entry.work_context.is_not(None))
            .group_by(weekday_expr, Entry.work_context)
        )
    ).all()

    per_weekday: dict[int, list[tuple[str, uuid.UUID | None, str, int]]] = {}
    for (weekday, canonical_id), count in tag_counts.items():
        tag = tags_by_id.get(canonical_id)
        if tag is None:
            continue
        per_weekday.setdefault(weekday, []).append(("tag", canonical_id, tag.name, count))
    for (weekday, symptom_id), count in symptom_counts.items():
        symptom = symptoms_by_id.get(symptom_id)
        if symptom is None:
            continue
        per_weekday.setdefault(weekday, []).append(
            ("symptom", symptom_id, symptom.display_name, count)
        )
    for weekday, work_context, count in context_rows:
        label = work_context.value if hasattr(work_context, "value") else str(work_context)
        per_weekday.setdefault(int(weekday), []).append(
            ("work_context", None, label, int(count or 0))
        )

    signals: dict[int, WeekdayTopSignal] = {}
    for weekday, candidates in per_weekday.items():
        signal = pick_top_signal(candidates, entries_per_weekday.get(weekday, 0))
        if signal is not None:
            signals[weekday] = signal
    return signals


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

    top_signals: dict[int, WeekdayTopSignal] = {}
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
            entries_per_weekday = {int(row[0]): int(row[1] or 0) for row in weekday_rows}
            top_signals = await _weekday_top_signals(
                db, user_id=user_id, as_of=as_of, entries_per_weekday=entries_per_weekday
            )
            weekday_summary = [
                WeekdaySummaryItem(
                    weekday=int(row[0]),
                    entry_count=int(row[1] or 0),
                    mood_avg=round(float(row[2]), 2) if row[2] is not None else None,
                    top_signal=top_signals.get(int(row[0])),
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

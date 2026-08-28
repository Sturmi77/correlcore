"""Weekday / work-context mood-delta insight families.

Weekday pattern, work-context pattern, and the combined weekday×context cell
pattern. Split out of ``insight_engine`` (#777); behavior is unchanged.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date as date_type

from app.models.entry import WorkContext
from app.models.insight import InsightTier, InsightType
from app.services.insights.shared import (
    _WEEKDAY_LABELS,
    _WORK_CONTEXT_LABELS,
    DEVELOPING_ENTRY_COUNT,
    MIN_CONTEXT_DELTA,
    MIN_CONTEXT_GROUP_SIZE,
    MIN_WEEKDAY_DELTA,
    MIN_WEEKDAY_ENTRIES,
    AnalyticsEntry,
    InsightCandidate,
    _base_flags,
    _confidence,
    _direction,
    _mean,
)


def _weekday_candidates(
    entries: Sequence[AnalyticsEntry],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    if len(entries) < MIN_WEEKDAY_ENTRIES:
        return []

    overall_avg = sum(entry.mood_score for entry in entries) / len(entries)
    by_weekday: dict[int, list[int]] = defaultdict(list)
    for entry in entries:
        by_weekday[entry.entry_date.weekday()].append(entry.mood_score)

    weekday_avgs = {
        weekday: sum(values) / len(values)
        for weekday, values in by_weekday.items()
        if len(values) >= 1
    }
    if not weekday_avgs:
        return []

    weekday, avg = max(weekday_avgs.items(), key=lambda item: abs(item[1] - overall_avg))
    delta = avg - overall_avg
    if abs(delta) < MIN_WEEKDAY_DELTA:
        return []

    direction = _direction(delta, "higher", "lower")
    label = _WEEKDAY_LABELS[weekday]
    statement = f"{label}s currently line up with {direction} mood than your overall average."
    effect_size = round(delta, 4)
    return [
        InsightCandidate(
            insight_type=InsightType.WEEKDAY_PATTERN,
            tier=tier,
            metric="mood_score",
            subject_type="weekday",
            subject_id=None,
            subject_label=label,
            effect_size=effect_size,
            confidence=_confidence(effect_size, None, tier),
            sample_n=len(entries),
            statement=statement,
            flags={
                **_base_flags(p_value=None, method="weekday_delta"),
                "early_pattern": len(entries) < DEVELOPING_ENTRY_COUNT,
            },
            payload={
                "weekday": weekday,
                "weekday_mood_avg": round(avg, 2),
                "weekday_mood_avgs": {
                    str(day): round(sum(values) / len(values), 2)
                    for day, values in sorted(by_weekday.items())
                },
                "weekday_entry_counts": {
                    str(day): len(values) for day, values in sorted(by_weekday.items())
                },
                "overall_mood_avg": round(overall_avg, 2),
                "weekday_entry_count": len(by_weekday[weekday]),
            },
            generated_for_date=generated_for_date,
        )
    ]


def _work_context_candidates(
    entries: Sequence[AnalyticsEntry],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    if len(entries) < MIN_WEEKDAY_ENTRIES:
        return []

    overall_values = [entry.mood_score for entry in entries]
    overall_avg = _mean(overall_values)
    by_context: dict[WorkContext, list[int]] = defaultdict(list)
    for entry in entries:
        by_context[entry.work_context].append(entry.mood_score)

    candidates: list[tuple[WorkContext, float, float, int, int]] = []
    for work_context, values in by_context.items():
        comparison_count = len(entries) - len(values)
        if len(values) < MIN_CONTEXT_GROUP_SIZE or comparison_count < MIN_CONTEXT_GROUP_SIZE:
            continue
        avg = _mean(values)
        delta = avg - overall_avg
        if abs(delta) >= MIN_CONTEXT_DELTA:
            candidates.append((work_context, avg, delta, len(values), comparison_count))

    if not candidates:
        return []

    work_context, avg, delta, context_count, comparison_count = max(
        candidates,
        key=lambda item: abs(item[2]),
    )
    effect_size = round(delta, 4)
    label = _WORK_CONTEXT_LABELS[work_context]
    direction = _direction(delta, "higher", "lower")
    statement = f"{label} days currently line up with {direction} mood than your overall average."
    return [
        InsightCandidate(
            insight_type=InsightType.WORK_CONTEXT_PATTERN,
            tier=tier,
            metric="mood_score",
            subject_type="work_context",
            subject_id=None,
            subject_label=label,
            effect_size=effect_size,
            confidence=_confidence(effect_size, None, tier),
            sample_n=len(entries),
            statement=statement,
            flags={
                **_base_flags(p_value=None, method="work_context_delta"),
                "early_pattern": len(entries) < DEVELOPING_ENTRY_COUNT,
            },
            payload={
                "work_context": work_context.value,
                "work_context_label": label,
                "work_context_mood_avg": round(avg, 2),
                "work_context_mood_avgs": {
                    context.value: round(_mean(values), 2)
                    for context, values in sorted(
                        by_context.items(), key=lambda item: item[0].value
                    )
                },
                "work_context_entry_counts": {
                    context.value: len(values)
                    for context, values in sorted(
                        by_context.items(), key=lambda item: item[0].value
                    )
                },
                "overall_mood_avg": round(overall_avg, 2),
                "context_entry_count": context_count,
                "comparison_entry_count": comparison_count,
            },
            generated_for_date=generated_for_date,
        )
    ]


def _weekday_context_candidates(
    entries: Sequence[AnalyticsEntry],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    if len(entries) < MIN_WEEKDAY_ENTRIES:
        return []
    if len({entry.work_context for entry in entries}) < 2:
        return []

    overall_values = [entry.mood_score for entry in entries]
    overall_avg = _mean(overall_values)
    by_cell: dict[tuple[int, WorkContext], list[int]] = defaultdict(list)
    for entry in entries:
        by_cell[(entry.entry_date.weekday(), entry.work_context)].append(entry.mood_score)

    candidates: list[tuple[int, WorkContext, float, float, int, int]] = []
    for (weekday, work_context), values in by_cell.items():
        comparison_count = len(entries) - len(values)
        if len(values) < MIN_CONTEXT_GROUP_SIZE or comparison_count < MIN_CONTEXT_GROUP_SIZE:
            continue
        avg = _mean(values)
        delta = avg - overall_avg
        if abs(delta) >= MIN_CONTEXT_DELTA:
            candidates.append((weekday, work_context, avg, delta, len(values), comparison_count))

    if not candidates:
        return []

    weekday, work_context, avg, delta, cell_count, comparison_count = max(
        candidates,
        key=lambda item: abs(item[3]),
    )
    effect_size = round(delta, 4)
    weekday_label = _WEEKDAY_LABELS[weekday]
    context_label = _WORK_CONTEXT_LABELS[work_context]
    subject_label = f"{weekday_label}s in {context_label}"
    direction = _direction(delta, "higher", "lower")
    statement = (
        f"{subject_label} currently line up with {direction} mood than your overall average."
    )
    return [
        InsightCandidate(
            insight_type=InsightType.WEEKDAY_CONTEXT_PATTERN,
            tier=tier,
            metric="mood_score",
            subject_type="weekday_context",
            subject_id=None,
            subject_label=subject_label,
            effect_size=effect_size,
            confidence=_confidence(effect_size, None, tier),
            sample_n=len(entries),
            statement=statement,
            flags={
                **_base_flags(p_value=None, method="weekday_context_delta"),
                "early_pattern": len(entries) < DEVELOPING_ENTRY_COUNT,
            },
            payload={
                "weekday": weekday,
                "weekday_label": weekday_label,
                "work_context": work_context.value,
                "work_context_label": context_label,
                "weekday_context_mood_avg": round(avg, 2),
                "overall_mood_avg": round(overall_avg, 2),
                "cell_entry_count": cell_count,
                "comparison_entry_count": comparison_count,
                "weekday_context_entry_counts": {
                    f"{day}:{context.value}": len(values)
                    for (day, context), values in sorted(
                        by_cell.items(),
                        key=lambda item: (item[0][0], item[0][1].value),
                    )
                },
            },
            generated_for_date=generated_for_date,
        )
    ]

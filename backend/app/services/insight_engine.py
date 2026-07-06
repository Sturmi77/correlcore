"""M3 analytics insight engine.

This module computes the first deterministic insight candidates for CorrelCore.
It deliberately stays inside the service layer: no API route, scheduler changes
or UI assumptions are introduced in this sprint.
"""

from __future__ import annotations

import logging
import math
import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from datetime import date as date_type
from typing import Any, Literal

from scipy.stats import chisquare, pointbiserialr, spearmanr
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from statsmodels.stats.multitest import multipletests

from app.core.config import settings
from app.models.entry import Entry, WorkContext
from app.models.insight import Insight, InsightTier, InsightType
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag
from app.services.multivariate_analytics import (
    FeatureMetadata,
    LagFinding,
    LassoFinding,
    MultivariateEntry,
    build_design_matrix,
    run_lag_analysis,
    run_lasso_models,
)
from app.services.symptom_analytics import (
    DailySymptomEntry,
    SymptomMetricAssociation,
    SymptomRef,
    SymptomTagAssociation,
    TagRef,
    compute_symptom_metric_associations,
    compute_symptom_tag_associations,
)
from app.services.tag_service import active_tag_predicate
from app.services.weekday_confounder import (
    is_metric_association_calendar_context_confounded,
    is_metric_association_weekday_confounded,
)

logger = logging.getLogger(__name__)

EARLY_ENTRY_COUNT = 3
PRELIMINARY_ENTRY_COUNT = 8
DEVELOPING_ENTRY_COUNT = 15
ROBUST_ENTRY_COUNT = 30
MIN_WEEKDAY_ENTRIES = 7
MIN_BIVARIATE_ENTRIES = DEVELOPING_ENTRY_COUNT
MIN_TAG_GROUP_SIZE = 2
MIN_ABS_EFFECT_SIZE = 0.25
MIN_WEEKDAY_DELTA = 0.5
MIN_CONTEXT_GROUP_SIZE = 2
MIN_CONTEXT_DELTA = 0.5
FDR_ALPHA = 0.05

MetricName = Literal["mood_score", "energy", "stress"]

_METRIC_LABELS: dict[MetricName, str] = {
    "mood_score": "mood",
    "energy": "energy",
    "stress": "stress",
}
_WEEKDAY_LABELS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_WORK_CONTEXT_LABELS: dict[WorkContext, str] = {
    WorkContext.HOMEOFFICE: "Home office",
    WorkContext.OFFICE: "Office",
    WorkContext.TRAVEL: "Travel",
    WorkContext.VACATION: "Vacation",
    WorkContext.SICK: "Sick leave",
    WorkContext.WEEKEND: "Weekend",
}


@dataclass(frozen=True)
class AnalyticsEntry:
    """Daily row used by the insight engine."""

    id: uuid.UUID
    entry_date: date_type
    mood_score: int
    energy: int
    stress: int
    work_context: WorkContext = WorkContext.HOMEOFFICE
    tag_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)
    symptom_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)


@dataclass(frozen=True)
class TagSnapshot:
    """Tag metadata needed for statement rendering."""

    id: uuid.UUID
    label: str
    slug: str
    is_default: bool = False


@dataclass(frozen=True)
class SymptomSnapshot:
    """Symptom metadata needed for M7 multivariate analytics."""

    id: uuid.UUID
    label: str
    slug: str
    is_default: bool = False


@dataclass(frozen=True)
class InsightCandidate:
    """Computed, persistence-ready insight payload."""

    insight_type: InsightType
    tier: InsightTier
    metric: str
    subject_type: str | None
    subject_id: uuid.UUID | None
    subject_label: str | None
    effect_size: float | None
    confidence: float | None
    sample_n: int
    statement: str
    flags: dict[str, object]
    payload: dict[str, object]
    generated_for_date: date_type


def confidence_tier_for_sample(sample_n: int) -> InsightTier:
    """Map entry count to the M3 tiered confidence ladder."""

    if sample_n >= ROBUST_ENTRY_COUNT:
        return InsightTier.ROBUST
    if sample_n >= DEVELOPING_ENTRY_COUNT:
        return InsightTier.DEVELOPING
    if sample_n >= PRELIMINARY_ENTRY_COUNT:
        return InsightTier.PRELIMINARY
    if sample_n >= EARLY_ENTRY_COUNT:
        return InsightTier.EARLY
    return InsightTier.NONE


def _metric_value(entry: AnalyticsEntry, metric: MetricName) -> int:
    if metric == "mood_score":
        return entry.mood_score
    if metric == "energy":
        return entry.energy
    return entry.stress


def display_metric_value(
    metric: MetricName, raw: int, *, scale_min: int = 1, scale_max: int = 5
) -> int:
    """View-layer inversion for stress (FRONTEND.md §4.3). Raw DB values stay unchanged."""

    if metric == "stress":
        return scale_min + scale_max - raw
    return raw


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _confidence(
    effect_size: float | None, p_value: float | None, tier: InsightTier
) -> float | None:
    if effect_size is None or tier is InsightTier.NONE:
        return None

    tier_weight = {
        InsightTier.EARLY: 0.35,
        InsightTier.PRELIMINARY: 0.55,
        InsightTier.DEVELOPING: 0.75,
        InsightTier.ROBUST: 0.95,
    }.get(tier, 0.0)
    effect_weight = min(1.0, abs(effect_size) / 0.8)
    p_weight = 0.65 if p_value is None else max(0.0, min(1.0, 1.0 - p_value))
    return round(max(0.0, min(1.0, tier_weight * effect_weight * p_weight)), 2)


def _direction(effect_size: float | None, positive: str, negative: str) -> str:
    return positive if effect_size is not None and effect_size >= 0 else negative


def _mean(values: Sequence[int]) -> float:
    return sum(values) / len(values)


def _base_flags(
    *,
    p_value: float | None,
    method: str,
    p_corrected: float | None = None,
) -> dict[str, object]:
    flags: dict[str, object] = {
        "method": method,
        "p_value": _round_or_none(p_value),
        "medical_disclaimer_required": True,
        "causal_claim": False,
    }
    if p_corrected is not None:
        flags["p_corrected"] = _round_or_none(p_corrected)
        flags["multiple_testing_correction"] = "fdr_bh"
    return flags


def _fdr_results(p_values: Sequence[float]) -> list[tuple[bool, float]]:
    """Apply Benjamini-Hochberg FDR correction to one correlation family."""

    if not p_values:
        return []
    reject, p_corrected, _, _ = multipletests(p_values, alpha=FDR_ALPHA, method="fdr_bh")
    return [
        (bool(sig), float(corrected)) for sig, corrected in zip(reject, p_corrected, strict=True)
    ]


def is_weekday_biased(
    entries: Sequence[AnalyticsEntry],
    tag_id: uuid.UUID,
    *,
    threshold_p: float = FDR_ALPHA,
) -> bool:
    """Return True when a tag is concentrated on specific weekdays."""

    observed = [
        sum(1 for entry in entries if tag_id in entry.tag_ids and entry.entry_date.weekday() == day)
        for day in range(7)
    ]
    total = sum(observed)
    if total < settings.ANALYTICS_MIN_TAG_USAGES:
        return False

    expected = [total / 7] * 7
    result = chisquare(observed, f_exp=expected)
    p_value = _finite_float(result.pvalue)
    return p_value is not None and p_value < threshold_p


def is_work_context_biased(
    entries: Sequence[AnalyticsEntry],
    tag_id: uuid.UUID,
    *,
    min_count: int = MIN_TAG_GROUP_SIZE,
    threshold_p: float = FDR_ALPHA,
) -> bool:
    """Return True when a tag is concentrated in specific work contexts."""

    if len(entries) < ROBUST_ENTRY_COUNT:
        return False

    contexts = sorted({entry.work_context for entry in entries}, key=lambda item: item.value)
    if len(contexts) < 2:
        return False

    observed = [
        sum(1 for entry in entries if tag_id in entry.tag_ids and entry.work_context == context)
        for context in contexts
    ]
    total = sum(observed)
    if total < min_count:
        return False

    expected = [total / len(contexts)] * len(contexts)
    result = chisquare(observed, f_exp=expected)
    p_value = _finite_float(result.pvalue)
    return p_value is not None and p_value < threshold_p


def _confounders(
    *,
    weekday_confounded: bool,
    work_context_confounded: bool,
    calendar_context_confounded: bool,
) -> list[str]:
    values: list[str] = []
    if weekday_confounded:
        values.append("weekday")
    if work_context_confounded:
        values.append("work_context")
    if calendar_context_confounded and not values:
        values.append("calendar_context")
    return values


def _primary_confounder(confounders: Sequence[str]) -> str | None:
    return confounders[0] if confounders else None


def _context_confounded_statement(
    statement: str,
    *,
    weekday_confounded: bool,
    work_context_confounded: bool,
    calendar_context_confounded: bool,
) -> str:
    if not calendar_context_confounded:
        return statement
    if work_context_confounded:
        return f"{statement} Note: this pattern occurs primarily in specific work contexts."
    if weekday_confounded:
        return f"{statement} Note: this pattern occurs primarily on specific weekdays."
    return f"{statement} Note: this pattern may be explained by calendar or work-context patterns."


def _weekday_confounded_statement(statement: str, *, weekday_confounded: bool) -> str:
    return _context_confounded_statement(
        statement,
        weekday_confounded=weekday_confounded,
        work_context_confounded=False,
        calendar_context_confounded=weekday_confounded,
    )


def _dedupe_daily_entries(entries: Sequence[AnalyticsEntry]) -> list[AnalyticsEntry]:
    """Collapse multiple slots on a date into one daily vector.

    M1/M2 normally have one entry per day. This keeps the engine additive for
    the existing M3 multi-slot reservation by averaging scores and unioning tags.
    """

    grouped: dict[date_type, list[AnalyticsEntry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.entry_date].append(entry)

    daily: list[AnalyticsEntry] = []
    for day, rows in sorted(grouped.items()):
        first = rows[0]
        daily.append(
            AnalyticsEntry(
                id=first.id,
                entry_date=day,
                mood_score=round(sum(row.mood_score for row in rows) / len(rows)),
                energy=round(sum(row.energy for row in rows) / len(rows)),
                stress=round(sum(row.stress for row in rows) / len(rows)),
                work_context=first.work_context,
                tag_ids=frozenset(tag_id for row in rows for tag_id in row.tag_ids),
                symptom_ids=frozenset(symptom_id for row in rows for symptom_id in row.symptom_ids),
            )
        )
    return daily


def _canonicalize_tag_aliases(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot],
) -> tuple[list[AnalyticsEntry], list[TagSnapshot]]:
    """Collapse default/override tag rows that share the same slug.

    Copy-on-write tag overrides keep the default slug but receive their own
    database ID. Historical entries can therefore reference the curated default
    while newer entries reference the override. Analytics treats both IDs as
    one semantic tag so matrices and insight feeds do not show duplicates such
    as two separate "Alcohol" rows.
    """

    by_slug: dict[str, list[TagSnapshot]] = defaultdict(list)
    for tag in tags:
        by_slug[tag.slug].append(tag)

    canonical_by_slug: dict[str, TagSnapshot] = {}
    aliases: dict[uuid.UUID, uuid.UUID] = {}
    for slug, snapshots in by_slug.items():
        canonical = sorted(
            snapshots,
            key=lambda item: (item.is_default, item.label.casefold(), str(item.id)),
        )[0]
        canonical_by_slug[slug] = canonical
        for snapshot in snapshots:
            aliases[snapshot.id] = canonical.id

    canonical_entries = [
        AnalyticsEntry(
            id=entry.id,
            entry_date=entry.entry_date,
            mood_score=entry.mood_score,
            energy=entry.energy,
            stress=entry.stress,
            work_context=entry.work_context,
            tag_ids=frozenset(aliases.get(tag_id, tag_id) for tag_id in entry.tag_ids),
            symptom_ids=entry.symptom_ids,
        )
        for entry in entries
    ]
    return canonical_entries, sorted(canonical_by_slug.values(), key=lambda tag: tag.slug)


def _spearman_candidates(
    entries: Sequence[AnalyticsEntry],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    if len(entries) < MIN_BIVARIATE_ENTRIES:
        return []

    raw: list[tuple[MetricName, MetricName, str, float, float]] = []
    pairs: tuple[tuple[MetricName, MetricName, str], ...] = (
        ("energy", "mood_score", "energy_mood"),
        ("stress", "mood_score", "stress_mood"),
    )
    for left, right, metric in pairs:
        left_values = [_metric_value(entry, left) for entry in entries]
        right_values = [_metric_value(entry, right) for entry in entries]
        if len(set(left_values)) < 2 or len(set(right_values)) < 2:
            continue
        result = spearmanr(left_values, right_values)
        rho = _finite_float(result.statistic)
        p_value = _finite_float(result.pvalue)
        if rho is None or p_value is None or abs(rho) < MIN_ABS_EFFECT_SIZE:
            continue
        raw.append((left, right, metric, rho, p_value))

    candidates: list[InsightCandidate] = []
    for (left, right, metric, rho, p_value), (significant, p_corrected) in zip(
        raw,
        _fdr_results([item[4] for item in raw]),
        strict=True,
    ):
        if not significant:
            continue
        direction = _direction(rho, "higher", "lower")
        statement = (
            f"In your entries so far, {_METRIC_LABELS[left]} tends to be {direction} "
            f"when {_METRIC_LABELS[right]} is higher. This is a data pattern, not a diagnosis."
        )
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SPEARMAN,
                tier=tier,
                metric=metric,
                subject_type="metric",
                subject_id=None,
                subject_label=right,
                effect_size=round(rho, 4),
                confidence=_confidence(rho, p_corrected, tier),
                sample_n=len(entries),
                statement=statement,
                flags=_base_flags(p_value=p_value, p_corrected=p_corrected, method="spearman"),
                payload={
                    "left_metric": left,
                    "right_metric": right,
                    "rho": round(rho, 4),
                    "p_corrected": round(p_corrected, 4),
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


def _pointbiserial_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: dict[uuid.UUID, TagSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    if len(entries) < MIN_BIVARIATE_ENTRIES:
        return []

    raw: list[
        tuple[
            uuid.UUID,
            TagSnapshot,
            float,
            float,
            int,
            int,
            float,
            float,
            bool,
            bool,
            bool,
        ]
    ] = []
    for tag_id, tag in sorted(tags.items(), key=lambda item: item[1].slug):
        binary = [1 if tag_id in entry.tag_ids else 0 for entry in entries]
        tagged_count = sum(binary)
        untagged_count = len(binary) - tagged_count
        if tagged_count < settings.ANALYTICS_MIN_TAG_USAGES or untagged_count < MIN_TAG_GROUP_SIZE:
            continue

        mood_values = [entry.mood_score for entry in entries]
        result = pointbiserialr(binary, mood_values)
        coefficient = _finite_float(result.statistic)
        p_value = _finite_float(result.pvalue)
        if coefficient is None or p_value is None or abs(coefficient) < MIN_ABS_EFFECT_SIZE:
            continue

        weekday_confounded = is_weekday_biased(entries, tag_id) or (
            is_metric_association_weekday_confounded(
                [entry.entry_date for entry in entries],
                mood_values,
                binary,
                raw_coefficient=coefficient,
                raw_p_value=p_value,
                min_effect=MIN_ABS_EFFECT_SIZE,
                alpha=FDR_ALPHA,
            )
        )
        work_context_confounded = is_work_context_biased(entries, tag_id)
        calendar_context_confounded = (
            weekday_confounded
            or work_context_confounded
            or is_metric_association_calendar_context_confounded(
                [entry.entry_date for entry in entries],
                [entry.work_context.value for entry in entries],
                mood_values,
                binary,
                raw_coefficient=coefficient,
                raw_p_value=p_value,
                min_effect=MIN_ABS_EFFECT_SIZE,
                alpha=FDR_ALPHA,
            )
        )

        tagged_mood = (
            sum(entry.mood_score for entry, present in zip(entries, binary, strict=True) if present)
            / tagged_count
        )
        untagged_mood = (
            sum(
                entry.mood_score
                for entry, present in zip(entries, binary, strict=True)
                if not present
            )
            / untagged_count
        )
        raw.append(
            (
                tag_id,
                tag,
                coefficient,
                p_value,
                tagged_count,
                untagged_count,
                tagged_mood,
                untagged_mood,
                weekday_confounded,
                work_context_confounded,
                calendar_context_confounded,
            )
        )

    candidates: list[InsightCandidate] = []
    for (
        tag_id,
        tag,
        coefficient,
        p_value,
        tagged_count,
        untagged_count,
        tagged_mood,
        untagged_mood,
        weekday_confounded,
        work_context_confounded,
        calendar_context_confounded,
    ), (significant, p_corrected) in zip(
        raw,
        _fdr_results([item[3] for item in raw]),
        strict=True,
    ):
        if not significant:
            continue
        direction = _direction(coefficient, "higher", "lower")
        statement = (
            f"Days tagged {tag.label} currently line up with {direction} mood scores "
            "in your data. Treat this as a pattern to reflect on, not a cause."
        )
        statement = _context_confounded_statement(
            statement,
            weekday_confounded=weekday_confounded,
            work_context_confounded=work_context_confounded,
            calendar_context_confounded=calendar_context_confounded,
        )
        confounders = _confounders(
            weekday_confounded=weekday_confounded,
            work_context_confounded=work_context_confounded,
            calendar_context_confounded=calendar_context_confounded,
        )
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.POINTBISERIAL,
                tier=tier,
                metric="mood_score",
                subject_type="tag",
                subject_id=tag_id,
                subject_label=tag.label,
                effect_size=round(coefficient, 4),
                confidence=_confidence(coefficient, p_corrected, tier),
                sample_n=len(entries),
                statement=statement,
                flags={
                    **_base_flags(
                        p_value=p_value,
                        p_corrected=p_corrected,
                        method="pointbiserial",
                    ),
                    "weekday_confounded": weekday_confounded,
                    "work_context_confounded": work_context_confounded,
                    "calendar_context_confounded": calendar_context_confounded,
                    "min_tag_usages": settings.ANALYTICS_MIN_TAG_USAGES,
                },
                payload={
                    "tag_slug": tag.slug,
                    "tagged_count": tagged_count,
                    "untagged_count": untagged_count,
                    "tagged_mood_avg": round(tagged_mood, 2),
                    "untagged_mood_avg": round(untagged_mood, 2),
                    "p_corrected": round(p_corrected, 4),
                    "confounder": _primary_confounder(confounders),
                    "confounders": confounders,
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


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
    statement = (
        f"{label}s currently line up with {direction} mood than your overall average. "
        "This is an early calendar pattern, not a diagnosis."
    )
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
    statement = (
        f"{label} days currently line up with {direction} mood than your overall average. "
        "This is an early context pattern, not a diagnosis."
    )
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
                    for context, values in sorted(by_context.items(), key=lambda item: item[0].value)
                },
                "work_context_entry_counts": {
                    context.value: len(values)
                    for context, values in sorted(by_context.items(), key=lambda item: item[0].value)
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
        f"{subject_label} currently line up with {direction} mood than your overall average. "
        "This is an early calendar/context pattern, not a diagnosis."
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


def _multivariate_entries(entries: Sequence[AnalyticsEntry]) -> list[MultivariateEntry]:
    return [
        MultivariateEntry(
            entry_date=entry.entry_date,
            mood_score=entry.mood_score,
            energy=entry.energy,
            stress=entry.stress,
            tag_ids=entry.tag_ids,
            symptom_ids=entry.symptom_ids,
        )
        for entry in entries
    ]


def _feature_meta_for_tags(tags: Iterable[TagSnapshot]) -> dict[uuid.UUID, FeatureMetadata]:
    return {
        tag.id: FeatureMetadata(
            kind="tag",
            key=f"tag:{tag.slug}",
            label=tag.label,
            slug=tag.slug,
            id=tag.id,
        )
        for tag in tags
    }


def _feature_meta_for_symptoms(
    symptoms: Iterable[SymptomSnapshot],
) -> dict[uuid.UUID, FeatureMetadata]:
    return {
        symptom.id: FeatureMetadata(
            kind="symptom",
            key=f"symptom:{symptom.slug}",
            label=symptom.label,
            slug=symptom.slug,
            id=symptom.id,
        )
        for symptom in symptoms
    }


def _payload_feature(
    feature: FeatureMetadata, *, coefficient: float | None = None
) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": feature.kind,
        "key": feature.key,
        "name": feature.label,
    }
    if feature.slug is not None:
        payload["slug"] = feature.slug
    if feature.id is not None:
        payload["id"] = str(feature.id)
    if coefficient is not None:
        payload["coefficient"] = coefficient
    return payload


def _lasso_statement(finding: LassoFinding) -> str:
    labels = ", ".join(feature.feature.label for feature in finding.features[:3])
    return (
        f"Across your tracked signals, {finding.target} currently varies most with {labels}. "
        "This is a multivariate pattern, not a cause."
    )


def _lag_statement(finding: LagFinding) -> str:
    direction = _direction(finding.correlation, "higher", "lower")
    return (
        f"{finding.feature.label} logged {finding.lag_days} day(s) earlier currently lines up "
        f"with {direction} {finding.target.label}. Treat this as a time-shifted pattern, not a cause."
    )


def _lasso_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot],
    symptoms: Iterable[SymptomSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    frame, feature_meta = build_design_matrix(
        _multivariate_entries(entries),
        tags=_feature_meta_for_tags(tags),
        symptoms=_feature_meta_for_symptoms(symptoms),
    )
    findings = run_lasso_models(frame, feature_meta)
    candidates: list[InsightCandidate] = []
    for finding in findings:
        max_coefficient = max(abs(feature.coefficient) for feature in finding.features)
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SYMPTOM_CLUSTER,
                tier=tier,
                metric=finding.target,
                subject_type="metric",
                subject_id=None,
                subject_label=finding.target,
                effect_size=round(max_coefficient, 4),
                confidence=_confidence(max_coefficient, None, tier),
                sample_n=finding.sample_n,
                statement=_lasso_statement(finding),
                flags=_base_flags(p_value=None, method="lasso"),
                payload={
                    "method": "lasso",
                    "target": finding.target,
                    "features": [
                        _payload_feature(feature.feature, coefficient=feature.coefficient)
                        for feature in finding.features
                    ],
                    "cv": "TimeSeriesSplit",
                    "cv_splits": 5,
                    "cv_score": finding.cv_score,
                    "alpha": finding.alpha,
                    "sample_n": finding.sample_n,
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


def _lag_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot],
    symptoms: Iterable[SymptomSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    frame, feature_meta = build_design_matrix(
        _multivariate_entries(entries),
        tags=_feature_meta_for_tags(tags),
        symptoms=_feature_meta_for_symptoms(symptoms),
    )
    findings = run_lag_analysis(frame, feature_meta)
    candidates: list[InsightCandidate] = []
    for finding in findings:
        target_id = finding.target.id if finding.target.kind == "symptom" else None
        metric = finding.target.key if finding.target.kind == "metric" else "symptom_presence"
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SYMPTOM_CLUSTER,
                tier=tier,
                metric=metric,
                subject_type=finding.target.kind,
                subject_id=target_id,
                subject_label=finding.target.label,
                effect_size=finding.correlation,
                confidence=_confidence(finding.correlation, finding.p_corrected, tier),
                sample_n=finding.sample_n,
                statement=_lag_statement(finding),
                flags={
                    **_base_flags(
                        p_value=finding.p_value,
                        p_corrected=finding.p_corrected,
                        method="lag",
                    ),
                    "lag_days": finding.lag_days,
                },
                payload={
                    "method": "lag",
                    "target": _payload_feature(finding.target),
                    "feature": _payload_feature(finding.feature),
                    "lag_days": finding.lag_days,
                    "correlation": finding.correlation,
                    "p_value_corrected": finding.p_corrected,
                    "sample_n": finding.sample_n,
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


def _symptom_entries(entries: Sequence[AnalyticsEntry]) -> list[DailySymptomEntry]:
    return [
        DailySymptomEntry(
            entry_date=entry.entry_date,
            mood_score=entry.mood_score,
            energy=entry.energy,
            stress=entry.stress,
            tag_ids=entry.tag_ids,
            symptom_ids=entry.symptom_ids,
            work_context=entry.work_context,
        )
        for entry in entries
    ]


def _symptom_refs(symptoms: Iterable[SymptomSnapshot]) -> dict[uuid.UUID, SymptomRef]:
    return {
        symptom.id: SymptomRef(id=symptom.id, label=symptom.label, slug=symptom.slug)
        for symptom in symptoms
    }


def _tag_refs(tags: Iterable[TagSnapshot]) -> dict[uuid.UUID, TagRef]:
    return {tag.id: TagRef(id=tag.id, label=tag.label, slug=tag.slug) for tag in tags}


def _symptom_metric_statement(finding: SymptomMetricAssociation) -> str:
    direction = _direction(finding.coefficient, "higher", "lower")
    statement = (
        f"Days with {finding.symptom.label} currently line up with {direction} "
        f"{_METRIC_LABELS[finding.metric]} in your data. "
        "Treat this as an association, not a cause."
    )
    return _context_confounded_statement(
        statement,
        weekday_confounded=finding.weekday_confounded,
        work_context_confounded=finding.work_context_confounded,
        calendar_context_confounded=finding.calendar_context_confounded,
    )


def _symptom_tag_statement(finding: SymptomTagAssociation) -> str:
    if finding.lift >= 1:
        relationship = "appears together with"
    else:
        relationship = "appears less often with"
    statement = (
        f"{finding.symptom.label} currently {relationship} {finding.tag.label} "
        "more than expected from their individual frequencies. "
        "This is a co-occurrence pattern, not a cause."
    )
    return _context_confounded_statement(
        statement,
        weekday_confounded=finding.weekday_confounded,
        work_context_confounded=finding.work_context_confounded,
        calendar_context_confounded=finding.calendar_context_confounded,
    )


def _symptom_metric_candidates(
    entries: Sequence[AnalyticsEntry],
    symptoms: Iterable[SymptomSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    findings = compute_symptom_metric_associations(
        _symptom_entries(entries),
        _symptom_refs(symptoms),
    )
    candidates: list[InsightCandidate] = []
    for finding in findings:
        confounders = _confounders(
            weekday_confounded=finding.weekday_confounded,
            work_context_confounded=finding.work_context_confounded,
            calendar_context_confounded=finding.calendar_context_confounded,
        )
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SYMPTOM_MOOD_ASSOCIATION,
                tier=tier,
                metric=finding.metric,
                subject_type="symptom",
                subject_id=finding.symptom.id,
                subject_label=finding.symptom.label,
                effect_size=finding.coefficient,
                confidence=_confidence(finding.coefficient, finding.p_corrected, tier),
                sample_n=finding.sample_n,
                statement=_symptom_metric_statement(finding),
                flags={
                    **_base_flags(
                        p_value=finding.p_value,
                        p_corrected=finding.p_corrected,
                        method="pointbiserial",
                    ),
                    "weekday_confounded": finding.weekday_confounded,
                    "work_context_confounded": finding.work_context_confounded,
                    "calendar_context_confounded": finding.calendar_context_confounded,
                    "min_symptom_usages": 5,
                },
                payload={
                    "kind": "symptom_mood_association",
                    "symptom_id": str(finding.symptom.id),
                    "symptom_slug": finding.symptom.slug,
                    "symptom_name": finding.symptom.label,
                    "metric": finding.metric,
                    "method": "pointbiserial",
                    "effect_size": finding.coefficient,
                    "p_value_corrected": finding.p_corrected,
                    "sample_n": finding.sample_n,
                    "symptom_n": finding.symptom_count,
                    "comparison_n": finding.comparison_count,
                    "symptom_metric_avg": finding.symptom_metric_avg,
                    "comparison_metric_avg": finding.comparison_metric_avg,
                    "confounder": _primary_confounder(confounders),
                    "confounders": confounders,
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


def _symptom_tag_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot],
    symptoms: Iterable[SymptomSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    findings = compute_symptom_tag_associations(
        _symptom_entries(entries),
        _symptom_refs(symptoms),
        _tag_refs(tags),
    )
    candidates: list[InsightCandidate] = []
    for finding in findings:
        effect_size = finding.phi if finding.phi != 0 else finding.lift - 1.0
        confounders = _confounders(
            weekday_confounded=finding.weekday_confounded,
            work_context_confounded=finding.work_context_confounded,
            calendar_context_confounded=finding.calendar_context_confounded,
        )
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SYMPTOM_TAG_COOCCURRENCE,
                tier=tier,
                metric="symptom_tag_cooccurrence",
                subject_type="symptom_tag",
                subject_id=None,
                subject_label=f"{finding.symptom.label} + {finding.tag.label}",
                effect_size=round(effect_size, 4),
                confidence=_confidence(effect_size, finding.p_corrected, tier),
                sample_n=finding.total_count,
                statement=_symptom_tag_statement(finding),
                flags={
                    **_base_flags(
                        p_value=finding.p_value,
                        p_corrected=finding.p_corrected,
                        method="fisher_exact_lift",
                    ),
                    "weekday_confounded": finding.weekday_confounded,
                    "work_context_confounded": finding.work_context_confounded,
                    "calendar_context_confounded": finding.calendar_context_confounded,
                    "min_symptom_usages": 5,
                    "min_tag_usages": 5,
                },
                payload={
                    "kind": "symptom_tag_cooccurrence",
                    "symptom_id": str(finding.symptom.id),
                    "symptom_slug": finding.symptom.slug,
                    "symptom_name": finding.symptom.label,
                    "tag_id": str(finding.tag.id),
                    "tag_slug": finding.tag.slug,
                    "tag_name": finding.tag.label,
                    "phi": finding.phi,
                    "jaccard": finding.jaccard,
                    "lift": finding.lift,
                    "co_count": finding.co_count,
                    "symptom_count": finding.symptom_count,
                    "tag_count": finding.tag_count,
                    "total_count": finding.total_count,
                    "p_value_corrected": finding.p_corrected,
                    "confounder": _primary_confounder(confounders),
                    "confounders": confounders,
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


def generate_insight_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot] = (),
    symptoms: Iterable[SymptomSnapshot] = (),
    *,
    as_of: date_type | None = None,
) -> list[InsightCandidate]:
    """Generate deterministic insight candidates from user-owned data."""

    daily_entries = _dedupe_daily_entries(entries)
    if not daily_entries:
        return []

    generated_for_date = as_of or daily_entries[-1].entry_date
    tier = confidence_tier_for_sample(len(daily_entries))
    if tier is InsightTier.NONE:
        return []

    daily_entries, canonical_tags = _canonicalize_tag_aliases(daily_entries, tags)
    tags_by_id = {tag.id: tag for tag in canonical_tags}
    symptom_list = sorted(symptoms, key=lambda symptom: symptom.slug)
    candidates = [
        *_weekday_candidates(daily_entries, tier=tier, generated_for_date=generated_for_date),
        *_work_context_candidates(daily_entries, tier=tier, generated_for_date=generated_for_date),
        *_weekday_context_candidates(
            daily_entries,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_spearman_candidates(daily_entries, tier=tier, generated_for_date=generated_for_date),
        *_pointbiserial_candidates(
            daily_entries,
            tags_by_id,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_symptom_metric_candidates(
            daily_entries,
            symptom_list,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_symptom_tag_candidates(
            daily_entries,
            canonical_tags,
            symptom_list,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_lasso_candidates(
            daily_entries,
            canonical_tags,
            symptom_list,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_lag_candidates(
            daily_entries,
            canonical_tags,
            symptom_list,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
    ]
    return sorted(
        candidates,
        key=lambda candidate: (
            -(candidate.confidence or 0),
            -abs(candidate.effect_size or 0),
            candidate.insight_type.value,
            candidate.metric,
            candidate.subject_label or "",
        ),
    )


async def _load_analytics_inputs(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type,
) -> tuple[list[AnalyticsEntry], list[TagSnapshot], list[SymptomSnapshot]]:
    result = await db.execute(
        select(Entry)
        # Temporal integrity guard: analytics must follow entry_date only.
        # created_at/updated_at would leak look-ahead bias for backdated entries.
        .where(Entry.user_id == user_id, Entry.entry_date < as_of)
        .order_by(Entry.entry_date.asc(), Entry.slot.asc())
    )
    entries = list(result.scalars().all())
    if not entries:
        return [], [], []

    tag_rows = await db.execute(
        select(EntryTag.entry_id, Tag)
        .join(Tag, Tag.id == EntryTag.tag_id)
        .join(Entry, Entry.id == EntryTag.entry_id)
        .where(
            EntryTag.user_id == user_id,
            Entry.user_id == user_id,
            Entry.entry_date < as_of,
            active_tag_predicate(user_id),
        )
    )
    tag_ids_by_entry: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    tags_by_id: dict[uuid.UUID, TagSnapshot] = {}
    for entry_id, tag in tag_rows.all():
        tag_ids_by_entry[entry_id].add(tag.id)
        tags_by_id[tag.id] = TagSnapshot(
            id=tag.id,
            label=tag.name,
            slug=tag.slug,
            is_default=tag.is_default,
        )

    symptom_rows = await db.execute(
        select(EntrySymptom.entry_id, Symptom)
        .join(Symptom, Symptom.id == EntrySymptom.symptom_id)
        .join(Entry, Entry.id == EntrySymptom.entry_id)
        .where(
            EntrySymptom.user_id == user_id,
            EntrySymptom.intensity > 0,
            Entry.user_id == user_id,
            Entry.entry_date < as_of,
            or_(Symptom.is_default.is_(True), Symptom.user_id == user_id),
        )
    )
    symptom_ids_by_entry: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    symptoms_by_id: dict[uuid.UUID, SymptomSnapshot] = {}
    for entry_id, symptom in symptom_rows.all():
        symptom_ids_by_entry[entry_id].add(symptom.id)
        symptoms_by_id[symptom.id] = SymptomSnapshot(
            id=symptom.id,
            label=symptom.display_name,
            slug=symptom.slug,
            is_default=symptom.is_default,
        )

    analytics_entries = [
        AnalyticsEntry(
            id=entry.id,
            entry_date=entry.entry_date,
            mood_score=entry.mood_score,
            energy=entry.energy,
            stress=entry.stress,
            work_context=entry.work_context,
            tag_ids=frozenset(tag_ids_by_entry.get(entry.id, set())),
            symptom_ids=frozenset(symptom_ids_by_entry.get(entry.id, set())),
        )
        for entry in entries
    ]
    canonical_entries, canonical_tags = _canonicalize_tag_aliases(
        analytics_entries,
        tags_by_id.values(),
    )
    return (
        canonical_entries,
        canonical_tags,
        sorted(symptoms_by_id.values(), key=lambda item: item.slug),
    )


async def load_analytics_data(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type,
) -> tuple[list[AnalyticsEntry], list[TagSnapshot], list[SymptomSnapshot]]:
    """Load sanitized analytics rows for tests and diagnostics.

    The public wrapper preserves the M3 service contract while keeping the
    query implementation private to this module.
    """

    return await _load_analytics_inputs(db, user_id=user_id, as_of=as_of)


async def generate_and_store_insights(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type | None = None,
) -> list[Insight]:
    """Regenerate and store M3 insight rows for a user/date.

    The function is idempotent for ``(user_id, generated_for_date)`` by deleting
    existing rows for that date before inserting the new candidates. The caller
    must bind the user's DEK before flushing because ``Insight.statement_enc``
    uses :class:`app.core.crypto.EncryptedString`.
    """

    generated_for_date = as_of or datetime.now(UTC).date()
    entries, tags, symptoms = await _load_analytics_inputs(
        db,
        user_id=user_id,
        as_of=generated_for_date,
    )
    candidates = generate_insight_candidates(entries, tags, symptoms, as_of=generated_for_date)

    await db.execute(
        delete(Insight).where(
            Insight.user_id == user_id,
            Insight.generated_for_date == generated_for_date,
        )
    )

    insights = [
        Insight(
            user_id=user_id,
            insight_type=candidate.insight_type,
            tier=candidate.tier,
            metric=candidate.metric,
            subject_type=candidate.subject_type,
            subject_id=candidate.subject_id,
            subject_label=candidate.subject_label,
            effect_size=candidate.effect_size,
            confidence=candidate.confidence,
            sample_n=candidate.sample_n,
            statement_enc=candidate.statement,
            flags=candidate.flags,
            payload=candidate.payload,
            generated_for_date=candidate.generated_for_date,
        )
        for candidate in candidates
    ]
    for insight in insights:
        db.add(insight)
    await db.flush()
    logger.info(
        "insights.generated",
        extra={"user_id": str(user_id), "insight_count": len(insights)},
    )
    return insights

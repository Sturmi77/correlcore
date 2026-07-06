"""M7 symptom analytics helpers for univariate and co-occurrence insights."""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date as date_type
from typing import Any, Literal

from scipy.stats import chisquare, fisher_exact, pointbiserialr
from statsmodels.stats.multitest import multipletests

from app.models.entry import WorkContext
from app.services.weekday_confounder import (
    is_metric_association_calendar_context_confounded,
    is_metric_association_weekday_confounded,
    is_pair_cooccurrence_calendar_context_confounded,
    is_pair_cooccurrence_weekday_confounded,
)

MetricName = Literal["mood_score", "energy", "stress"]

MIN_SYMPTOM_ANALYTICS_ENTRIES = 15
MIN_SYMPTOM_USAGES = 5
MIN_TAG_USAGES_FOR_SYMPTOM_COOCCURRENCE = 5
MIN_ABS_SYMPTOM_EFFECT_SIZE = 0.25
SYMPTOM_FDR_ALPHA = 0.10
MIN_CARD_LIFT_DELTA = 0.67
MIN_HEATMAP_LIFT_DELTA = 0.50

METRIC_TARGETS: tuple[MetricName, ...] = ("mood_score", "energy", "stress")


@dataclass(frozen=True)
class DailySymptomEntry:
    """Daily binary signal row consumed by symptom analytics."""

    entry_date: date_type
    mood_score: int
    energy: int
    stress: int
    tag_ids: frozenset[uuid.UUID]
    symptom_ids: frozenset[uuid.UUID]
    work_context: WorkContext = WorkContext.HOMEOFFICE


@dataclass(frozen=True)
class SymptomRef:
    id: uuid.UUID
    label: str
    slug: str


@dataclass(frozen=True)
class TagRef:
    id: uuid.UUID
    label: str
    slug: str


@dataclass(frozen=True)
class SymptomMetricAssociation:
    symptom: SymptomRef
    metric: MetricName
    coefficient: float
    p_value: float
    p_corrected: float
    symptom_count: int
    comparison_count: int
    symptom_metric_avg: float
    comparison_metric_avg: float
    weekday_confounded: bool
    work_context_confounded: bool
    calendar_context_confounded: bool
    sample_n: int


@dataclass(frozen=True)
class SymptomTagAssociation:
    symptom: SymptomRef
    tag: TagRef
    phi: float
    jaccard: float
    lift: float
    p_value: float
    p_corrected: float
    co_count: int
    symptom_count: int
    tag_count: int
    total_count: int
    weekday_confounded: bool
    work_context_confounded: bool
    calendar_context_confounded: bool


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _metric_value(entry: DailySymptomEntry, metric: MetricName) -> int:
    if metric == "mood_score":
        return entry.mood_score
    if metric == "energy":
        return entry.energy
    return entry.stress


def _fdr_correct(p_values: Sequence[float]) -> list[tuple[bool, float]]:
    if not p_values:
        return []
    reject, p_corrected, _, _ = multipletests(
        p_values,
        alpha=SYMPTOM_FDR_ALPHA,
        method="fdr_bh",
    )
    return [
        (bool(significant), float(corrected))
        for significant, corrected in zip(reject, p_corrected, strict=True)
    ]


def is_weekday_biased_signal(
    entries: Sequence[DailySymptomEntry],
    signal_id: uuid.UUID,
    *,
    kind: Literal["tag", "symptom"],
    min_count: int = MIN_SYMPTOM_USAGES,
    threshold_p: float = SYMPTOM_FDR_ALPHA,
) -> bool:
    """Return True when a tag or symptom is concentrated on specific weekdays."""

    def present(entry: DailySymptomEntry) -> bool:
        return signal_id in (entry.tag_ids if kind == "tag" else entry.symptom_ids)

    observed = [
        sum(1 for entry in entries if present(entry) and entry.entry_date.weekday() == day)
        for day in range(7)
    ]
    total = sum(observed)
    if total < min_count:
        return False

    expected = [total / 7] * 7
    result = chisquare(observed, f_exp=expected)
    p_value = _finite_float(result.pvalue)
    return p_value is not None and p_value < threshold_p


def is_work_context_biased_signal(
    entries: Sequence[DailySymptomEntry],
    signal_id: uuid.UUID,
    *,
    kind: Literal["tag", "symptom"],
    min_count: int = MIN_SYMPTOM_USAGES,
    threshold_p: float = SYMPTOM_FDR_ALPHA,
) -> bool:
    """Return True when a tag or symptom is concentrated in specific work contexts."""

    if len(entries) < 30:
        return False

    def present(entry: DailySymptomEntry) -> bool:
        return signal_id in (entry.tag_ids if kind == "tag" else entry.symptom_ids)

    contexts = sorted({entry.work_context for entry in entries}, key=lambda item: item.value)
    if len(contexts) < 2:
        return False

    observed = [
        sum(1 for entry in entries if present(entry) and entry.work_context == context)
        for context in contexts
    ]
    total = sum(observed)
    if total < min_count:
        return False

    expected = [total / len(contexts)] * len(contexts)
    result = chisquare(observed, f_exp=expected)
    p_value = _finite_float(result.pvalue)
    return p_value is not None and p_value < threshold_p


def compute_symptom_metric_associations(
    entries: Sequence[DailySymptomEntry],
    symptoms: Mapping[uuid.UUID, SymptomRef],
    *,
    min_entries: int = MIN_SYMPTOM_ANALYTICS_ENTRIES,
    min_symptom_usages: int = MIN_SYMPTOM_USAGES,
    min_abs_effect_size: float = MIN_ABS_SYMPTOM_EFFECT_SIZE,
) -> list[SymptomMetricAssociation]:
    """Compute pointbiserial symptom associations per metric with BH-FDR."""

    if len(entries) < min_entries:
        return []

    associations: list[SymptomMetricAssociation] = []
    for metric in METRIC_TARGETS:
        raw: list[tuple[SymptomRef, float, float, int, int, float, float, bool, bool, bool]] = []
        metric_values = [_metric_value(entry, metric) for entry in entries]
        if len(set(metric_values)) < 2:
            continue

        for symptom_id, symptom in sorted(symptoms.items(), key=lambda item: item[1].slug):
            binary = [1 if symptom_id in entry.symptom_ids else 0 for entry in entries]
            symptom_count = sum(binary)
            comparison_count = len(binary) - symptom_count
            if symptom_count < min_symptom_usages or comparison_count < min_symptom_usages:
                continue

            result = pointbiserialr(binary, metric_values)
            coefficient = _finite_float(result.statistic)
            p_value = _finite_float(result.pvalue)
            if coefficient is None or p_value is None or abs(coefficient) < min_abs_effect_size:
                continue

            symptom_avg = (
                sum(value for value, present in zip(metric_values, binary, strict=True) if present)
                / symptom_count
            )
            comparison_avg = (
                sum(
                    value
                    for value, present in zip(metric_values, binary, strict=True)
                    if not present
                )
                / comparison_count
            )
            weekday_confounded = is_weekday_biased_signal(
                entries, symptom_id, kind="symptom"
            ) or is_metric_association_weekday_confounded(
                [entry.entry_date for entry in entries],
                metric_values,
                binary,
                raw_coefficient=coefficient,
                raw_p_value=p_value,
                min_effect=min_abs_effect_size,
                alpha=SYMPTOM_FDR_ALPHA,
            )
            work_context_confounded = is_work_context_biased_signal(
                entries,
                symptom_id,
                kind="symptom",
            )
            calendar_context_confounded = (
                weekday_confounded
                or work_context_confounded
                or is_metric_association_calendar_context_confounded(
                    [entry.entry_date for entry in entries],
                    [entry.work_context.value for entry in entries],
                    metric_values,
                    binary,
                    raw_coefficient=coefficient,
                    raw_p_value=p_value,
                    min_effect=min_abs_effect_size,
                    alpha=SYMPTOM_FDR_ALPHA,
                )
            )
            raw.append(
                (
                    symptom,
                    coefficient,
                    p_value,
                    symptom_count,
                    comparison_count,
                    symptom_avg,
                    comparison_avg,
                    weekday_confounded,
                    work_context_confounded,
                    calendar_context_confounded,
                )
            )

        for (
            symptom,
            coefficient,
            p_value,
            symptom_count,
            comparison_count,
            symptom_avg,
            comparison_avg,
            weekday_confounded,
            work_context_confounded,
            calendar_context_confounded,
        ), (significant, p_corrected) in zip(
            raw,
            _fdr_correct([item[2] for item in raw]),
            strict=True,
        ):
            if not significant:
                continue
            associations.append(
                SymptomMetricAssociation(
                    symptom=symptom,
                    metric=metric,
                    coefficient=round(coefficient, 4),
                    p_value=round(p_value, 6),
                    p_corrected=round(p_corrected, 6),
                    symptom_count=symptom_count,
                    comparison_count=comparison_count,
                    symptom_metric_avg=round(symptom_avg, 2),
                    comparison_metric_avg=round(comparison_avg, 2),
                    weekday_confounded=weekday_confounded,
                    work_context_confounded=work_context_confounded,
                    calendar_context_confounded=calendar_context_confounded,
                    sample_n=len(entries),
                )
            )

    return associations


def _phi(a: int, b: int, c: int, d: int) -> float | None:
    denominator = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    if denominator == 0:
        return None
    return (a * d - b * c) / denominator


def _cooccurrence_stats(
    entries: Sequence[DailySymptomEntry],
    *,
    symptom_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> tuple[int, int, int, int, float, float, float, float] | None:
    total = len(entries)
    co_count = sum(
        1 for entry in entries if symptom_id in entry.symptom_ids and tag_id in entry.tag_ids
    )
    symptom_count = sum(1 for entry in entries if symptom_id in entry.symptom_ids)
    tag_count = sum(1 for entry in entries if tag_id in entry.tag_ids)
    neither_count = total - symptom_count - tag_count + co_count
    symptom_only = symptom_count - co_count
    tag_only = tag_count - co_count

    phi = _phi(co_count, symptom_only, tag_only, neither_count)
    if phi is None:
        return None
    union_count = symptom_count + tag_count - co_count
    jaccard = co_count / union_count if union_count else 0.0
    expected = (symptom_count / total) * (tag_count / total)
    observed = co_count / total
    lift = observed / expected if expected else 0.0
    _, p_value = fisher_exact([[co_count, symptom_only], [tag_only, neither_count]])
    return co_count, symptom_count, tag_count, total, phi, jaccard, lift, float(p_value)


def compute_symptom_tag_associations(
    entries: Sequence[DailySymptomEntry],
    symptoms: Mapping[uuid.UUID, SymptomRef],
    tags: Mapping[uuid.UUID, TagRef],
    *,
    min_entries: int = MIN_SYMPTOM_ANALYTICS_ENTRIES,
    min_symptom_usages: int = MIN_SYMPTOM_USAGES,
    min_tag_usages: int = MIN_TAG_USAGES_FOR_SYMPTOM_COOCCURRENCE,
    card_lift_delta: float = MIN_CARD_LIFT_DELTA,
) -> list[SymptomTagAssociation]:
    """Compute symptom x tag associations with Fisher exact + BH-FDR."""

    if len(entries) < min_entries:
        return []

    symptom_counts = {
        symptom_id: sum(1 for entry in entries if symptom_id in entry.symptom_ids)
        for symptom_id in symptoms
    }
    tag_counts = {tag_id: sum(1 for entry in entries if tag_id in entry.tag_ids) for tag_id in tags}

    raw: list[
        tuple[SymptomRef, TagRef, int, int, int, int, float, float, float, float, bool, bool, bool]
    ] = []
    for symptom_id, symptom in sorted(symptoms.items(), key=lambda item: item[1].slug):
        if symptom_counts[symptom_id] < min_symptom_usages:
            continue
        for tag_id, tag in sorted(tags.items(), key=lambda item: item[1].slug):
            if tag_counts[tag_id] < min_tag_usages:
                continue
            stats = _cooccurrence_stats(entries, symptom_id=symptom_id, tag_id=tag_id)
            if stats is None:
                continue
            co_count, symptom_count, tag_count, total, phi, jaccard, lift, p_value = stats
            if co_count < 5 and not (co_count >= 3 and p_value < 0.05):
                continue
            weekday_confounded = (
                is_weekday_biased_signal(entries, symptom_id, kind="symptom")
                and is_weekday_biased_signal(entries, tag_id, kind="tag")
            ) or is_pair_cooccurrence_weekday_confounded(
                [entry.entry_date for entry in entries],
                [1 if symptom_id in entry.symptom_ids else 0 for entry in entries],
                [1 if tag_id in entry.tag_ids else 0 for entry in entries],
                alpha=SYMPTOM_FDR_ALPHA,
            )
            work_context_confounded = (
                is_work_context_biased_signal(entries, symptom_id, kind="symptom")
                and is_work_context_biased_signal(entries, tag_id, kind="tag")
            )
            calendar_context_confounded = (
                weekday_confounded
                or work_context_confounded
                or is_pair_cooccurrence_calendar_context_confounded(
                    [entry.entry_date for entry in entries],
                    [entry.work_context.value for entry in entries],
                    [1 if symptom_id in entry.symptom_ids else 0 for entry in entries],
                    [1 if tag_id in entry.tag_ids else 0 for entry in entries],
                    alpha=SYMPTOM_FDR_ALPHA,
                )
            )
            raw.append(
                (
                    symptom,
                    tag,
                    co_count,
                    symptom_count,
                    tag_count,
                    total,
                    phi,
                    jaccard,
                    lift,
                    p_value,
                    weekday_confounded,
                    work_context_confounded,
                    calendar_context_confounded,
                )
            )

    associations: list[SymptomTagAssociation] = []
    for (
        symptom,
        tag,
        co_count,
        symptom_count,
        tag_count,
        total,
        phi,
        jaccard,
        lift,
        p_value,
        weekday_confounded,
        work_context_confounded,
        calendar_context_confounded,
    ), (significant, p_corrected) in zip(
        raw,
        _fdr_correct([item[9] for item in raw]),
        strict=True,
    ):
        if not significant or abs(lift - 1.0) <= card_lift_delta:
            continue
        associations.append(
            SymptomTagAssociation(
                symptom=symptom,
                tag=tag,
                phi=round(phi, 4),
                jaccard=round(jaccard, 4),
                lift=round(lift, 4),
                p_value=round(p_value, 6),
                p_corrected=round(p_corrected, 6),
                co_count=co_count,
                symptom_count=symptom_count,
                tag_count=tag_count,
                total_count=total,
                weekday_confounded=weekday_confounded,
                work_context_confounded=work_context_confounded,
                calendar_context_confounded=calendar_context_confounded,
            )
        )

    associations.sort(key=lambda item: (-abs(item.lift - 1.0), item.symptom.slug, item.tag.slug))
    return associations


def heatmap_symptom_tag_associations(
    entries: Sequence[DailySymptomEntry],
    symptoms: Mapping[uuid.UUID, SymptomRef],
    tags: Mapping[uuid.UUID, TagRef],
    *,
    min_entries: int = MIN_SYMPTOM_ANALYTICS_ENTRIES,
    min_symptom_usages: int = MIN_SYMPTOM_USAGES,
    min_tag_usages: int = MIN_TAG_USAGES_FOR_SYMPTOM_COOCCURRENCE,
    heatmap_lift_delta: float = MIN_HEATMAP_LIFT_DELTA,
) -> list[SymptomTagAssociation]:
    """Return associations broad enough for exploratory heatmap rendering."""

    if len(entries) < min_entries:
        return []

    raw = compute_symptom_tag_associations(
        entries,
        symptoms,
        tags,
        min_entries=min_entries,
        min_symptom_usages=min_symptom_usages,
        min_tag_usages=min_tag_usages,
        card_lift_delta=0.0,
    )
    return [
        association
        for association in raw
        if abs(association.lift - 1.0) > heatmap_lift_delta
        or association.p_corrected <= SYMPTOM_FDR_ALPHA
    ]

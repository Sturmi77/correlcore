"""M7 symptom analytics helpers for univariate and co-occurrence insights."""

from __future__ import annotations

import math
import time
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
MIN_TAG_USAGES_FOR_TAG_COOCCURRENCE = 5
MIN_ABS_SYMPTOM_EFFECT_SIZE = 0.25
SYMPTOM_FDR_ALPHA = 0.10
# Shared by symptom×tag and tag×tag co-occurrence families (Fisher + BH-FDR).
# Do not reuse insights/shared.FDR_ALPHA (0.05) — that gates bivariate insight cards.
COOCCURRENCE_FDR_ALPHA = SYMPTOM_FDR_ALPHA
MIN_CARD_LIFT_DELTA = 0.67
MIN_HEATMAP_LIFT_DELTA = 0.50

METRIC_TARGETS: tuple[MetricName, ...] = ("mood_score", "energy", "stress")


class CooccurrenceComputationTimeout(RuntimeError):
    """Raised cooperatively when an interactive analysis exhausts its budget."""


def _check_cooccurrence_deadline(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise CooccurrenceComputationTimeout


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
    # The raw metric values behind each group, so the insight payload can carry
    # real G2 distributions. Without them the UI had group sizes but no
    # histograms and synthesised zeros, rendering "good on 0 of N days" (#928 L2).
    symptom_metric_values: tuple[float, ...] = ()
    comparison_metric_values: tuple[float, ...] = ()


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


@dataclass(frozen=True)
class TagTagAssociation:
    tag_a: TagRef
    tag_b: TagRef
    phi: float
    jaccard: float
    lift: float
    p_value: float
    p_corrected: float
    co_count: int
    tag_a_count: int
    tag_b_count: int
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
        alpha=COOCCURRENCE_FDR_ALPHA,
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

    context_counts = [
        sum(1 for entry in entries if entry.work_context == context) for context in contexts
    ]
    expected = [total * context_count / len(entries) for context_count in context_counts]
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
        raw: list[
            tuple[
                SymptomRef,
                float,
                float,
                int,
                int,
                float,
                float,
                bool,
                bool,
                bool,
                tuple[float, ...],
                tuple[float, ...],
            ]
        ] = []
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

            symptom_values = tuple(
                float(value)
                for value, present in zip(metric_values, binary, strict=True)
                if present
            )
            comparison_values = tuple(
                float(value)
                for value, present in zip(metric_values, binary, strict=True)
                if not present
            )
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
                    symptom_values,
                    comparison_values,
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
            symptom_values,
            comparison_values,
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
                    symptom_metric_values=symptom_values,
                    comparison_metric_values=comparison_values,
                )
            )

    return associations


def _phi(a: int, b: int, c: int, d: int) -> float | None:
    denominator = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    if denominator == 0:
        return None
    return (a * d - b * c) / denominator


def _signal_present(
    entry: DailySymptomEntry,
    signal_id: uuid.UUID,
    *,
    kind: Literal["tag", "symptom"],
) -> bool:
    return signal_id in (entry.tag_ids if kind == "tag" else entry.symptom_ids)


def _cooccurrence_stats(
    entries: Sequence[DailySymptomEntry],
    *,
    signal_a_id: uuid.UUID,
    signal_b_id: uuid.UUID,
    kind_a: Literal["tag", "symptom"],
    kind_b: Literal["tag", "symptom"],
) -> tuple[int, int, int, int, float, float, float, float] | None:
    total = len(entries)
    co_count = sum(
        1
        for entry in entries
        if _signal_present(entry, signal_a_id, kind=kind_a)
        and _signal_present(entry, signal_b_id, kind=kind_b)
    )
    count_a = sum(1 for entry in entries if _signal_present(entry, signal_a_id, kind=kind_a))
    count_b = sum(1 for entry in entries if _signal_present(entry, signal_b_id, kind=kind_b))
    neither_count = total - count_a - count_b + co_count
    only_a = count_a - co_count
    only_b = count_b - co_count

    phi = _phi(co_count, only_a, only_b, neither_count)
    if phi is None:
        return None
    union_count = count_a + count_b - co_count
    jaccard = co_count / union_count if union_count else 0.0
    expected = (count_a / total) * (count_b / total)
    observed = co_count / total
    lift = observed / expected if expected else 0.0
    _, p_value = fisher_exact([[co_count, only_a], [only_b, neither_count]])
    return co_count, count_a, count_b, total, phi, jaccard, lift, float(p_value)


def _cooccurrence_stats_from_presence(
    present_a: frozenset[int],
    present_b: frozenset[int],
    *,
    total: int,
) -> tuple[int, int, int, int, float, float, float, float] | None:
    """Equivalent pair statistics from precomputed daily-presence indexes."""

    co_count = len(present_a & present_b)
    count_a = len(present_a)
    count_b = len(present_b)
    neither_count = total - count_a - count_b + co_count
    only_a = count_a - co_count
    only_b = count_b - co_count
    phi = _phi(co_count, only_a, only_b, neither_count)
    if phi is None:
        return None
    union_count = count_a + count_b - co_count
    jaccard = co_count / union_count if union_count else 0.0
    expected = (count_a / total) * (count_b / total)
    observed = co_count / total
    lift = observed / expected if expected else 0.0
    _, p_value = fisher_exact([[co_count, only_a], [only_b, neither_count]])
    return co_count, count_a, count_b, total, phi, jaccard, lift, float(p_value)


def compute_symptom_tag_associations(
    entries: Sequence[DailySymptomEntry],
    symptoms: Mapping[uuid.UUID, SymptomRef],
    tags: Mapping[uuid.UUID, TagRef],
    *,
    min_entries: int = MIN_SYMPTOM_ANALYTICS_ENTRIES,
    min_symptom_usages: int = MIN_SYMPTOM_USAGES,
    min_tag_usages: int = MIN_TAG_USAGES_FOR_SYMPTOM_COOCCURRENCE,
    card_lift_delta: float = MIN_CARD_LIFT_DELTA,
    deadline: float | None = None,
) -> list[SymptomTagAssociation]:
    """Compute symptom x tag associations with Fisher exact + BH-FDR."""

    if len(entries) < min_entries:
        return []

    symptom_presence = {
        symptom_id: frozenset(
            index for index, entry in enumerate(entries) if symptom_id in entry.symptom_ids
        )
        for symptom_id in symptoms
    }
    tag_presence = {
        tag_id: frozenset(index for index, entry in enumerate(entries) if tag_id in entry.tag_ids)
        for tag_id in tags
    }
    symptom_counts = {signal_id: len(indexes) for signal_id, indexes in symptom_presence.items()}
    tag_counts = {signal_id: len(indexes) for signal_id, indexes in tag_presence.items()}
    symptom_vectors = {
        signal_id: [1 if index in indexes else 0 for index in range(len(entries))]
        for signal_id, indexes in symptom_presence.items()
    }
    tag_vectors = {
        signal_id: [1 if index in indexes else 0 for index in range(len(entries))]
        for signal_id, indexes in tag_presence.items()
    }
    entry_dates = [entry.entry_date for entry in entries]
    work_contexts = [entry.work_context.value for entry in entries]
    symptom_weekday_bias = {
        signal_id: is_weekday_biased_signal(entries, signal_id, kind="symptom")
        for signal_id in symptoms
    }
    tag_weekday_bias = {
        signal_id: is_weekday_biased_signal(entries, signal_id, kind="tag") for signal_id in tags
    }
    symptom_work_bias = {
        signal_id: is_work_context_biased_signal(entries, signal_id, kind="symptom")
        for signal_id in symptoms
    }
    tag_work_bias = {
        signal_id: is_work_context_biased_signal(entries, signal_id, kind="tag")
        for signal_id in tags
    }

    raw: list[
        tuple[SymptomRef, TagRef, int, int, int, int, float, float, float, float, bool, bool, bool]
    ] = []
    for symptom_id, symptom in sorted(symptoms.items(), key=lambda item: item[1].slug):
        _check_cooccurrence_deadline(deadline)
        if symptom_counts[symptom_id] < min_symptom_usages:
            continue
        for tag_id, tag in sorted(tags.items(), key=lambda item: item[1].slug):
            _check_cooccurrence_deadline(deadline)
            if tag_counts[tag_id] < min_tag_usages:
                continue
            stats = _cooccurrence_stats_from_presence(
                symptom_presence[symptom_id],
                tag_presence[tag_id],
                total=len(entries),
            )
            if stats is None:
                continue
            co_count, symptom_count, tag_count, total, phi, jaccard, lift, p_value = stats
            if co_count < 5 and not (co_count >= 3 and p_value < 0.05):
                continue
            weekday_confounded = (
                symptom_weekday_bias[symptom_id]
                and tag_weekday_bias[tag_id]
            ) or is_pair_cooccurrence_weekday_confounded(
                entry_dates,
                symptom_vectors[symptom_id],
                tag_vectors[tag_id],
                alpha=COOCCURRENCE_FDR_ALPHA,
            )
            work_context_confounded = (
                symptom_work_bias[symptom_id] and tag_work_bias[tag_id]
            )
            calendar_context_confounded = (
                weekday_confounded
                or work_context_confounded
                or is_pair_cooccurrence_calendar_context_confounded(
                    entry_dates,
                    work_contexts,
                    symptom_vectors[symptom_id],
                    tag_vectors[tag_id],
                    alpha=COOCCURRENCE_FDR_ALPHA,
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
    deadline: float | None = None,
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
        deadline=deadline,
    )
    return [
        association
        for association in raw
        if abs(association.lift - 1.0) > heatmap_lift_delta
        or association.p_corrected <= COOCCURRENCE_FDR_ALPHA
    ]


def compute_tag_tag_associations(
    entries: Sequence[DailySymptomEntry],
    tags: Mapping[uuid.UUID, TagRef],
    *,
    min_entries: int = MIN_SYMPTOM_ANALYTICS_ENTRIES,
    min_tag_usages: int = MIN_TAG_USAGES_FOR_TAG_COOCCURRENCE,
    card_lift_delta: float = MIN_CARD_LIFT_DELTA,
    require_significance: bool = True,
    deadline: float | None = None,
) -> list[TagTagAssociation]:
    """Compute tag×tag associations with Fisher exact + BH-FDR (α=0.10).

    ``require_significance=False`` keeps FDR-insignificant pairs in the result so
    a caller can apply its own gate. The heatmap needs that: it admits a pair on
    *either* a large lift or FDR significance, but this function dropped the
    insignificant ones first, so the lift half of that rule could never fire
    (#966). ``p_corrected`` rides along either way.
    """

    if len(entries) < min_entries:
        return []

    tag_presence = {
        tag_id: frozenset(index for index, entry in enumerate(entries) if tag_id in entry.tag_ids)
        for tag_id in tags
    }
    tag_counts = {signal_id: len(indexes) for signal_id, indexes in tag_presence.items()}
    tag_vectors = {
        signal_id: [1 if index in indexes else 0 for index in range(len(entries))]
        for signal_id, indexes in tag_presence.items()
    }
    entry_dates = [entry.entry_date for entry in entries]
    work_contexts = [entry.work_context.value for entry in entries]
    tag_weekday_bias = {
        signal_id: is_weekday_biased_signal(entries, signal_id, kind="tag") for signal_id in tags
    }
    tag_work_bias = {
        signal_id: is_work_context_biased_signal(entries, signal_id, kind="tag")
        for signal_id in tags
    }
    tag_items = sorted(tags.items(), key=lambda item: item[1].slug)

    raw: list[
        tuple[TagRef, TagRef, int, int, int, int, float, float, float, float, bool, bool, bool]
    ] = []
    for index, (tag_a_id, tag_a) in enumerate(tag_items):
        _check_cooccurrence_deadline(deadline)
        if tag_counts[tag_a_id] < min_tag_usages:
            continue
        for tag_b_id, tag_b in tag_items[index + 1 :]:
            _check_cooccurrence_deadline(deadline)
            if tag_counts[tag_b_id] < min_tag_usages:
                continue
            stats = _cooccurrence_stats_from_presence(
                tag_presence[tag_a_id],
                tag_presence[tag_b_id],
                total=len(entries),
            )
            if stats is None:
                continue
            co_count, count_a, count_b, total, phi, jaccard, lift, p_value = stats
            if co_count < 5 and not (co_count >= 3 and p_value < 0.05):
                continue
            weekday_confounded = (
                tag_weekday_bias[tag_a_id]
                and tag_weekday_bias[tag_b_id]
            ) or is_pair_cooccurrence_weekday_confounded(
                entry_dates,
                tag_vectors[tag_a_id],
                tag_vectors[tag_b_id],
                alpha=COOCCURRENCE_FDR_ALPHA,
            )
            work_context_confounded = tag_work_bias[tag_a_id] and tag_work_bias[tag_b_id]
            calendar_context_confounded = (
                weekday_confounded
                or work_context_confounded
                or is_pair_cooccurrence_calendar_context_confounded(
                    entry_dates,
                    work_contexts,
                    tag_vectors[tag_a_id],
                    tag_vectors[tag_b_id],
                    alpha=COOCCURRENCE_FDR_ALPHA,
                )
            )
            raw.append(
                (
                    tag_a,
                    tag_b,
                    co_count,
                    count_a,
                    count_b,
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

    associations: list[TagTagAssociation] = []
    for (
        tag_a,
        tag_b,
        co_count,
        count_a,
        count_b,
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
        if require_significance and not significant:
            continue
        if abs(lift - 1.0) <= card_lift_delta:
            continue
        associations.append(
            TagTagAssociation(
                tag_a=tag_a,
                tag_b=tag_b,
                phi=round(phi, 4),
                jaccard=round(jaccard, 4),
                lift=round(lift, 4),
                p_value=round(p_value, 6),
                p_corrected=round(p_corrected, 6),
                co_count=co_count,
                tag_a_count=count_a,
                tag_b_count=count_b,
                total_count=total,
                weekday_confounded=weekday_confounded,
                work_context_confounded=work_context_confounded,
                calendar_context_confounded=calendar_context_confounded,
            )
        )

    associations.sort(key=lambda item: (-abs(item.lift - 1.0), item.tag_a.slug, item.tag_b.slug))
    return associations


def heatmap_tag_tag_associations(
    entries: Sequence[DailySymptomEntry],
    tags: Mapping[uuid.UUID, TagRef],
    *,
    min_entries: int = MIN_SYMPTOM_ANALYTICS_ENTRIES,
    min_tag_usages: int = MIN_TAG_USAGES_FOR_TAG_COOCCURRENCE,
    heatmap_lift_delta: float = MIN_HEATMAP_LIFT_DELTA,
    deadline: float | None = None,
) -> list[TagTagAssociation]:
    """Return tag×tag associations for the Insights heatmap gate (no UI lift column)."""

    if len(entries) < min_entries:
        return []

    raw = compute_tag_tag_associations(
        entries,
        tags,
        min_entries=min_entries,
        min_tag_usages=min_tag_usages,
        card_lift_delta=0.0,
        # The gate below admits a pair on a large lift *or* FDR significance;
        # dropping the insignificant ones here would decide that in advance.
        require_significance=False,
        deadline=deadline,
    )
    return [
        association
        for association in raw
        if abs(association.lift - 1.0) > heatmap_lift_delta
        or association.p_corrected <= COOCCURRENCE_FDR_ALPHA
    ]

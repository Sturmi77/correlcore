"""Bivariate correlation insight families.

Spearman metric↔metric, Spearman sleep↔mood (pairwise deletion), and
point-biserial tag↔mood associations. Split out of ``insight_engine`` (#777);
behavior is unchanged.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date as date_type

from scipy.stats import pointbiserialr, spearmanr

from app.core.config import settings
from app.models.insight import InsightTier, InsightType
from app.services.insights.shared import (
    _METRIC_LABELS,
    _SLEEP_METRIC_LABELS,
    FDR_ALPHA,
    MIN_ABS_EFFECT_SIZE,
    MIN_BIVARIATE_ENTRIES,
    MIN_SLEEP_OBSERVATIONS,
    MIN_TAG_GROUP_SIZE,
    AnalyticsEntry,
    InsightCandidate,
    MetricName,
    SleepMetricName,
    TagSnapshot,
    _base_flags,
    _confidence,
    _confounders,
    _context_confounded_statement,
    _direction,
    _fdr_results,
    _finite_float,
    _metric_value,
    _primary_confounder,
    _weekday_confounded_statement,
    confidence_tier_for_sample,
    is_weekday_biased,
    is_work_context_biased,
)
from app.services.weekday_confounder import (
    is_continuous_association_calendar_context_confounded,
    is_continuous_association_weekday_confounded,
    is_metric_association_calendar_context_confounded,
    is_metric_association_weekday_confounded,
)


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
            f"when {_METRIC_LABELS[right]} is higher."
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


def _sleep_spearman_candidates(
    entries: Sequence[AnalyticsEntry],
    *,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    """Spearman sleep↔mood correlations (M8 Sprint 2, #172).

    Sleep is optional, so each metric uses pairwise deletion: only days that
    recorded that sleep value take part, and a pair needs at least
    ``MIN_SLEEP_OBSERVATIONS`` such days. The confidence tier reflects that
    paired count, not the total entry count. FDR is applied across the sleep
    family independently of the always-present metric pairs. A raw hit is
    checked against weekday/work-context OLS controls (e.g. weekend days with
    both more sleep and better mood) and flagged rather than presented as a
    plain sleep association when calendar context explains it away.
    """
    if len(entries) < MIN_BIVARIATE_ENTRIES:
        return []

    raw: list[tuple[SleepMetricName, float, float, int, bool, bool]] = []
    metrics: tuple[SleepMetricName, ...] = ("sleep_minutes", "sleep_quality")
    for metric in metrics:
        paired = [
            (entry.entry_date, entry.work_context, getattr(entry, metric), entry.mood_score)
            for entry in entries
            if getattr(entry, metric) is not None
        ]
        if len(paired) < MIN_SLEEP_OBSERVATIONS:
            continue
        entry_dates = [item[0] for item in paired]
        work_contexts = [item[1] for item in paired]
        sleep_values = [item[2] for item in paired]
        mood_values = [item[3] for item in paired]
        if len(set(sleep_values)) < 2 or len(set(mood_values)) < 2:
            continue
        result = spearmanr(sleep_values, mood_values)
        rho = _finite_float(result.statistic)
        p_value = _finite_float(result.pvalue)
        if rho is None or p_value is None or abs(rho) < MIN_ABS_EFFECT_SIZE:
            continue

        weekday_confounded = is_continuous_association_weekday_confounded(
            entry_dates,
            mood_values,
            sleep_values,
            raw_coefficient=rho,
            raw_p_value=p_value,
            min_effect=MIN_ABS_EFFECT_SIZE,
            alpha=FDR_ALPHA,
        )
        calendar_context_confounded = (
            weekday_confounded
            or is_continuous_association_calendar_context_confounded(
                entry_dates,
                [work_context.value for work_context in work_contexts],
                mood_values,
                sleep_values,
                raw_coefficient=rho,
                raw_p_value=p_value,
                min_effect=MIN_ABS_EFFECT_SIZE,
                alpha=FDR_ALPHA,
            )
        )
        raw.append(
            (metric, rho, p_value, len(paired), weekday_confounded, calendar_context_confounded)
        )

    candidates: list[InsightCandidate] = []
    for (
        metric,
        rho,
        p_value,
        sample_n,
        weekday_confounded,
        calendar_context_confounded,
    ), (significant, p_corrected) in zip(
        raw,
        _fdr_results([item[2] for item in raw]),
        strict=True,
    ):
        if not significant:
            continue
        tier = confidence_tier_for_sample(sample_n)
        direction = _direction(rho, "higher", "lower")
        label = _SLEEP_METRIC_LABELS[metric]
        statement = f"In your entries so far, mood tends to be {direction} when {label} is higher."
        statement = _weekday_confounded_statement(
            statement, weekday_confounded=calendar_context_confounded
        )
        confounders = _confounders(
            weekday_confounded=weekday_confounded,
            work_context_confounded=False,
            calendar_context_confounded=calendar_context_confounded,
        )
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SPEARMAN,
                tier=tier,
                metric=f"mood_{metric}",
                subject_type="metric",
                subject_id=None,
                subject_label=metric,
                effect_size=round(rho, 4),
                confidence=_confidence(rho, p_corrected, tier),
                sample_n=sample_n,
                statement=statement,
                flags={
                    **_base_flags(p_value=p_value, p_corrected=p_corrected, method="spearman"),
                    "weekday_confounded": weekday_confounded,
                    "calendar_context_confounded": calendar_context_confounded,
                },
                payload={
                    "left_metric": "mood_score",
                    "right_metric": metric,
                    "rho": round(rho, 4),
                    "p_corrected": round(p_corrected, 4),
                    "confounder": _primary_confounder(confounders),
                    "confounders": confounders,
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
            f"Days tagged {tag.label} currently line up with {direction} mood scores in your data."
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

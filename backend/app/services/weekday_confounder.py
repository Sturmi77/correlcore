"""OLS weekday confounder checks with Newey-West HAC standard errors (ADR-0016, #146)."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_type
from typing import Any

import numpy as np
import statsmodels.api as sm

from app.services.metric_semantics import (
    GOOD_METRIC_THRESHOLD,
    is_good_metric_value,
    metric_semantics,
)

DEFAULT_ALPHA = 0.10
DEFAULT_MIN_EFFECT = 0.25
MIN_OLS_ROWS = 10
MIN_CONTEXT_OLS_ROWS = 30
# Kept for importers; the per-metric rules live in app.services.metric_semantics (#955).
DEFAULT_GOOD_THRESHOLD = GOOD_METRIC_THRESHOLD


@dataclass(frozen=True)
class MetricAdjustmentResult:
    """OLS signal coefficient after holding weekday / calendar context (Phase 12 / L5)."""

    confounded: bool
    adjusted_coefficient: float | None
    adjusted_p: float | None
    n: int


@dataclass(frozen=True)
class SameSituationFrequencies:
    """Natural frequencies on the modal work situation of signal days (Phase 12 / L5)."""

    context: str | None
    with_n: int
    without_n: int
    with_good: int
    without_good: int


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _weekday_dummy_matrix(weekdays: Sequence[int]) -> np.ndarray:
    """Monday–Saturday dummies with Sunday (0) as the reference category."""

    matrix = np.zeros((len(weekdays), 6), dtype=float)
    for index, weekday in enumerate(weekdays):
        if weekday == 0:
            continue
        matrix[index, weekday - 1] = 1.0
    return matrix


def _categorical_dummy_matrix(values: Sequence[str]) -> np.ndarray:
    """Return one-hot dummies with the first sorted category as reference."""

    categories = sorted(set(values))
    if len(categories) <= 1:
        return np.zeros((len(values), 0), dtype=float)

    columns = categories[1:]
    matrix = np.zeros((len(values), len(columns)), dtype=float)
    for row, value in enumerate(values):
        for col, category in enumerate(columns):
            if value == category:
                matrix[row, col] = 1.0
                break
    return matrix


def _hac_maxlags(sample_n: int) -> int:
    return max(1, min(7, sample_n // 5))


def _confounded_from_adjusted(
    adjusted_coef: float | None,
    adjusted_p: float | None,
    *,
    min_effect: float,
    alpha: float,
) -> bool:
    if adjusted_coef is None or adjusted_p is None:
        return False
    return adjusted_p >= alpha or abs(adjusted_coef) < min_effect


def same_work_context_metric_frequencies(
    work_contexts: Sequence[str],
    binary_signal: Sequence[int],
    metric_values: Sequence[float | int],
    *,
    metric: str,
) -> SameSituationFrequencies:
    """Count good days with/without the signal inside the modal work context of signal days.

    ``metric`` decides what a good day is. It is required: this helper is reached
    from the symptom family, which iterates every metric target, and a fixed
    ``>= 4`` there counted the *most stressful* days as good ones (#955).
    """

    empty = SameSituationFrequencies(
        context=None, with_n=0, without_n=0, with_good=0, without_good=0
    )
    if not (
        len(work_contexts) == len(binary_signal) == len(metric_values) and len(work_contexts) > 0
    ):
        return empty

    signal_contexts = [
        context for context, present in zip(work_contexts, binary_signal, strict=True) if present
    ]
    if not signal_contexts:
        return empty
    context, _ = Counter(signal_contexts).most_common(1)[0]

    with_n = without_n = with_good = without_good = 0
    for ctx, present, metric_value in zip(work_contexts, binary_signal, metric_values, strict=True):
        if ctx != context:
            continue
        good = is_good_metric_value(metric, metric_value)
        if present:
            with_n += 1
            if good:
                with_good += 1
        else:
            without_n += 1
            if good:
                without_good += 1

    if with_n == 0 or without_n == 0:
        return SameSituationFrequencies(
            context=context,
            with_n=with_n,
            without_n=without_n,
            with_good=with_good,
            without_good=without_good,
        )
    return SameSituationFrequencies(
        context=context,
        with_n=with_n,
        without_n=without_n,
        with_good=with_good,
        without_good=without_good,
    )


def evaluate_metric_association_weekday(
    entry_dates: Sequence[date_type],
    metric_values: Sequence[float],
    binary_signal: Sequence[int],
    *,
    raw_coefficient: float,
    raw_p_value: float,
    min_effect: float = DEFAULT_MIN_EFFECT,
    alpha: float = DEFAULT_ALPHA,
) -> MetricAdjustmentResult:
    """OLS signal coefficient after weekday dummies; also used as the confounded gate."""

    n = len(entry_dates)
    if raw_p_value >= alpha or abs(raw_coefficient) < min_effect:
        return MetricAdjustmentResult(False, None, None, n)
    if n < MIN_OLS_ROWS:
        return MetricAdjustmentResult(False, None, None, n)
    if len(set(metric_values)) < 2 or len(set(binary_signal)) < 2:
        return MetricAdjustmentResult(False, None, None, n)

    weekdays = [entry_date.weekday() for entry_date in entry_dates]
    signal_weekdays = {
        weekday for weekday, present in zip(weekdays, binary_signal, strict=True) if present
    }
    if len(signal_weekdays) <= 1:
        return MetricAdjustmentResult(True, None, None, n)

    y = np.asarray(metric_values, dtype=float)
    signal = np.asarray(binary_signal, dtype=float)
    weekday_matrix = _weekday_dummy_matrix(weekdays)
    design = sm.add_constant(np.column_stack([signal, weekday_matrix]), has_constant="add")

    try:
        result = sm.OLS(y, design).fit(
            cov_type="HAC",
            cov_kwds={"maxlags": _hac_maxlags(len(y))},
        )
    except (ValueError, np.linalg.LinAlgError):
        return MetricAdjustmentResult(False, None, None, n)

    adjusted_coef = _finite_float(result.params[1])
    adjusted_p = _finite_float(result.pvalues[1])
    return MetricAdjustmentResult(
        confounded=_confounded_from_adjusted(
            adjusted_coef, adjusted_p, min_effect=min_effect, alpha=alpha
        ),
        adjusted_coefficient=round(adjusted_coef, 4) if adjusted_coef is not None else None,
        adjusted_p=round(adjusted_p, 6) if adjusted_p is not None else None,
        n=n,
    )


def is_metric_association_weekday_confounded(
    entry_dates: Sequence[date_type],
    metric_values: Sequence[float],
    binary_signal: Sequence[int],
    *,
    raw_coefficient: float,
    raw_p_value: float,
    min_effect: float = DEFAULT_MIN_EFFECT,
    alpha: float = DEFAULT_ALPHA,
) -> bool:
    """Return True when a raw association is explained by weekday effects after OLS adjustment."""

    return evaluate_metric_association_weekday(
        entry_dates,
        metric_values,
        binary_signal,
        raw_coefficient=raw_coefficient,
        raw_p_value=raw_p_value,
        min_effect=min_effect,
        alpha=alpha,
    ).confounded


def evaluate_metric_association_calendar_context(
    entry_dates: Sequence[date_type],
    work_contexts: Sequence[str],
    metric_values: Sequence[float],
    binary_signal: Sequence[int],
    *,
    raw_coefficient: float,
    raw_p_value: float,
    min_effect: float = DEFAULT_MIN_EFFECT,
    alpha: float = DEFAULT_ALPHA,
) -> MetricAdjustmentResult:
    """OLS signal coefficient after weekday + work-context dummies."""

    n = len(entry_dates)
    if raw_p_value >= alpha or abs(raw_coefficient) < min_effect:
        return MetricAdjustmentResult(False, None, None, n)
    if n < MIN_CONTEXT_OLS_ROWS:
        return MetricAdjustmentResult(False, None, None, n)
    if len(entry_dates) != len(work_contexts):
        return MetricAdjustmentResult(False, None, None, n)
    if len(set(metric_values)) < 2 or len(set(binary_signal)) < 2:
        return MetricAdjustmentResult(False, None, None, n)
    if len(set(work_contexts)) < 2:
        return MetricAdjustmentResult(False, None, None, n)

    signal_contexts = {
        context for context, present in zip(work_contexts, binary_signal, strict=True) if present
    }
    if len(signal_contexts) <= 1:
        return MetricAdjustmentResult(True, None, None, n)

    y = np.asarray(metric_values, dtype=float)
    signal = np.asarray(binary_signal, dtype=float)
    weekdays = [entry_date.weekday() for entry_date in entry_dates]
    design = sm.add_constant(
        np.column_stack(
            [
                signal,
                _weekday_dummy_matrix(weekdays),
                _categorical_dummy_matrix(work_contexts),
            ]
        ),
        has_constant="add",
    )

    try:
        result = sm.OLS(y, design).fit(
            cov_type="HAC",
            cov_kwds={"maxlags": _hac_maxlags(len(y))},
        )
    except (ValueError, np.linalg.LinAlgError):
        return MetricAdjustmentResult(False, None, None, n)

    adjusted_coef = _finite_float(result.params[1])
    adjusted_p = _finite_float(result.pvalues[1])
    return MetricAdjustmentResult(
        confounded=_confounded_from_adjusted(
            adjusted_coef, adjusted_p, min_effect=min_effect, alpha=alpha
        ),
        adjusted_coefficient=round(adjusted_coef, 4) if adjusted_coef is not None else None,
        adjusted_p=round(adjusted_p, 6) if adjusted_p is not None else None,
        n=n,
    )


def is_metric_association_calendar_context_confounded(
    entry_dates: Sequence[date_type],
    work_contexts: Sequence[str],
    metric_values: Sequence[float],
    binary_signal: Sequence[int],
    *,
    raw_coefficient: float,
    raw_p_value: float,
    min_effect: float = DEFAULT_MIN_EFFECT,
    alpha: float = DEFAULT_ALPHA,
) -> bool:
    """Return True when weekday/work-context controls explain a raw metric association."""

    return evaluate_metric_association_calendar_context(
        entry_dates,
        work_contexts,
        metric_values,
        binary_signal,
        raw_coefficient=raw_coefficient,
        raw_p_value=raw_p_value,
        min_effect=min_effect,
        alpha=alpha,
    ).confounded


def situation_adjustment_payload(
    *,
    weekday: MetricAdjustmentResult,
    calendar: MetricAdjustmentResult,
    situation: SameSituationFrequencies,
    primary_confounder: str | None,
    metric: str,
) -> dict[str, object]:
    """Additive Layer-2 payload keys — natural frequencies first, coefficients optional."""

    semantics = metric_semantics(metric)
    survives = True
    if primary_confounder in {"weekday", "calendar_context", "work_context"}:
        if primary_confounder == "weekday":
            survives = not weekday.confounded
        else:
            survives = not calendar.confounded

    payload: dict[str, object] = {
        "situation_effect_survives": survives,
        "weekday_held_coefficient": weekday.adjusted_coefficient,
        "weekday_held_p": weekday.adjusted_p,
        "calendar_held_coefficient": calendar.adjusted_coefficient,
        "calendar_held_p": calendar.adjusted_p,
    }
    if situation.context and situation.with_n > 0 and situation.without_n > 0:
        payload.update(
            {
                "same_work_context": situation.context,
                "same_work_context_with_n": situation.with_n,
                "same_work_context_without_n": situation.without_n,
                "same_work_context_with_good": situation.with_good,
                "same_work_context_without_good": situation.without_good,
                # Good-day counts never travel without the rule that produced
                # them — "good" is `<= 2` on stress and `>= 4` elsewhere (#955).
                "same_work_context_good_threshold": semantics.good_threshold,
                "same_work_context_good_direction": semantics.good_direction,
            }
        )
    return payload


def _standardized(values: Sequence[float]) -> np.ndarray | None:
    """Z-score a continuous predictor so its OLS coefficient is comparable to
    ``min_effect`` thresholds tuned for correlation-scale effect sizes."""

    array = np.asarray(values, dtype=float)
    std = array.std(ddof=0)
    if std == 0:
        return None
    return np.asarray((array - array.mean()) / std, dtype=float)


def is_continuous_association_weekday_confounded(
    entry_dates: Sequence[date_type],
    metric_values: Sequence[float],
    predictor_values: Sequence[float],
    *,
    raw_coefficient: float,
    raw_p_value: float,
    min_effect: float = DEFAULT_MIN_EFFECT,
    alpha: float = DEFAULT_ALPHA,
) -> bool:
    """Return True when a raw continuous↔continuous association (e.g. sleep↔mood,
    #172) is explained by weekday effects after OLS adjustment."""

    if raw_p_value >= alpha or abs(raw_coefficient) < min_effect:
        return False
    if len(entry_dates) < MIN_OLS_ROWS:
        return False
    if len(set(metric_values)) < 2 or len(set(predictor_values)) < 2:
        return False

    weekdays = [entry_date.weekday() for entry_date in entry_dates]
    if len(set(weekdays)) <= 1:
        return False

    predictor = _standardized(predictor_values)
    if predictor is None:
        return False

    y = np.asarray(metric_values, dtype=float)
    weekday_matrix = _weekday_dummy_matrix(weekdays)
    design = sm.add_constant(np.column_stack([predictor, weekday_matrix]), has_constant="add")

    try:
        result = sm.OLS(y, design).fit(
            cov_type="HAC",
            cov_kwds={"maxlags": _hac_maxlags(len(y))},
        )
    except (ValueError, np.linalg.LinAlgError):
        return False

    adjusted_coef = _finite_float(result.params[1])
    adjusted_p = _finite_float(result.pvalues[1])
    if adjusted_coef is None or adjusted_p is None:
        return False
    return adjusted_p >= alpha or abs(adjusted_coef) < min_effect


def is_continuous_association_calendar_context_confounded(
    entry_dates: Sequence[date_type],
    work_contexts: Sequence[str],
    metric_values: Sequence[float],
    predictor_values: Sequence[float],
    *,
    raw_coefficient: float,
    raw_p_value: float,
    min_effect: float = DEFAULT_MIN_EFFECT,
    alpha: float = DEFAULT_ALPHA,
) -> bool:
    """Return True when weekday/work-context controls explain a raw continuous
    association (e.g. sleep↔mood, #172)."""

    if raw_p_value >= alpha or abs(raw_coefficient) < min_effect:
        return False
    if len(entry_dates) < MIN_CONTEXT_OLS_ROWS:
        return False
    if len(entry_dates) != len(work_contexts):
        return False
    if len(set(metric_values)) < 2 or len(set(predictor_values)) < 2:
        return False
    if len(set(work_contexts)) < 2:
        return False

    predictor = _standardized(predictor_values)
    if predictor is None:
        return False

    y = np.asarray(metric_values, dtype=float)
    weekdays = [entry_date.weekday() for entry_date in entry_dates]
    design = sm.add_constant(
        np.column_stack(
            [
                predictor,
                _weekday_dummy_matrix(weekdays),
                _categorical_dummy_matrix(work_contexts),
            ]
        ),
        has_constant="add",
    )

    try:
        result = sm.OLS(y, design).fit(
            cov_type="HAC",
            cov_kwds={"maxlags": _hac_maxlags(len(y))},
        )
    except (ValueError, np.linalg.LinAlgError):
        return False

    adjusted_coef = _finite_float(result.params[1])
    adjusted_p = _finite_float(result.pvalues[1])
    if adjusted_coef is None or adjusted_p is None:
        return False
    return adjusted_p >= alpha or abs(adjusted_coef) < min_effect


def is_pair_cooccurrence_weekday_confounded(
    entry_dates: Sequence[date_type],
    symptom_present: Sequence[int],
    tag_present: Sequence[int],
    *,
    alpha: float = DEFAULT_ALPHA,
) -> bool:
    """Return True when co-occurrence is not significant after symptom, tag, and weekday controls."""

    if len(entry_dates) < MIN_OLS_ROWS:
        return False

    co_occurrence = np.asarray(
        [
            1.0 if symptom and tag else 0.0
            for symptom, tag in zip(symptom_present, tag_present, strict=True)
        ],
        dtype=float,
    )
    if co_occurrence.sum() < 3 or len(np.unique(co_occurrence)) < 2:
        return False

    symptom = np.asarray(symptom_present, dtype=float)
    tag = np.asarray(tag_present, dtype=float)
    co_weekdays = {
        entry_date.weekday()
        for entry_date, value in zip(entry_dates, co_occurrence, strict=True)
        if value > 0
    }
    if len(co_weekdays) <= 1:
        return True

    weekdays = [entry_date.weekday() for entry_date in entry_dates]
    weekday_matrix = _weekday_dummy_matrix(weekdays)
    design = sm.add_constant(
        np.column_stack([symptom, tag, weekday_matrix]),
        has_constant="add",
    )

    try:
        result = sm.OLS(co_occurrence, design).fit(
            cov_type="HAC",
            cov_kwds={"maxlags": _hac_maxlags(len(co_occurrence))},
        )
    except (ValueError, np.linalg.LinAlgError):
        return False

    symptom_p = _finite_float(result.pvalues[1])
    tag_p = _finite_float(result.pvalues[2])
    if symptom_p is None or tag_p is None:
        return False
    return symptom_p >= alpha and tag_p >= alpha


def is_pair_cooccurrence_calendar_context_confounded(
    entry_dates: Sequence[date_type],
    work_contexts: Sequence[str],
    symptom_present: Sequence[int],
    tag_present: Sequence[int],
    *,
    alpha: float = DEFAULT_ALPHA,
) -> bool:
    """Return True when co-occurrence is not significant after calendar/context controls."""

    if len(entry_dates) < MIN_CONTEXT_OLS_ROWS:
        return False
    if len(entry_dates) != len(work_contexts):
        return False
    if len(set(work_contexts)) < 2:
        return False

    co_occurrence = np.asarray(
        [
            1.0 if symptom and tag else 0.0
            for symptom, tag in zip(symptom_present, tag_present, strict=True)
        ],
        dtype=float,
    )
    if co_occurrence.sum() < 3 or len(np.unique(co_occurrence)) < 2:
        return False

    co_contexts = {
        context for context, value in zip(work_contexts, co_occurrence, strict=True) if value > 0
    }
    if len(co_contexts) <= 1:
        return True

    symptom = np.asarray(symptom_present, dtype=float)
    tag = np.asarray(tag_present, dtype=float)
    weekdays = [entry_date.weekday() for entry_date in entry_dates]
    design = sm.add_constant(
        np.column_stack(
            [
                symptom,
                tag,
                _weekday_dummy_matrix(weekdays),
                _categorical_dummy_matrix(work_contexts),
            ]
        ),
        has_constant="add",
    )

    try:
        result = sm.OLS(co_occurrence, design).fit(
            cov_type="HAC",
            cov_kwds={"maxlags": _hac_maxlags(len(co_occurrence))},
        )
    except (ValueError, np.linalg.LinAlgError):
        return False

    symptom_p = _finite_float(result.pvalues[1])
    tag_p = _finite_float(result.pvalues[2])
    if symptom_p is None or tag_p is None:
        return False
    return symptom_p >= alpha and tag_p >= alpha

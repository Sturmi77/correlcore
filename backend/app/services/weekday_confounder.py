"""OLS weekday confounder checks with Newey-West HAC standard errors (ADR-0016, #146)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date as date_type
from typing import Any

import numpy as np
import statsmodels.api as sm

DEFAULT_ALPHA = 0.10
DEFAULT_MIN_EFFECT = 0.25
MIN_OLS_ROWS = 10
MIN_CONTEXT_OLS_ROWS = 30


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

    if raw_p_value >= alpha or abs(raw_coefficient) < min_effect:
        return False
    if len(entry_dates) < MIN_OLS_ROWS:
        return False
    if len(set(metric_values)) < 2 or len(set(binary_signal)) < 2:
        return False

    weekdays = [entry_date.weekday() for entry_date in entry_dates]
    signal_weekdays = {
        weekday for weekday, present in zip(weekdays, binary_signal, strict=True) if present
    }
    if len(signal_weekdays) <= 1:
        return True

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
        return False

    adjusted_coef = _finite_float(result.params[1])
    adjusted_p = _finite_float(result.pvalues[1])
    if adjusted_coef is None or adjusted_p is None:
        return False
    return adjusted_p >= alpha or abs(adjusted_coef) < min_effect


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

    if raw_p_value >= alpha or abs(raw_coefficient) < min_effect:
        return False
    if len(entry_dates) < MIN_CONTEXT_OLS_ROWS:
        return False
    if len(entry_dates) != len(work_contexts):
        return False
    if len(set(metric_values)) < 2 or len(set(binary_signal)) < 2:
        return False
    if len(set(work_contexts)) < 2:
        return False

    signal_contexts = {
        context for context, present in zip(work_contexts, binary_signal, strict=True) if present
    }
    if len(signal_contexts) <= 1:
        return True

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
        return False

    adjusted_coef = _finite_float(result.params[1])
    adjusted_p = _finite_float(result.pvalues[1])
    if adjusted_coef is None or adjusted_p is None:
        return False
    return adjusted_p >= alpha or abs(adjusted_coef) < min_effect


def _standardized(values: Sequence[float]) -> np.ndarray | None:
    """Z-score a continuous predictor so its OLS coefficient is comparable to
    ``min_effect`` thresholds tuned for correlation-scale effect sizes."""

    array = np.asarray(values, dtype=float)
    std = array.std(ddof=0)
    if std == 0:
        return None
    return (array - array.mean()) / std


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

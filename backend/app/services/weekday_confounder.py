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

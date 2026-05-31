"""M7 multivariate analytics helpers for Lasso and lag analysis."""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date as date_type
from typing import Any, Literal

import pandas as pd
from scipy.stats import pearsonr
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests

MetricName = Literal["mood_score", "energy", "stress"]
FeatureKind = Literal["metric", "tag", "symptom"]

MIN_ML_ENTRIES = 90
MAX_LAG_DAYS = 7
MIN_BINARY_FEATURE_USAGES = 5
MIN_LAG_OBSERVATIONS = 10
MIN_ABS_LASSO_COEFFICIENT = 0.05
MIN_ABS_LAG_CORRELATION = 0.25
LAG_FDR_ALPHA = 0.10
TIMESERIES_SPLITS = 5

METRIC_TARGETS: tuple[MetricName, ...] = ("mood_score", "energy", "stress")


@dataclass(frozen=True)
class MultivariateEntry:
    """Daily analytics row consumed by M7 ML helpers."""

    entry_date: date_type
    mood_score: int
    energy: int
    stress: int
    tag_ids: frozenset[uuid.UUID]
    symptom_ids: frozenset[uuid.UUID]


@dataclass(frozen=True)
class FeatureMetadata:
    """Human-readable metadata for a design-matrix column."""

    kind: FeatureKind
    key: str
    label: str
    slug: str | None = None
    id: uuid.UUID | None = None


@dataclass(frozen=True)
class FeatureCoefficient:
    """A non-zero Lasso coefficient tied to its source feature."""

    feature: FeatureMetadata
    coefficient: float


@dataclass(frozen=True)
class LassoFinding:
    """Aggregated Lasso result for one metric target."""

    target: MetricName
    features: tuple[FeatureCoefficient, ...]
    cv_score: float
    alpha: float
    sample_n: int


@dataclass(frozen=True)
class LagFinding:
    """One lagged association that survived effect-size and FDR gates."""

    target: FeatureMetadata
    feature: FeatureMetadata
    lag_days: int
    correlation: float
    p_value: float
    p_corrected: float
    sample_n: int


def m7_time_series_split() -> TimeSeriesSplit:
    """Return the canonical M7 splitter from ADR-0016."""

    return TimeSeriesSplit(n_splits=TIMESERIES_SPLITS)


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _binary_column(kind: FeatureKind, item_id: uuid.UUID) -> str:
    return f"{kind}_{item_id.hex}"


def _metric_metadata(metric: MetricName) -> FeatureMetadata:
    return FeatureMetadata(kind="metric", key=metric, label=metric, slug=metric)


def build_design_matrix(
    entries: Sequence[MultivariateEntry],
    *,
    tags: Mapping[uuid.UUID, FeatureMetadata] | None = None,
    symptoms: Mapping[uuid.UUID, FeatureMetadata] | None = None,
    min_binary_feature_usages: int = MIN_BINARY_FEATURE_USAGES,
) -> tuple[pd.DataFrame, dict[str, FeatureMetadata]]:
    """Build the M7 design matrix with metric, tag, and symptom columns."""

    sorted_entries = sorted(entries, key=lambda entry: entry.entry_date)
    feature_meta: dict[str, FeatureMetadata] = {
        metric: _metric_metadata(metric) for metric in METRIC_TARGETS
    }
    tag_meta = tags or {}
    symptom_meta = symptoms or {}

    tag_counts = {
        tag_id: sum(1 for entry in sorted_entries if tag_id in entry.tag_ids) for tag_id in tag_meta
    }
    symptom_counts = {
        symptom_id: sum(1 for entry in sorted_entries if symptom_id in entry.symptom_ids)
        for symptom_id in symptom_meta
    }

    eligible_tags = {
        tag_id: count
        for tag_id, count in tag_counts.items()
        if count >= min_binary_feature_usages and len(sorted_entries) - count >= 2
    }
    eligible_symptoms = {
        symptom_id: count
        for symptom_id, count in symptom_counts.items()
        if count >= min_binary_feature_usages and len(sorted_entries) - count >= 2
    }

    for tag_id in eligible_tags:
        feature_meta[_binary_column("tag", tag_id)] = tag_meta[tag_id]
    for symptom_id in eligible_symptoms:
        feature_meta[_binary_column("symptom", symptom_id)] = symptom_meta[symptom_id]

    rows: list[dict[str, object]] = []
    for entry in sorted_entries:
        row: dict[str, object] = {
            "entry_date": entry.entry_date,
            "mood_score": entry.mood_score,
            "energy": entry.energy,
            "stress": entry.stress,
        }
        for tag_id in eligible_tags:
            row[_binary_column("tag", tag_id)] = 1 if tag_id in entry.tag_ids else 0
        for symptom_id in eligible_symptoms:
            row[_binary_column("symptom", symptom_id)] = 1 if symptom_id in entry.symptom_ids else 0
        rows.append(row)

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, feature_meta
    return frame.set_index("entry_date").sort_index(), feature_meta


def _usable_feature_columns(frame: pd.DataFrame, target: str) -> list[str]:
    return [
        column
        for column in frame.columns
        if column != target and frame[column].nunique(dropna=True) > 1
    ]


def run_lasso_models(
    frame: pd.DataFrame,
    feature_meta: Mapping[str, FeatureMetadata],
    *,
    min_entries: int = MIN_ML_ENTRIES,
    min_abs_coefficient: float = MIN_ABS_LASSO_COEFFICIENT,
) -> list[LassoFinding]:
    """Run deterministic LassoCV models for mood, energy, and stress targets."""

    if len(frame) < min_entries:
        return []

    findings: list[LassoFinding] = []
    splitter = m7_time_series_split()
    for target in METRIC_TARGETS:
        if target not in frame or frame[target].nunique(dropna=True) < 2:
            continue

        feature_columns = _usable_feature_columns(frame, target)
        if not feature_columns:
            continue

        model = make_pipeline(
            StandardScaler(),
            LassoCV(cv=splitter, random_state=0, max_iter=20_000),
        )
        x = frame[feature_columns]
        y = frame[target]
        model.fit(x, y)

        lasso = model.named_steps["lassocv"]
        coefficients = [
            FeatureCoefficient(
                feature=feature_meta[column],
                coefficient=round(float(coefficient), 4),
            )
            for column, coefficient in zip(feature_columns, lasso.coef_, strict=True)
            if abs(float(coefficient)) >= min_abs_coefficient
        ]
        coefficients.sort(
            key=lambda item: (-abs(item.coefficient), item.feature.kind, item.feature.key)
        )
        if not coefficients:
            continue

        score = _finite_float(model.score(x, y))
        alpha = _finite_float(lasso.alpha_)
        findings.append(
            LassoFinding(
                target=target,
                features=tuple(coefficients[:5]),
                cv_score=round(score or 0.0, 4),
                alpha=round(alpha or 0.0, 6),
                sample_n=len(frame),
            )
        )

    return findings


def build_lagged_frame(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    max_lag_days: int = MAX_LAG_DAYS,
) -> pd.DataFrame:
    """Construct lag features and drop causal warm-up rows after shifting."""

    lagged = frame.copy()
    for column in columns:
        for lag_days in range(1, max_lag_days + 1):
            lagged[f"{column}_lag{lag_days}"] = lagged[column].shift(lag_days)
    return lagged.dropna().copy()


def run_lag_analysis(
    frame: pd.DataFrame,
    feature_meta: Mapping[str, FeatureMetadata],
    *,
    max_lag_days: int = MAX_LAG_DAYS,
    min_observations: int = MIN_LAG_OBSERVATIONS,
    min_abs_correlation: float = MIN_ABS_LAG_CORRELATION,
    fdr_alpha: float = LAG_FDR_ALPHA,
) -> list[LagFinding]:
    """Compute lagged associations with BH correction across the full lag matrix."""

    if len(frame) < MIN_ML_ENTRIES:
        return []

    base_columns = [
        column for column in frame.columns if column in feature_meta and frame[column].nunique() > 1
    ]
    if len(base_columns) < 2:
        return []

    target_columns = [
        column for column in base_columns if feature_meta[column].kind in {"metric", "symptom"}
    ]

    lagged = build_lagged_frame(frame, base_columns, max_lag_days=max_lag_days)
    raw: list[tuple[str, str, int, float, float, int]] = []
    for target in target_columns:
        for feature in base_columns:
            if feature == target:
                continue
            for lag_days in range(1, max_lag_days + 1):
                lag_column = f"{feature}_lag{lag_days}"
                pair = lagged[[target, lag_column]].dropna()
                if len(pair) < min_observations:
                    continue
                if pair[target].nunique() < 2 or pair[lag_column].nunique() < 2:
                    continue
                result = pearsonr(pair[lag_column], pair[target])
                correlation = _finite_float(result.statistic)
                p_value = _finite_float(result.pvalue)
                if correlation is None or p_value is None:
                    continue
                raw.append((target, feature, lag_days, correlation, p_value, len(pair)))

    if not raw:
        return []

    _, p_corrected, _, _ = multipletests(
        [item[4] for item in raw],
        alpha=fdr_alpha,
        method="fdr_bh",
    )
    findings: list[LagFinding] = []
    for (target, feature, lag_days, correlation, p_value, sample_n), corrected in zip(
        raw,
        p_corrected,
        strict=True,
    ):
        corrected_float = float(corrected)
        if corrected_float > fdr_alpha or abs(correlation) < min_abs_correlation:
            continue
        findings.append(
            LagFinding(
                target=feature_meta[target],
                feature=feature_meta[feature],
                lag_days=lag_days,
                correlation=round(correlation, 4),
                p_value=round(p_value, 6),
                p_corrected=round(corrected_float, 6),
                sample_n=sample_n,
            )
        )

    findings.sort(
        key=lambda item: (
            item.target.kind != "metric",
            -abs(item.correlation),
            item.target.key,
            item.feature.key,
            item.lag_days,
        )
    )
    return findings[:10]

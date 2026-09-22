"""Versioned, family-specific evidence projected from stored insight payloads.

Stored JSON remains readable as-is. Invalid or incomplete historical payloads
produce no typed evidence instead of invented zeros or an API validation error.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AssociationEvidence(BaseModel):
    family: Literal["association"] = "association"
    version: Literal[1] = 1
    metric: str
    outcome: Literal["association", "null", "unknown"] = "unknown"
    with_n: int = Field(ge=1)
    without_n: int = Field(ge=1)
    with_mean_raw: float | None = None
    without_mean_raw: float | None = None
    with_mean_display: float | None = None
    without_mean_display: float | None = None
    with_distribution: list[int] | None = None
    without_distribution: list[int] | None = None
    with_good_count: int | None = None
    without_good_count: int | None = None
    raw_coefficient: float | None = None
    weekday_held_coefficient: float | None = None
    calendar_held_coefficient: float | None = None
    lag_days: int | None = None
    evidence_start: date | None = None
    evidence_end: date | None = None


class ChangepointEvidence(BaseModel):
    family: Literal["changepoint"] = "changepoint"
    version: Literal[1] = 1
    series: Literal["mood_score", "stress", "energy"]
    before_raw: float
    after_raw: float
    before_display: float
    after_display: float
    raw_direction: Literal["higher", "lower", "unchanged"]
    display_direction: Literal["higher", "lower", "unchanged"]
    boundary_before: date | None = None
    boundary_after: date | None = None


class BelastungEvidence(BaseModel):
    family: Literal["belastung"] = "belastung"
    version: Literal[1] = 1
    recent_n: int = Field(ge=1)
    prior_n: int = Field(ge=1)
    recent_start: date | None = None
    recent_end: date | None = None
    prior_start: date | None = None
    prior_end: date | None = None
    stress_recent_raw: float | None = None
    stress_prior_raw: float | None = None
    stress_recent_display: float | None = None
    stress_prior_display: float | None = None
    energy_recent_raw: float | None = None
    energy_prior_raw: float | None = None
    fatigue_recent: int | None = None
    fatigue_prior: int | None = None
    stress_up: bool = False
    energy_down: bool = False
    fatigue_up: bool = False
    joint_frequency_recent: int | None = None
    joint_frequency_prior: int | None = None


class LagEvidence(BaseModel):
    family: Literal["lag"] = "lag"
    version: Literal[1] = 1
    target_key: str
    feature_key: str
    lag_days: int = Field(ge=0)
    raw_coefficient: float | None = None
    corrected_p: float | None = None
    evidence_start: date | None = None
    evidence_end: date | None = None


InsightEvidence = Annotated[
    AssociationEvidence | ChangepointEvidence | BelastungEvidence | LagEvidence,
    Field(discriminator="family"),
]


def _number(value: object) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) else None


def _count(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _direction(before: float, after: float) -> Literal["higher", "lower", "unchanged"]:
    if after > before:
        return "higher"
    if after < before:
        return "lower"
    return "unchanged"


def _distribution(value: object, n: int) -> list[int] | None:
    if not isinstance(value, list) or len(value) != 5:
        return None
    counts = [_count(item) for item in value]
    if (
        any(item is None for item in counts)
        or sum(item for item in counts if item is not None) != n
    ):
        return None
    return [int(item) for item in counts if item is not None]


def _pair_key(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("key", "slug", "id"):
        part = value.get(key)
        if isinstance(part, str) and part:
            return part
    return None


def build_insight_evidence(
    insight_type: str, metric: str, payload: dict[str, object], effect_size: float | None
) -> InsightEvidence | None:
    """Compatibility adapter for new and historical persisted payload versions."""
    if insight_type in {"pointbiserial", "null_association", "symptom_mood_association"}:
        with_n = _count(payload.get("tagged_count"))
        if with_n is None:
            with_n = _count(payload.get("symptom_n"))
        without_n = _count(payload.get("untagged_count"))
        if without_n is None:
            without_n = _count(payload.get("comparison_n"))
        if not with_n or not without_n:
            return None
        with_mean = _number(payload.get("tagged_mood_avg"))
        if with_mean is None:
            with_mean = _number(payload.get("symptom_metric_avg"))
        without_mean = _number(payload.get("untagged_mood_avg"))
        if without_mean is None:
            without_mean = _number(payload.get("comparison_metric_avg"))
        raw_outcome = payload.get("outcome")
        outcome: Literal["association", "null", "unknown"] = "unknown"
        if raw_outcome == "association":
            outcome = "association"
        elif raw_outcome == "null":
            outcome = "null"
        with_good = _count(payload.get("with_good_count"))
        without_good = _count(payload.get("without_good_count"))
        return AssociationEvidence(
            metric=metric,
            with_n=with_n,
            without_n=without_n,
            outcome=outcome,
            with_mean_raw=with_mean,
            without_mean_raw=without_mean,
            with_mean_display=6 - with_mean
            if metric == "stress" and with_mean is not None
            else with_mean,
            without_mean_display=6 - without_mean
            if metric == "stress" and without_mean is not None
            else without_mean,
            with_distribution=_distribution(payload.get("with_distribution"), with_n),
            without_distribution=_distribution(payload.get("without_distribution"), without_n),
            with_good_count=with_good if with_good is not None and with_good <= with_n else None,
            without_good_count=without_good
            if without_good is not None and without_good <= without_n
            else None,
            raw_coefficient=_number(effect_size),
            weekday_held_coefficient=_number(payload.get("weekday_held_coefficient")),
            calendar_held_coefficient=_number(payload.get("calendar_held_coefficient")),
            evidence_start=_date(payload.get("evidence_start")),
            evidence_end=_date(payload.get("evidence_end")),
        )
    if insight_type == "changepoint":
        raw_series = payload.get("series")
        if raw_series not in {"mood_score", "stress", "energy"}:
            raw_series = {
                "mood_changepoint": "mood_score",
                "stress_changepoint": "stress",
                "energy_changepoint": "energy",
            }.get(metric)
        before = _number(payload.get("before_avg"))
        after = _number(payload.get("after_avg"))
        if raw_series not in {"mood_score", "stress", "energy"} or before is None or after is None:
            return None
        series: Literal["mood_score", "stress", "energy"] = (
            "stress"
            if raw_series == "stress"
            else "energy"
            if raw_series == "energy"
            else "mood_score"
        )
        before_display = 6 - before if series == "stress" else before
        after_display = 6 - after if series == "stress" else after
        return ChangepointEvidence(
            series=series,
            before_raw=before,
            after_raw=after,
            before_display=before_display,
            after_display=after_display,
            raw_direction=_direction(before, after),
            display_direction=_direction(before_display, after_display),
            boundary_before=_date(payload.get("changepoint_date")),
            boundary_after=_date(payload.get("shift_date")),
        )
    if insight_type == "belastung_pattern":
        recent_n = _count(payload.get("recent_n"))
        prior_n = _count(payload.get("prior_n"))
        if not recent_n or not prior_n:
            return None
        sr = _number(payload.get("stress_avg_recent"))
        sp = _number(payload.get("stress_avg_prior"))
        er = _number(payload.get("energy_avg_recent"))
        ep = _number(payload.get("energy_avg_prior"))
        fr = _count(payload.get("fatigue_days_recent"))
        fp = _count(payload.get("fatigue_days_prior"))
        recent_end = _date(payload.get("recent_end"))
        prior_end = _date(payload.get("prior_end"))
        return BelastungEvidence(
            recent_n=recent_n,
            prior_n=prior_n,
            recent_start=_date(payload.get("recent_start")),
            recent_end=recent_end,
            prior_start=_date(payload.get("prior_start")),
            prior_end=prior_end,
            stress_recent_raw=sr,
            stress_prior_raw=sp,
            stress_recent_display=6 - sr if sr is not None else None,
            stress_prior_display=6 - sp if sp is not None else None,
            energy_recent_raw=er,
            energy_prior_raw=ep,
            fatigue_recent=fr,
            fatigue_prior=fp,
            stress_up=sr is not None and sp is not None and sr >= sp + 0.25,
            energy_down=er is not None and ep is not None and er <= ep - 0.25,
            fatigue_up=fr is not None and fp is not None and fr / recent_n > fp / prior_n,
        )
    if insight_type == "symptom_cluster" and payload.get("method") == "lag":
        target = _pair_key(payload.get("target"))
        feature = _pair_key(payload.get("feature"))
        lag_days = _count(payload.get("lag_days"))
        if target is None or feature is None or lag_days is None:
            return None
        return LagEvidence(
            target_key=target,
            feature_key=feature,
            lag_days=lag_days,
            raw_coefficient=_number(effect_size),
            corrected_p=_number(payload.get("p_value_corrected")),
            evidence_start=_date(payload.get("evidence_start")),
            evidence_end=_date(payload.get("evidence_end")),
        )
    return None

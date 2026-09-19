"""Changepoint insight family: detect mean shifts in mood, stress, and energy.

Split out of ``insight_engine`` (#777). Detection lives in
:mod:`app.services.changepoint` (PELT). Phase 13 runs one PELT fit per series;
``MAX_CHANGEPOINTS`` is per series (not a global cap across mood/stress/energy).
Multiplicity is controlled by penalty + per-series max — PELT has no p-value / FDR.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type

from app.models.insight import InsightTier, InsightType
from app.services.changepoint import detect_changepoints, strongest_changepoint_index
from app.services.insights.shared import (
    AnalyticsEntry,
    InsightCandidate,
    MetricName,
    _base_flags,
    _confidence,
    _direction,
    _metric_value,
)

# (series key, insight metric id, English noun for statement)
_CHANGEPOINT_SERIES: tuple[tuple[MetricName, str, str], ...] = (
    ("mood_score", "mood_changepoint", "mood"),
    ("stress", "stress_changepoint", "stress"),
    ("energy", "energy_changepoint", "energy"),
)


def _iso(day: date_type) -> str:
    return day.isoformat()


def _candidate_for_series(
    entries: Sequence[AnalyticsEntry],
    *,
    series: MetricName,
    metric: str,
    series_label: str,
    tier: InsightTier,
    generated_for_date: date_type,
) -> InsightCandidate | None:
    values = [float(_metric_value(entry, series)) for entry in entries]
    changepoints = detect_changepoints(values)
    if not changepoints:
        return None

    index = strongest_changepoint_index(values, changepoints)
    if index is None or index < 0 or index >= len(entries) - 1:
        return None

    before = values[: index + 1]
    after = values[index + 1 :]
    if not before or not after:
        return None

    before_avg = sum(before) / len(before)
    after_avg = sum(after) / len(after)
    delta = after_avg - before_avg
    direction = _direction(delta, "higher", "lower")
    changepoint_date = entries[index].entry_date
    shift_date = entries[index + 1].entry_date
    changepoint_dates = [
        _iso(entries[cp].entry_date) for cp in changepoints if 0 <= cp < len(entries)
    ]
    statement = (
        f"Your {series_label} average shifted to {direction} levels around "
        f"{_iso(changepoint_date)} (shift from {_iso(shift_date)})."
    )
    effect_size = round(delta, 4)
    return InsightCandidate(
        insight_type=InsightType.CHANGEPOINT,
        tier=tier,
        metric=metric,
        subject_type="changepoint",
        subject_id=None,
        subject_label=_iso(changepoint_date),
        effect_size=effect_size,
        confidence=_confidence(effect_size, None, tier),
        sample_n=len(values),
        statement=statement,
        flags={
            **_base_flags(p_value=None, method="pelt_rbf"),
            "changepoint_index": index,
            "series": series,
        },
        payload={
            "series": series,
            "changepoint_index": index,
            "changepoint_date": _iso(changepoint_date),
            "shift_date": _iso(shift_date),
            "changepoint_dates": changepoint_dates,
            "before_avg": round(before_avg, 2),
            "after_avg": round(after_avg, 2),
            "changepoints": list(changepoints),
        },
        generated_for_date=generated_for_date,
    )


def _changepoint_candidates(
    entries: Sequence[AnalyticsEntry],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    """Emit at most one strongest changepoint insight per metric series."""

    if len(entries) < 2:
        return []

    candidates: list[InsightCandidate] = []
    for series, metric, series_label in _CHANGEPOINT_SERIES:
        candidate = _candidate_for_series(
            entries,
            series=series,
            metric=metric,
            series_label=series_label,
            tier=tier,
            generated_for_date=generated_for_date,
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates

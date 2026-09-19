"""Changepoint insight family: detect a shift in the mood mean over history.

Split out of ``insight_engine`` (#777); behavior is unchanged. The detection
itself lives in :mod:`app.services.changepoint`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type
from typing import Any

from app.models.insight import InsightTier, InsightType
from app.services.changepoint import detect_changepoints, strongest_changepoint_index
from app.services.insights.shared import (
    AnalyticsEntry,
    InsightCandidate,
    _base_flags,
    _confidence,
    _direction,
)


def _iso_date_at(entries: Sequence[AnalyticsEntry], index: int) -> str | None:
    """Return ``entry_date`` as ISO-8601, or ``None`` when the index is out of range."""

    if index < 0 or index >= len(entries):
        return None
    return entries[index].entry_date.isoformat()


def _resolve_changepoint_dates(
    entries: Sequence[AnalyticsEntry],
    index: int,
) -> dict[str, Any] | None:
    """Map a PELT index to the before/after boundary dates.

    ``detect_changepoints`` returns zero-based indices immediately *before* a
    shift: the change sits between ``entries[index]`` and ``entries[index + 1]``.
    Returns ``None`` when either side is missing (edge of the series).
    """

    changepoint_date = _iso_date_at(entries, index)
    shift_date = _iso_date_at(entries, index + 1)
    if changepoint_date is None or shift_date is None:
        return None
    return {
        "index": index,
        "changepoint_date": changepoint_date,
        "shift_date": shift_date,
    }


def _changepoint_candidates(
    entries: Sequence[AnalyticsEntry],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    moods = [entry.mood_score for entry in entries]
    changepoints = detect_changepoints(moods)
    if not changepoints:
        return []

    index = strongest_changepoint_index(moods, changepoints)
    if index is None:
        return []

    resolved = _resolve_changepoint_dates(entries, index)
    if resolved is None:
        # Primary index has no after-segment day (series edge) — skip cleanly.
        return []

    before = moods[: index + 1]
    after = moods[index + 1 :]
    before_avg = sum(before) / len(before)
    after_avg = sum(after) / len(after)
    delta = after_avg - before_avg
    direction = _direction(delta, "higher", "lower")
    changepoint_date = resolved["changepoint_date"]
    shift_date = resolved["shift_date"]
    statement = (
        f"Your mood average shifted to {direction} levels around {changepoint_date} "
        f"(from {shift_date})."
    )
    effect_size = round(delta, 4)
    changepoint_dates = [
        date_pair
        for cp_index in changepoints
        if (date_pair := _resolve_changepoint_dates(entries, cp_index)) is not None
    ]
    return [
        InsightCandidate(
            insight_type=InsightType.CHANGEPOINT,
            tier=tier,
            metric="mood_changepoint",
            subject_type="changepoint",
            subject_id=None,
            subject_label=changepoint_date,
            effect_size=effect_size,
            confidence=_confidence(effect_size, None, tier),
            sample_n=len(moods),
            statement=statement,
            flags={
                **_base_flags(p_value=None, method="pelt_rbf"),
                "changepoint_index": index,
            },
            payload={
                "changepoint_index": index,
                "changepoint_date": changepoint_date,
                "shift_date": shift_date,
                "before_avg": round(before_avg, 2),
                "after_avg": round(after_avg, 2),
                "changepoints": changepoints,
                "changepoint_dates": changepoint_dates,
            },
            generated_for_date=generated_for_date,
        )
    ]

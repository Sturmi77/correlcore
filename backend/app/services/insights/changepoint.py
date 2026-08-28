"""Changepoint insight family: detect a shift in the mood mean over history.

Split out of ``insight_engine`` (#777); behavior is unchanged. The detection
itself lives in :mod:`app.services.changepoint`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type

from app.models.insight import InsightTier, InsightType
from app.services.changepoint import detect_changepoints, strongest_changepoint_index
from app.services.insights.shared import (
    AnalyticsEntry,
    InsightCandidate,
    _base_flags,
    _confidence,
    _direction,
)


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

    before = moods[: index + 1]
    after = moods[index + 1 :]
    before_avg = sum(before) / len(before)
    after_avg = sum(after) / len(after)
    delta = after_avg - before_avg
    direction = _direction(delta, "higher", "lower")
    statement = (
        f"Your mood average shifted to {direction} levels around entry {index + 1} in your history."
    )
    effect_size = round(delta, 4)
    return [
        InsightCandidate(
            insight_type=InsightType.CHANGEPOINT,
            tier=tier,
            metric="mood_changepoint",
            subject_type="changepoint",
            subject_id=None,
            subject_label=f"entry_{index + 1}",
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
                "before_avg": round(before_avg, 2),
                "after_avg": round(after_avg, 2),
                "changepoints": changepoints,
            },
            generated_for_date=generated_for_date,
        )
    ]

"""Marker-based mood insight candidates (Notes in Analysis #198)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_type
from statistics import mean

from app.models.insight import InsightTier, InsightType

MIN_MARKER_INSIGHT_SAMPLE = 20
MIN_MARKER_MOOD_DELTA = 0.2


def _confidence_tier_for_sample(sample_n: int) -> InsightTier:
    if sample_n >= 30:
        return InsightTier.ROBUST
    if sample_n >= 15:
        return InsightTier.DEVELOPING
    if sample_n >= 8:
        return InsightTier.PRELIMINARY
    if sample_n >= 3:
        return InsightTier.EARLY
    return InsightTier.NONE


@dataclass(frozen=True)
class EntryWithMarkers:
    entry_id: uuid.UUID
    entry_date: date_type
    mood_score: int
    markers: frozenset[str]
    has_note: bool


def build_marker_mood_insights(
    entries_with_markers: Sequence[EntryWithMarkers],
    *,
    generated_for_date: date_type,
    time_window_days: int = 90,
) -> list:
    """Build note-marker mood association insights when sample gates pass."""
    from app.services.insight_engine import InsightCandidate

    noted = [row for row in entries_with_markers if row.has_note]
    if len(noted) < MIN_MARKER_INSIGHT_SAMPLE:
        return []

    baseline = mean(row.mood_score for row in noted)
    by_marker: dict[str, list[EntryWithMarkers]] = defaultdict(list)
    for row in noted:
        for marker in row.markers:
            by_marker[marker].append(row)

    candidates: list[InsightCandidate] = []
    for marker, rows in sorted(by_marker.items()):
        if len(rows) < MIN_MARKER_INSIGHT_SAMPLE:
            continue
        marker_avg = mean(row.mood_score for row in rows)
        delta = marker_avg - baseline
        if abs(delta) < MIN_MARKER_MOOD_DELTA:
            continue

        sample_n = len(rows)
        confidence = min(1.0, sample_n / 40) * min(1.0, abs(delta) / 2)
        tier = _confidence_tier_for_sample(sample_n)
        direction = "higher" if delta > 0 else "lower"
        statement = (
            f"On days marked “{marker}”, your mood averaged {abs(delta):.1f} points "
            f"{direction} than your note-day average."
        )
        example_ids = [row.entry_id for row in sorted(rows, key=lambda r: r.entry_date, reverse=True)[:5]]
        example_dates = [row.entry_date.isoformat() for row in sorted(rows, key=lambda r: r.entry_date, reverse=True)[:5]]

        candidates.append(
            InsightCandidate(
                insight_type=InsightType.NOTE_MARKER_MOOD,
                tier=tier,
                metric="mood_score",
                subject_type="note_marker",
                subject_id=None,
                subject_label=marker,
                effect_size=round(delta, 3),
                confidence=round(confidence, 3),
                sample_n=sample_n,
                statement=statement,
                flags={},
                payload={
                    "marker": marker,
                    "sample_size": sample_n,
                    "time_window": time_window_days,
                    "avg_delta": round(delta, 2),
                    "confidence": round(confidence, 2),
                    "example_entry_ids": [str(entry_id) for entry_id in example_ids],
                    "example_dates": example_dates,
                    "evidence": {
                        "marker": marker,
                        "sample_size": sample_n,
                        "time_window": time_window_days,
                        "avg_delta": round(delta, 2),
                        "confidence": round(confidence, 2),
                        "example_entry_ids": [str(entry_id) for entry_id in example_ids],
                    },
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates

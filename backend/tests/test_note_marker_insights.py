"""Tests for marker-based mood insight generation."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.services.note_marker_insights import EntryWithMarkers, build_marker_mood_insights


def _row(
    *,
    day: int,
    mood: int,
    markers: set[str],
    has_note: bool = True,
) -> EntryWithMarkers:
    return EntryWithMarkers(
        entry_id=uuid.uuid4(),
        entry_date=date(2026, 1, 1) + timedelta(days=day - 1),
        mood_score=mood,
        markers=frozenset(markers),
        has_note=has_note,
    )


def test_build_marker_mood_insights_requires_minimum_sample() -> None:
    rows = [_row(day=i, mood=3, markers={"stress"}) for i in range(1, 10)]
    assert build_marker_mood_insights(rows, generated_for_date=date(2026, 2, 1)) == []


def test_build_marker_mood_insights_emits_candidate_when_delta_large_enough() -> None:
    rows = [_row(day=i, mood=3, markers=set()) for i in range(1, 25)]
    rows.extend(_row(day=25 + i, mood=1, markers={"stress"}) for i in range(25))

    insights = build_marker_mood_insights(rows, generated_for_date=date(2026, 2, 1))
    assert len(insights) == 1
    insight = insights[0]
    assert insight.metric == "mood_score"
    assert insight.sample_n >= 20
    assert insight.payload["marker"] == "stress"
    assert insight.payload["evidence"]["sample_size"] >= 20

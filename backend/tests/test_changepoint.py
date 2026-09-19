from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.core.config import settings
from app.models.entry import WorkContext
from app.models.insight import InsightType
from app.services.changepoint import detect_changepoints, strongest_changepoint_index
from app.services.insights.changepoint import _changepoint_candidates
from app.services.insights.shared import AnalyticsEntry, InsightTier


def _entry(day: date, *, mood: int, energy: int = 3, stress: int = 3) -> AnalyticsEntry:
    return AnalyticsEntry(
        id=uuid.uuid4(),
        entry_date=day,
        mood_score=mood,
        energy=energy,
        stress=stress,
        work_context=WorkContext.HOMEOFFICE,
        tag_ids=frozenset(),
        symptom_ids=frozenset(),
    )


def test_detect_changepoints_flat_series_returns_empty() -> None:
    series = [3.0] * 80
    assert detect_changepoints(series) == []


def test_detect_changepoints_step_change_finds_one_near_index() -> None:
    series = [2.0] * 40 + [4.5] * 40
    changepoints = detect_changepoints(series)
    assert len(changepoints) >= 1
    index = strongest_changepoint_index(series, changepoints)
    assert index is not None
    assert 35 <= index <= 45


def test_detect_changepoints_respects_min_entries_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ANALYTICS_MIN_ENTRIES_CHANGEPOINT", 100)
    series = [2.0] * 40 + [4.0] * 40
    assert detect_changepoints(series) == []


def test_changepoint_candidates_emit_mood_stress_energy_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ANALYTICS_MIN_ENTRIES_CHANGEPOINT", 60)
    start = date(2026, 1, 1)
    entries = []
    for offset in range(80):
        # Mood steps at 40; stress steps at 40; energy stays flat.
        mood = 2 if offset < 40 else 5
        stress = 2 if offset < 40 else 5
        energy = 3
        entries.append(_entry(start + timedelta(days=offset), mood=mood, energy=energy, stress=stress))

    candidates = _changepoint_candidates(
        entries,
        tier=InsightTier.ROBUST,
        generated_for_date=date(2026, 4, 1),
    )
    metrics = {candidate.metric for candidate in candidates}
    assert "mood_changepoint" in metrics
    assert "stress_changepoint" in metrics
    assert "energy_changepoint" not in metrics

    mood = next(c for c in candidates if c.metric == "mood_changepoint")
    assert mood.insight_type == InsightType.CHANGEPOINT
    assert mood.payload["series"] == "mood_score"
    assert "changepoint_date" in mood.payload
    assert "shift_date" in mood.payload
    assert mood.payload["changepoint_date"] < mood.payload["shift_date"]
    assert mood.subject_label == mood.payload["changepoint_date"]
    assert mood.payload["changepoint_date"] in mood.statement


def test_changepoint_candidates_map_index_to_entry_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ANALYTICS_MIN_ENTRIES_CHANGEPOINT", 60)
    start = date(2026, 1, 1)
    # Non-contiguous calendar (weekdays only) — index still maps to entry_date.
    entries = []
    cursor = start
    for offset in range(80):
        while cursor.weekday() >= 5:
            cursor += timedelta(days=1)
        mood = 2 if offset < 40 else 5
        entries.append(_entry(cursor, mood=mood))
        cursor += timedelta(days=1)

    candidates = _changepoint_candidates(
        entries,
        tier=InsightTier.ROBUST,
        generated_for_date=date(2026, 6, 1),
    )
    mood = next(c for c in candidates if c.metric == "mood_changepoint")
    index = int(mood.payload["changepoint_index"])
    assert mood.payload["changepoint_date"] == entries[index].entry_date.isoformat()
    assert mood.payload["shift_date"] == entries[index + 1].entry_date.isoformat()
    assert len(mood.payload["changepoint_dates"]) == len(mood.payload["changepoints"])


def test_changepoint_candidates_empty_when_below_min_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ANALYTICS_MIN_ENTRIES_CHANGEPOINT", 60)
    start = date(2026, 1, 1)
    entries = [
        _entry(start + timedelta(days=offset), mood=2 if offset < 20 else 5)
        for offset in range(40)
    ]
    assert (
        _changepoint_candidates(
            entries,
            tier=InsightTier.ROBUST,
            generated_for_date=date(2026, 3, 1),
        )
        == []
    )

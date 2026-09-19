from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.core.config import settings
from app.models.insight import InsightTier
from app.services.changepoint import detect_changepoints, strongest_changepoint_index
from app.services.insights.changepoint import (
    _changepoint_candidates,
    _resolve_changepoint_dates,
)
from app.services.insights.shared import AnalyticsEntry


def _entry(day: date, mood: int = 3) -> AnalyticsEntry:
    return AnalyticsEntry(
        id=uuid.uuid4(),
        entry_date=day,
        mood_score=mood,
        energy=3,
        stress=3,
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


def test_resolve_changepoint_dates_maps_index_across_gaps() -> None:
    """Indices address the deduped daily sequence, not calendar-day offsets."""

    start = date(2026, 1, 1)
    # Gaps of several days between entries — index still points at entry_date.
    entries = [
        _entry(start, mood=2),
        _entry(start + timedelta(days=3), mood=2),
        _entry(start + timedelta(days=10), mood=2),  # index 2 = last day of before
        _entry(start + timedelta(days=14), mood=5),  # index 3 = first day of after
        _entry(start + timedelta(days=20), mood=5),
    ]
    resolved = _resolve_changepoint_dates(entries, 2)
    assert resolved == {
        "index": 2,
        "changepoint_date": "2026-01-11",
        "shift_date": "2026-01-15",
    }


def test_resolve_changepoint_dates_edge_index_returns_none() -> None:
    entries = [_entry(date(2026, 1, 1) + timedelta(days=i)) for i in range(5)]
    # index + 1 is outside the series → no after-segment day
    assert _resolve_changepoint_dates(entries, 4) is None
    assert _resolve_changepoint_dates(entries, -1) is None
    assert _resolve_changepoint_dates(entries, 99) is None


def test_changepoint_candidates_empty_when_detector_finds_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = [_entry(date(2026, 1, 1) + timedelta(days=i)) for i in range(10)]
    monkeypatch.setattr(
        "app.services.insights.changepoint.detect_changepoints",
        lambda _moods: [],
    )
    assert (
        _changepoint_candidates(
            entries,
            tier=InsightTier.ROBUST,
            generated_for_date=date(2026, 1, 15),
        )
        == []
    )


def test_changepoint_candidates_empty_when_strongest_index_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = [_entry(date(2026, 1, 1) + timedelta(days=i)) for i in range(10)]
    monkeypatch.setattr(
        "app.services.insights.changepoint.detect_changepoints",
        lambda _moods: [0],
    )
    monkeypatch.setattr(
        "app.services.insights.changepoint.strongest_changepoint_index",
        lambda _moods, _cps: None,
    )
    assert (
        _changepoint_candidates(
            entries,
            tier=InsightTier.ROBUST,
            generated_for_date=date(2026, 1, 15),
        )
        == []
    )


def test_changepoint_candidates_payload_uses_iso_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    start = date(2026, 3, 1)
    entries = [
        _entry(start + timedelta(days=i * 2), mood=2 if i < 4 else 5) for i in range(8)
    ]
    # Force a known index without requiring a full PELT run / min-entry gate.
    monkeypatch.setattr(
        "app.services.insights.changepoint.detect_changepoints",
        lambda _moods: [3],
    )
    monkeypatch.setattr(
        "app.services.insights.changepoint.strongest_changepoint_index",
        lambda _moods, _cps: 3,
    )

    candidates = _changepoint_candidates(
        entries,
        tier=InsightTier.ROBUST,
        generated_for_date=date(2026, 4, 1),
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.subject_label == "2026-03-07"
    assert "2026-03-07" in candidate.statement
    assert "2026-03-09" in candidate.statement
    assert "entry_" not in candidate.statement
    assert candidate.payload["changepoint_index"] == 3
    assert candidate.payload["changepoint_date"] == "2026-03-07"
    assert candidate.payload["shift_date"] == "2026-03-09"
    assert candidate.payload["changepoint_dates"] == [
        {
            "index": 3,
            "changepoint_date": "2026-03-07",
            "shift_date": "2026-03-09",
        }
    ]


def test_changepoint_candidates_skips_when_shift_out_of_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = [_entry(date(2026, 1, 1) + timedelta(days=i), mood=3) for i in range(10)]
    monkeypatch.setattr(
        "app.services.insights.changepoint.detect_changepoints",
        lambda _moods: [9],
    )
    monkeypatch.setattr(
        "app.services.insights.changepoint.strongest_changepoint_index",
        lambda _moods, _cps: 9,
    )

    assert (
        _changepoint_candidates(
            entries,
            tier=InsightTier.ROBUST,
            generated_for_date=date(2026, 1, 15),
        )
        == []
    )


def test_changepoint_dates_omits_unresolvable_secondary_indices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    start = date(2026, 5, 1)
    entries = [_entry(start + timedelta(days=i), mood=2 if i < 5 else 4) for i in range(10)]
    # Primary is valid; trailing index at the series edge is dropped from dates.
    monkeypatch.setattr(
        "app.services.insights.changepoint.detect_changepoints",
        lambda _moods: [4, 9],
    )
    monkeypatch.setattr(
        "app.services.insights.changepoint.strongest_changepoint_index",
        lambda _moods, _cps: 4,
    )

    candidates = _changepoint_candidates(
        entries,
        tier=InsightTier.ROBUST,
        generated_for_date=date(2026, 6, 1),
    )
    assert len(candidates) == 1
    dates = candidates[0].payload["changepoint_dates"]
    assert dates == [
        {
            "index": 4,
            "changepoint_date": "2026-05-05",
            "shift_date": "2026-05-06",
        }
    ]

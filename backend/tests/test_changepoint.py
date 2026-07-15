from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.changepoint import detect_changepoints, strongest_changepoint_index


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

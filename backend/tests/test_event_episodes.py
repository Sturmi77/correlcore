"""Unit tests for episode collapse (#809 / ADR-0035 §6)."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.insight_service import collapse_presence_dates_to_episodes


def test_collapse_empty() -> None:
    assert collapse_presence_dates_to_episodes([]) == []


def test_collapse_single_day() -> None:
    assert collapse_presence_dates_to_episodes([date(2026, 7, 1)]) == [date(2026, 7, 1)]


def test_collapse_contiguous_run_to_one_onset() -> None:
    dates = [date(2026, 7, 3), date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 1)]
    assert collapse_presence_dates_to_episodes(dates) == [date(2026, 7, 1)]


def test_collapse_gap_starts_new_episode() -> None:
    dates = [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 5)]
    assert collapse_presence_dates_to_episodes(dates) == [
        date(2026, 7, 1),
        date(2026, 7, 5),
    ]


def test_collapse_one_day_hole_is_new_episode_by_default() -> None:
    # Diff of 2 calendar days (> min_gap_days=1) → separate episodes.
    assert collapse_presence_dates_to_episodes([date(2026, 7, 1), date(2026, 7, 3)]) == [
        date(2026, 7, 1),
        date(2026, 7, 3),
    ]


def test_collapse_wider_min_gap_keeps_hole_in_episode() -> None:
    assert collapse_presence_dates_to_episodes(
        [date(2026, 7, 1), date(2026, 7, 3)],
        min_gap_days=2,
    ) == [date(2026, 7, 1)]


def test_collapse_rejects_invalid_min_gap() -> None:
    with pytest.raises(ValueError, match="min_gap_days"):
        collapse_presence_dates_to_episodes([date(2026, 7, 1)], min_gap_days=0)

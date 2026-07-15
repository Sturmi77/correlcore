"""Mood changepoint detection via ruptures PELT (#149)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from app.core.config import settings

PENALTY = 3.0
MAX_CHANGEPOINTS = 3
MIN_SEGMENT_SIZE = 5


def detect_changepoints(series: Sequence[float]) -> list[int]:
    """Detect up to three changepoint indices in a mood time series.

    Returns zero-based indices immediately before a detected shift. Flat series
    should return an empty list.
    """

    min_entries = settings.ANALYTICS_MIN_ENTRIES_CHANGEPOINT
    if len(series) < min_entries:
        return []

    try:
        import ruptures as rpt
    except ImportError:  # pragma: no cover - analytics extra not installed
        return []

    signal = np.asarray(series, dtype=float).reshape(-1, 1)
    if signal.size < min_entries:
        return []

    algo = rpt.Pelt(model="rbf", min_size=MIN_SEGMENT_SIZE, jump=1).fit(signal)
    breakpoints = algo.predict(pen=PENALTY)
    changepoints = [index - 1 for index in breakpoints[:-1] if index > 0]
    return changepoints[:MAX_CHANGEPOINTS]


def strongest_changepoint_index(series: Sequence[float], changepoints: Sequence[int]) -> int | None:
    """Return the changepoint with the largest mean shift."""

    if not changepoints:
        return None

    values = list(series)
    best_index: int | None = None
    best_delta = 0.0
    for index in changepoints:
        if index <= 0 or index >= len(values) - 1:
            continue
        before = values[: index + 1]
        after = values[index + 1 :]
        if not before or not after:
            continue
        delta = abs(sum(after) / len(after) - sum(before) / len(before))
        if delta > best_delta:
            best_delta = delta
            best_index = index
    return best_index

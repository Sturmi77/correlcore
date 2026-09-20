"""Single source of truth for how a metric is read (#955).

Three questions get asked about a metric all over the codebase:

- is a **low** raw value the good one?
- what counts as a "good day"?
- which direction is an improvement?

Until #955 every call site answered them for itself, and the answers drifted.
``stress`` is the only inverted scale in the product — the API contract has
said so for a long time (``apps/web/src/lib/contracts/apiContract.ts``) — but
``>= 4`` was hardcoded in three separate payload builders, so a symptom that
went with *high* stress was reported as going with good days.

Anything that emits a good-day count, a histogram or a direction resolves it
here instead, and carries ``good_direction`` in its payload so the UI never has
to guess either.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

METRIC_SCALE_MIN = 1
METRIC_SCALE_MAX = 5

#: "Good" on a normal 1–5 scale: 4 or better.
GOOD_METRIC_THRESHOLD = 4
#: "Good" on an inverted scale: 2 or lower. Not ``6 - 4``; the cutoff is its own
#: product decision, and writing it out keeps that visible.
INVERTED_GOOD_METRIC_THRESHOLD = 2

GoodDirection = Literal["lte", "gte"]

#: Metrics whose raw scale runs the other way — a low value is the good day.
INVERTED_METRICS: frozenset[str] = frozenset({"stress"})


@dataclass(frozen=True)
class MetricSemantics:
    """How one metric is to be read."""

    key: str
    #: True when a lower raw value is the better one.
    invert: bool
    #: Comparator that makes a day "good": ``lte`` on inverted scales.
    good_direction: GoodDirection
    good_threshold: int
    scale_min: int
    scale_max: int


def metric_semantics(metric: str) -> MetricSemantics:
    """Resolve the reading rules for ``metric``.

    Unknown metrics fall back to the non-inverted 1–5 rules. That is the safe
    default for the scales this product uses; an inverted metric that forgets to
    register here would be caught by ``test_every_inverted_metric_is_declared``.
    """

    inverted = metric in INVERTED_METRICS
    return MetricSemantics(
        key=metric,
        invert=inverted,
        good_direction="lte" if inverted else "gte",
        good_threshold=INVERTED_GOOD_METRIC_THRESHOLD if inverted else GOOD_METRIC_THRESHOLD,
        scale_min=METRIC_SCALE_MIN,
        scale_max=METRIC_SCALE_MAX,
    )


def is_good_metric_value(metric: str, value: float | int) -> bool:
    """True when ``value`` is a good day for ``metric`` on its raw scale."""

    semantics = metric_semantics(metric)
    if semantics.good_direction == "lte":
        return float(value) <= semantics.good_threshold
    return float(value) >= semantics.good_threshold


def good_metric_count(metric: str, values: Sequence[float | int]) -> int:
    """Number of good days in ``values``, read on ``metric``'s own scale."""

    return sum(1 for value in values if is_good_metric_value(metric, value))


def metric_improved(metric: str, *, before: float, after: float) -> bool | None:
    """True when the move from ``before`` to ``after`` is an improvement.

    ``None`` when the two are equal, so callers can say "unchanged" rather than
    pick a direction. Comparing raw values without this is how a stress
    changepoint came to read "2.1 → 4.0 (higher)" while the plotted line — drawn
    on the inverted scale — moved down.
    """

    if after == before:
        return None
    return after < before if metric_semantics(metric).invert else after > before

"""Metric reading rules and the guardrail that keeps them in one place (#955)."""

from __future__ import annotations

import pytest

from app.services.metric_semantics import (
    GOOD_METRIC_THRESHOLD,
    INVERTED_GOOD_METRIC_THRESHOLD,
    INVERTED_METRICS,
    good_metric_count,
    is_good_metric_value,
    metric_improved,
    metric_semantics,
)


@pytest.mark.parametrize("metric", ["mood_score", "energy"])
def test_normal_scales_are_good_when_high(metric: str) -> None:
    semantics = metric_semantics(metric)
    assert semantics.invert is False
    assert semantics.good_direction == "gte"
    assert semantics.good_threshold == GOOD_METRIC_THRESHOLD
    assert is_good_metric_value(metric, 4) is True
    assert is_good_metric_value(metric, 3) is False


def test_stress_is_good_when_low() -> None:
    """The whole point: `>= 4` on stress counts the worst days as the best."""
    semantics = metric_semantics("stress")
    assert semantics.invert is True
    assert semantics.good_direction == "lte"
    assert semantics.good_threshold == INVERTED_GOOD_METRIC_THRESHOLD
    assert is_good_metric_value("stress", 2) is True
    assert is_good_metric_value("stress", 4) is False


def test_good_count_reads_each_metric_on_its_own_scale() -> None:
    values = [1, 2, 3, 4, 5]
    assert good_metric_count("mood_score", values) == 2  # 4, 5
    assert good_metric_count("stress", values) == 2  # 1, 2


def test_improvement_direction_follows_the_displayed_scale() -> None:
    # Mood up is better; stress up is worse even though the number grew.
    assert metric_improved("mood_score", before=2.0, after=4.0) is True
    assert metric_improved("stress", before=2.0, after=4.0) is False
    assert metric_improved("stress", before=4.0, after=2.0) is True
    assert metric_improved("mood_score", before=3.0, after=3.0) is None


def test_unknown_metric_falls_back_to_the_normal_scale() -> None:
    semantics = metric_semantics("sleep_quality")
    assert semantics.invert is False
    assert semantics.good_direction == "gte"


def test_stress_is_the_only_inverted_metric() -> None:
    """Pins the set. Adding one means auditing every payload that emits counts."""
    assert INVERTED_METRICS == frozenset({"stress"})


def test_every_payload_builder_ships_the_rule_with_its_counts() -> None:
    """Guardrail (#955): a good-day count must never travel without its comparator.

    This is the defect class that produced "good on 0 of N days", a stress rule
    rendered backwards on legacy rows, and same-situation frequencies counting
    the worst days as the best. Each was a payload that published a count and
    left the reader to guess the rule behind it.

    Any new `*_good_count` / `*_good` key has to ship a `good_direction` (or a
    prefixed variant) in the same dict, or this fails.
    """
    from app.services.insights.shared import _with_without_distribution_payload
    from app.services.weekday_confounder import (
        SameSituationFrequencies,
        situation_adjustment_payload,
    )

    payloads: dict[str, dict[str, object]] = {}

    for metric in ("mood_score", "stress"):
        payloads[f"with_without[{metric}]"] = _with_without_distribution_payload(
            [1, 2, 4, 5], [2, 3, 3, 4], metric=metric
        )

    from app.services.weekday_confounder import MetricAdjustmentResult

    neutral = MetricAdjustmentResult(False, 0.3, 0.02, 40)
    for metric in ("mood_score", "stress"):
        payloads[f"situation[{metric}]"] = situation_adjustment_payload(
            weekday=neutral,
            calendar=neutral,
            situation=SameSituationFrequencies(
                context="office", with_n=10, without_n=10, with_good=4, without_good=2
            ),
            primary_confounder=None,
            metric=metric,
        )

    for name, payload in payloads.items():
        count_keys = [
            key for key in payload if key.endswith("_good_count") or key.endswith("_good")
        ]
        if not count_keys:
            continue
        direction_keys = [key for key in payload if key.endswith("good_direction")]
        assert direction_keys, (
            f"{name} publishes {count_keys} without a good_direction — the reader "
            f"cannot tell whether 'good' means high or low"
        )
        for key in direction_keys:
            assert payload[key] in {"lte", "gte"}, f"{name}.{key} = {payload[key]!r}"

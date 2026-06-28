"""Tests for the deterministic M7 QA seed day planner."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.services.m7_qa_seed_service import M7_QA_DEFAULT_DAYS, build_m7_qa_day_plans
from app.services.multivariate_analytics import MIN_ML_ENTRIES

_EXPECTED_TAG_SLUGS = frozenset(
    {
        "sport",
        "running",
        "meditation",
        "yoga",
        "alcohol",
        "caffeine_high",
        "family",
        "reading",
    }
)


def test_build_m7_qa_day_plans_requires_minimum_entry_count() -> None:
    with pytest.raises(ValueError, match=str(MIN_ML_ENTRIES)):
        build_m7_qa_day_plans(end_date=date(2026, 6, 28), day_count=MIN_ML_ENTRIES - 1)


def test_build_m7_qa_day_plans_is_deterministic() -> None:
    end = date(2026, 6, 28)
    first = build_m7_qa_day_plans(end_date=end, day_count=M7_QA_DEFAULT_DAYS)
    second = build_m7_qa_day_plans(end_date=end, day_count=M7_QA_DEFAULT_DAYS)

    assert first == second
    assert len(first) == M7_QA_DEFAULT_DAYS
    assert first[0].entry_date == end - timedelta(days=M7_QA_DEFAULT_DAYS - 1)
    assert first[-1].entry_date == end


def test_build_m7_qa_day_plans_embeds_symptom_and_tag_signals() -> None:
    plans = build_m7_qa_day_plans(end_date=date(2026, 6, 28), day_count=M7_QA_DEFAULT_DAYS)

    headache_days = sum(1 for plan in plans if "headache" in plan.symptom_slugs)
    sport_days = sum(1 for plan in plans if "sport" in plan.tag_slugs)
    low_mood_with_headache = sum(
        1 for plan in plans if "headache" in plan.symptom_slugs and plan.mood_score <= 2
    )

    assert headache_days >= MIN_ML_ENTRIES // 3
    assert sport_days >= 20
    assert low_mood_with_headache == headache_days
    assert all(slug in _EXPECTED_TAG_SLUGS for plan in plans for slug in plan.tag_slugs)

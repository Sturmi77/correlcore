from __future__ import annotations

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.insight import InsightTier, InsightType
from app.services.insight_engine import (
    AnalyticsEntry,
    TagSnapshot,
    confidence_tier_for_sample,
    generate_and_store_insights,
    generate_insight_candidates,
)
from tests.conftest import make_entry, make_tag, make_user


def _scalar_result(values: list[object]) -> MagicMock:
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _row_result(values: list[tuple[object, ...]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values
    return result


def _entry(
    day: date,
    *,
    mood: int,
    energy: int,
    stress: int,
    tag_ids: frozenset[uuid.UUID] = frozenset(),
) -> AnalyticsEntry:
    return AnalyticsEntry(
        id=uuid.uuid4(),
        entry_date=day,
        mood_score=mood,
        energy=energy,
        stress=stress,
        tag_ids=tag_ids,
    )


def test_confidence_tier_boundaries_follow_m3_ladder() -> None:
    assert confidence_tier_for_sample(2) == InsightTier.NONE
    assert confidence_tier_for_sample(3) == InsightTier.EARLY
    assert confidence_tier_for_sample(8) == InsightTier.PRELIMINARY
    assert confidence_tier_for_sample(15) == InsightTier.DEVELOPING
    assert confidence_tier_for_sample(30) == InsightTier.ROBUST


def test_weekday_pattern_is_available_before_bivariate_correlation() -> None:
    monday = date(2026, 5, 4)
    entries = [
        _entry(monday + timedelta(days=offset), mood=mood, energy=3, stress=3)
        for offset, mood in enumerate([5, 3, 3, 3, 3, 3, 3])
    ]

    candidates = generate_insight_candidates(entries, as_of=date(2026, 5, 10))

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.insight_type == InsightType.WEEKDAY_PATTERN
    assert candidate.tier == InsightTier.EARLY
    assert candidate.subject_label == "Monday"
    assert candidate.flags["early_pattern"] is True


def test_bivariate_candidates_include_spearman_and_pointbiserial() -> None:
    sport_id = uuid.uuid4()
    sport = TagSnapshot(id=sport_id, label="Sport", slug="sport")
    start = date(2026, 4, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset % 2 == 0 else 2,
            energy=5 if offset % 2 == 0 else 2,
            stress=1 if offset % 2 == 0 else 5,
            tag_ids=frozenset({sport_id}) if offset % 2 == 0 else frozenset(),
        )
        for offset in range(30)
    ]

    candidates = generate_insight_candidates(entries, [sport], as_of=date(2026, 4, 30))

    by_type = {candidate.insight_type for candidate in candidates}
    assert InsightType.SPEARMAN in by_type
    assert InsightType.POINTBISERIAL in by_type
    assert all(candidate.tier == InsightTier.ROBUST for candidate in candidates)
    assert all(candidate.sample_n == 30 for candidate in candidates)
    assert all(candidate.confidence is not None for candidate in candidates)
    assert all("diagnoses" not in candidate.statement.lower() for candidate in candidates)
    tag_candidate = next(c for c in candidates if c.insight_type == InsightType.POINTBISERIAL)
    assert tag_candidate.subject_id == sport_id
    assert tag_candidate.payload["tagged_count"] == 15


def test_bivariate_candidates_wait_for_developing_sample_size() -> None:
    sport_id = uuid.uuid4()
    sport = TagSnapshot(id=sport_id, label="Sport", slug="sport")
    start = date(2026, 4, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset % 2 == 0 else 2,
            energy=5 if offset % 2 == 0 else 2,
            stress=1 if offset % 2 == 0 else 5,
            tag_ids=frozenset({sport_id}) if offset % 2 == 0 else frozenset(),
        )
        for offset in range(14)
    ]

    candidates = generate_insight_candidates(entries, [sport], as_of=date(2026, 4, 14))

    assert all(candidate.insight_type != InsightType.POINTBISERIAL for candidate in candidates)
    assert all(candidate.insight_type != InsightType.SPEARMAN for candidate in candidates)


@pytest.mark.asyncio
async def test_generate_and_store_insights_replaces_rows_for_day() -> None:
    user = make_user()
    sport = make_tag(user=None, is_default=True, slug="sport", name="Sport")
    start = date(2026, 4, 1)
    entries = [
        make_entry(
            user,
            entry_date=start + timedelta(days=offset),
            mood_score=5 if offset % 2 == 0 else 2,
            energy=5 if offset % 2 == 0 else 2,
            stress=1 if offset % 2 == 0 else 5,
        )
        for offset in range(30)
    ]
    tag_rows = [(entry.id, sport) for offset, entry in enumerate(entries) if offset % 2 == 0]
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[_scalar_result(entries), _row_result(tag_rows), MagicMock()]
    )
    db.flush = AsyncMock()

    stored = await generate_and_store_insights(db, user_id=user.id, as_of=date(2026, 4, 30))

    assert stored
    assert db.execute.await_count == 3
    delete_stmt = db.execute.await_args_list[2].args[0]
    assert "DELETE FROM insights" in str(delete_stmt)
    assert db.add.call_count == len(stored)
    assert db.flush.await_count == 1
    assert any(insight.insight_type == InsightType.POINTBISERIAL for insight in stored)
    assert all(insight.user_id == user.id for insight in stored)
    assert all(insight.generated_for_date == date(2026, 4, 30) for insight in stored)


def test_hidden_or_sparse_tag_groups_do_not_create_tag_insights() -> None:
    tag_id = uuid.uuid4()
    tag = TagSnapshot(id=tag_id, label="Focus", slug="focus")
    start = date(2026, 4, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset == 0 else 3,
            energy=3,
            stress=3,
            tag_ids=frozenset({tag_id}) if offset == 0 else frozenset(),
        )
        for offset in range(30)
    ]

    candidates = generate_insight_candidates(entries, [tag], as_of=date(2026, 4, 30))

    assert all(candidate.subject_id != tag_id for candidate in candidates)

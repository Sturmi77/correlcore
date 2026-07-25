from __future__ import annotations

import uuid
from datetime import date, timedelta
from random import Random
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.entry import WorkContext
from app.models.insight import InsightTier, InsightType
from app.services.insight_engine import (
    AnalyticsEntry,
    SymptomSnapshot,
    TagSnapshot,
    _acquire_insight_generation_lock,
    _canonicalize_tag_aliases,
    _dedupe_daily_entries,
    _insight_generation_lock_keys,
    confidence_tier_for_sample,
    display_metric_value,
    generate_and_store_insights,
    generate_insight_candidates,
    is_weekday_biased,
    is_work_context_biased,
    load_analytics_data,
)
from tests.conftest import make_entry, make_symptom, make_tag, make_user


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
    work_context: WorkContext = WorkContext.HOMEOFFICE,
    tag_ids: frozenset[uuid.UUID] = frozenset(),
    symptom_ids: frozenset[uuid.UUID] = frozenset(),
) -> AnalyticsEntry:
    return AnalyticsEntry(
        id=uuid.uuid4(),
        entry_date=day,
        mood_score=mood,
        energy=energy,
        stress=stress,
        work_context=work_context,
        tag_ids=tag_ids,
        symptom_ids=symptom_ids,
    )


def test_display_metric_value_inverts_stress_only() -> None:
    assert display_metric_value("mood_score", 3) == 3
    assert display_metric_value("energy", 5) == 5
    assert display_metric_value("stress", 1) == 5
    assert display_metric_value("stress", 5) == 1


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
    assert candidate.payload["weekday_mood_avgs"] == {
        "0": 5.0,
        "1": 3.0,
        "2": 3.0,
        "3": 3.0,
        "4": 3.0,
        "5": 3.0,
        "6": 3.0,
    }


def test_flat_mood_over_sixty_seven_days_yields_no_weekday_pattern() -> None:
    """ADR-0037: maturity can be robust while flat mood fails MIN_WEEKDAY_DELTA."""
    start = date(2026, 1, 5)  # Monday
    entries = [
        _entry(start + timedelta(days=offset), mood=3, energy=3, stress=3) for offset in range(67)
    ]

    candidates = generate_insight_candidates(entries, as_of=start + timedelta(days=67))

    assert all(candidate.insight_type != InsightType.WEEKDAY_PATTERN for candidate in candidates)
    assert candidates == []


def test_work_context_pattern_is_available_after_seven_entries() -> None:
    start = date(2026, 5, 4)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset in {0, 2} else 3,
            energy=3,
            stress=3,
            work_context=WorkContext.OFFICE if offset in {0, 2} else WorkContext.HOMEOFFICE,
        )
        for offset in range(7)
    ]

    candidates = generate_insight_candidates(entries, as_of=date(2026, 5, 11))
    candidate = next(c for c in candidates if c.insight_type == InsightType.WORK_CONTEXT_PATTERN)

    assert candidate.tier == InsightTier.EARLY
    assert candidate.subject_label == "Office"
    assert candidate.flags["early_pattern"] is True
    assert candidate.payload["work_context"] == "office"
    assert candidate.payload["context_entry_count"] == 2
    assert candidate.payload["comparison_entry_count"] == 5
    assert candidate.payload["work_context_entry_counts"] == {
        "homeoffice": 5,
        "office": 2,
    }


def test_context_patterns_wait_for_seven_entries() -> None:
    start = date(2026, 5, 4)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset < 2 else 3,
            energy=3,
            stress=3,
            work_context=WorkContext.OFFICE if offset < 2 else WorkContext.HOMEOFFICE,
        )
        for offset in range(6)
    ]

    candidates = generate_insight_candidates(entries, as_of=date(2026, 5, 10))

    assert all(
        candidate.insight_type != InsightType.WORK_CONTEXT_PATTERN for candidate in candidates
    )
    assert all(
        candidate.insight_type != InsightType.WEEKDAY_CONTEXT_PATTERN for candidate in candidates
    )


def test_work_context_pattern_skips_rare_contexts() -> None:
    start = date(2026, 5, 4)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset == 0 else 3,
            energy=3,
            stress=3,
            work_context=WorkContext.OFFICE if offset == 0 else WorkContext.HOMEOFFICE,
        )
        for offset in range(7)
    ]

    candidates = generate_insight_candidates(entries, as_of=date(2026, 5, 11))

    assert all(
        candidate.insight_type != InsightType.WORK_CONTEXT_PATTERN for candidate in candidates
    )


def test_weekday_context_pattern_requires_sufficient_cell_size() -> None:
    start = date(2026, 5, 4)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset in {0, 7} else 3,
            energy=3,
            stress=3,
            work_context=WorkContext.OFFICE if offset in {0, 7} else WorkContext.HOMEOFFICE,
        )
        for offset in range(14)
    ]

    candidates = generate_insight_candidates(entries, as_of=date(2026, 5, 18))
    candidate = next(c for c in candidates if c.insight_type == InsightType.WEEKDAY_CONTEXT_PATTERN)

    assert candidate.subject_label == "Mondays in Office"
    assert candidate.payload["weekday"] == 0
    assert candidate.payload["work_context"] == "office"
    assert candidate.payload["cell_entry_count"] == 2
    assert candidate.payload["comparison_entry_count"] == 12


def test_weekday_context_pattern_skips_single_entry_cells() -> None:
    start = date(2026, 5, 4)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset in {0, 1} else 3,
            energy=3,
            stress=3,
            work_context=WorkContext.OFFICE if offset in {0, 1} else WorkContext.HOMEOFFICE,
        )
        for offset in range(14)
    ]

    candidates = generate_insight_candidates(entries, as_of=date(2026, 5, 18))

    assert all(
        candidate.insight_type != InsightType.WEEKDAY_CONTEXT_PATTERN for candidate in candidates
    )


def test_daily_dedupe_preserves_work_context_from_first_slot() -> None:
    day = date(2026, 5, 4)
    entries = [
        _entry(day, mood=4, energy=3, stress=2, work_context=WorkContext.OFFICE),
        _entry(day, mood=2, energy=5, stress=4, work_context=WorkContext.HOMEOFFICE),
    ]

    daily = _dedupe_daily_entries(entries)

    assert len(daily) == 1
    assert daily[0].work_context is WorkContext.OFFICE
    assert daily[0].mood_score == 3


def test_tag_alias_canonicalization_preserves_work_context() -> None:
    default_id = uuid.uuid4()
    override_id = uuid.uuid4()
    default = TagSnapshot(id=default_id, label="Focus", slug="focus", is_default=True)
    override = TagSnapshot(id=override_id, label="Fokus", slug="focus", is_default=False)
    entry = _entry(
        date(2026, 5, 4),
        mood=4,
        energy=3,
        stress=2,
        work_context=WorkContext.TRAVEL,
        tag_ids=frozenset({default_id}),
    )

    entries, _ = _canonicalize_tag_aliases([entry], [default, override])

    assert entries[0].work_context is WorkContext.TRAVEL


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
    assert {"energy_mood", "stress_mood"} <= {
        candidate.metric
        for candidate in candidates
        if candidate.insight_type == InsightType.SPEARMAN
    }
    assert all(candidate.tier == InsightTier.ROBUST for candidate in candidates)
    assert all(candidate.sample_n == 30 for candidate in candidates)
    assert all(candidate.confidence is not None for candidate in candidates)
    assert all("diagnoses" not in candidate.statement.lower() for candidate in candidates)
    tag_candidate = next(c for c in candidates if c.insight_type == InsightType.POINTBISERIAL)
    assert tag_candidate.subject_id == sport_id
    assert tag_candidate.payload["tag_slug"] == "sport"
    assert tag_candidate.payload["tagged_count"] == 15


def test_pointbiserial_marks_work_context_confounder() -> None:
    tag_id = uuid.uuid4()
    tag = TagSnapshot(id=tag_id, label="Office-heavy", slug="office_heavy")
    start = date(2026, 4, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset < 10 else 2,
            energy=3,
            stress=3,
            work_context=WorkContext.OFFICE if offset < 10 else WorkContext.HOMEOFFICE,
            tag_ids=frozenset({tag_id}) if offset < 10 else frozenset(),
        )
        for offset in range(30)
    ]

    candidates = generate_insight_candidates(entries, [tag], as_of=date(2026, 5, 1))
    candidate = next(c for c in candidates if c.insight_type == InsightType.POINTBISERIAL)

    assert candidate.flags["weekday_confounded"] is False
    assert candidate.flags["work_context_confounded"] is True
    assert candidate.flags["calendar_context_confounded"] is True
    assert candidate.payload["confounder"] == "work_context"
    assert candidate.payload["confounders"] == ["work_context"]
    assert "work contexts" in candidate.statement


def test_work_context_biased_uses_available_context_day_baseline() -> None:
    tag_id = uuid.uuid4()
    start = date(2026, 1, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=3,
            energy=3,
            stress=3,
            tag_ids=frozenset({tag_id}) if offset < 20 or 25 <= offset < 29 else frozenset(),
            work_context=WorkContext.OFFICE if offset < 25 else WorkContext.HOMEOFFICE,
        )
        for offset in range(30)
    ]

    assert is_work_context_biased(entries, tag_id) is False


def test_pointbiserial_collapses_default_and_override_with_same_slug() -> None:
    default_id = uuid.uuid4()
    override_id = uuid.uuid4()
    default = TagSnapshot(id=default_id, label="Alcohol", slug="alcohol", is_default=True)
    override = TagSnapshot(id=override_id, label="Alkohol", slug="alcohol", is_default=False)
    start = date(2026, 4, 1)
    entries: list[AnalyticsEntry] = []
    for offset in range(30):
        tag_ids = frozenset()
        if offset < 8:
            tag_ids = frozenset({default_id})
        elif offset < 15:
            tag_ids = frozenset({override_id})
        entries.append(
            _entry(
                start + timedelta(days=offset),
                mood=5 if tag_ids else 2,
                energy=3,
                stress=3,
                tag_ids=tag_ids,
            )
        )

    candidates = generate_insight_candidates(entries, [default, override], as_of=date(2026, 4, 30))
    tag_candidates = [c for c in candidates if c.insight_type == InsightType.POINTBISERIAL]

    assert len(tag_candidates) == 1
    candidate = tag_candidates[0]
    assert candidate.subject_id == override_id
    assert candidate.subject_label == "Alkohol"
    assert candidate.payload["tag_slug"] == "alcohol"
    assert candidate.payload["tagged_count"] == 15


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


def test_pointbiserial_uses_fdr_correction_for_many_random_tags() -> None:
    rng = Random(42)
    start = date(2026, 4, 1)
    tag_ids = [uuid.uuid4() for _ in range(40)]
    tags = [
        TagSnapshot(id=tag_id, label=f"Tag {idx}", slug=f"tag_{idx}")
        for idx, tag_id in enumerate(tag_ids)
    ]
    entries: list[AnalyticsEntry] = []
    for offset in range(60):
        assigned = {tag_id for tag_id in tag_ids if rng.random() < 0.35}
        entries.append(
            _entry(
                start + timedelta(days=offset),
                mood=rng.randint(1, 5),
                energy=rng.randint(1, 5),
                stress=rng.randint(1, 5),
                tag_ids=frozenset(assigned),
            )
        )

    candidates = generate_insight_candidates(entries, tags, as_of=date(2026, 5, 31))
    tag_candidates = [c for c in candidates if c.insight_type == InsightType.POINTBISERIAL]

    assert len(tag_candidates) < 5
    assert all(c.flags["multiple_testing_correction"] == "fdr_bh" for c in tag_candidates)


def test_pairwise_min_tag_usages_skip_rare_tags() -> None:
    tag_id = uuid.uuid4()
    tag = TagSnapshot(id=tag_id, label="Rare tag", slug="rare")
    start = date(2026, 4, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=5 if offset < 3 else 2,
            energy=3,
            stress=3,
            tag_ids=frozenset({tag_id}) if offset < 3 else frozenset(),
        )
        for offset in range(30)
    ]

    candidates = generate_insight_candidates(entries, [tag], as_of=date(2026, 4, 30))

    assert all(candidate.subject_id != tag_id for candidate in candidates)


def test_weekday_biased_detects_tag_concentrated_on_one_weekday() -> None:
    tag_id = uuid.uuid4()
    start = date(2026, 4, 4)  # Saturday
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=3,
            energy=3,
            stress=3,
            tag_ids=frozenset({tag_id}) if offset % 7 == 0 else frozenset(),
        )
        for offset in range(70)
    ]

    assert is_weekday_biased(entries, tag_id) is True


def test_insight_generation_lock_keys_are_stable_per_user() -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    assert _insight_generation_lock_keys(user_a) == _insight_generation_lock_keys(user_a)
    assert _insight_generation_lock_keys(user_a) != _insight_generation_lock_keys(user_b)


@pytest.mark.asyncio
async def test_acquire_insight_generation_lock_uses_transaction_advisory_lock() -> None:
    user_id = uuid.uuid4()
    ns, key = _insight_generation_lock_keys(user_id)
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())

    await _acquire_insight_generation_lock(db, user_id=user_id)

    stmt = db.execute.await_args.args[0]
    params = db.execute.await_args.args[1]
    assert "pg_advisory_xact_lock" in str(stmt)
    assert params == {"ns": ns, "key": key}


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
        side_effect=[
            MagicMock(),  # advisory lock (must precede load)
            _scalar_result(entries),
            _row_result(tag_rows),
            _row_result([]),
            _scalar_result(entries),
            _row_result([]),
            MagicMock(),  # delete prior insights for the day
        ]
    )
    db.flush = AsyncMock()

    stored = await generate_and_store_insights(db, user_id=user.id, as_of=date(2026, 5, 1))

    assert stored
    assert db.execute.await_count == 7
    lock_stmt = db.execute.await_args_list[0].args[0]
    assert "pg_advisory_xact_lock" in str(lock_stmt)
    load_stmt = db.execute.await_args_list[1].args[0]
    assert "entries.entry_date < :entry_date_1" in str(load_stmt.whereclause)
    assert "ORDER BY entries.entry_date ASC" in str(load_stmt)
    delete_stmt = db.execute.await_args_list[6].args[0]
    assert "DELETE FROM insights" in str(delete_stmt)
    assert db.add.call_count == len(stored)
    assert db.flush.await_count == 1
    assert any(insight.insight_type == InsightType.POINTBISERIAL for insight in stored)
    assert all(insight.user_id == user.id for insight in stored)
    assert all(insight.generated_for_date == date(2026, 5, 1) for insight in stored)


@pytest.mark.asyncio
async def test_load_analytics_data_filters_hidden_tags() -> None:
    user = make_user()
    as_of = date(2026, 5, 1)
    entries = [make_entry(user, entry_date=as_of - timedelta(days=1))]
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_result(entries), _row_result([]), _row_result([])])

    await load_analytics_data(db, user_id=user.id, as_of=as_of)

    tag_stmt = db.execute.await_args_list[1].args[0]
    assert "tags.is_hidden IS false" in str(tag_stmt.whereclause)


@pytest.mark.asyncio
async def test_load_analytics_data_includes_visible_symptoms() -> None:
    user = make_user()
    as_of = date(2026, 5, 1)
    entry = make_entry(user, entry_date=as_of - timedelta(days=1))
    symptom = make_symptom(user=None, is_default=True, slug="headache", name="Headache")
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result([entry]),
            _row_result([]),
            _row_result([(entry.id, symptom)]),
        ]
    )

    entries, _, symptoms = await load_analytics_data(db, user_id=user.id, as_of=as_of)

    assert entries[0].symptom_ids == frozenset({symptom.id})
    assert symptoms == [
        SymptomSnapshot(
            id=symptom.id,
            label="Headache",
            slug="headache",
            is_default=True,
        )
    ]
    symptom_stmt = db.execute.await_args_list[2].args[0]
    where_sql = str(symptom_stmt.whereclause)
    assert "entry_symptoms.user_id = :user_id_1" in where_sql
    assert "entry_symptoms.intensity > :intensity_1" in where_sql


@pytest.mark.asyncio
async def test_load_analytics_data_includes_work_context() -> None:
    user = make_user()
    as_of = date(2026, 5, 1)
    entry = make_entry(
        user,
        entry_date=as_of - timedelta(days=1),
        work_context=WorkContext.TRAVEL,
    )
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_result([entry]), _row_result([]), _row_result([])])

    entries, _, _ = await load_analytics_data(db, user_id=user.id, as_of=as_of)

    assert entries[0].work_context is WorkContext.TRAVEL


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


def test_m7_lasso_candidates_include_symptom_features_after_90_entries() -> None:
    symptom_id = uuid.uuid4()
    symptom = SymptomSnapshot(id=symptom_id, label="Headache", slug="headache")
    start = date(2026, 1, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=2 if offset % 3 == 0 else 5,
            energy=3,
            stress=3,
            symptom_ids=frozenset({symptom_id}) if offset % 3 == 0 else frozenset(),
        )
        for offset in range(95)
    ]

    candidates = generate_insight_candidates(
        entries,
        symptoms=[symptom],
        as_of=date(2026, 4, 6),
    )

    lasso_candidates = [
        candidate
        for candidate in candidates
        if candidate.insight_type == InsightType.SYMPTOM_CLUSTER
        and candidate.payload["method"] == "lasso"
    ]
    assert lasso_candidates
    assert any(
        feature["kind"] == "symptom" and feature["slug"] == "headache"
        for candidate in lasso_candidates
        for feature in candidate.payload["features"]
    )

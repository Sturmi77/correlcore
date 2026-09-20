from __future__ import annotations

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.entry import EntrySlot
from app.models.insight import InsightType
from app.models.tag import TagCategory
from app.models.user import User
from app.schemas.stats import SymptomTagCooccurrenceResponse
from app.services.insight_engine import (
    AnalyticsEntry,
    SymptomSnapshot,
    TagSnapshot,
    generate_insight_candidates,
)
from app.services.stats_service import get_symptom_tag_cooccurrence
from tests.conftest import make_entry, make_symptom, make_tag, make_user


def _row_result(values: list[tuple[object, ...]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values
    return result


def _scalar_result(values: list[object]) -> MagicMock:
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _scalar_one_or_none_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _entry(
    day: date,
    *,
    mood: int = 3,
    energy: int = 3,
    stress: int = 3,
    tag_ids: frozenset[uuid.UUID] = frozenset(),
    symptom_ids: frozenset[uuid.UUID] = frozenset(),
) -> AnalyticsEntry:
    return AnalyticsEntry(
        id=uuid.uuid4(),
        entry_date=day,
        mood_score=mood,
        energy=energy,
        stress=stress,
        tag_ids=tag_ids,
        symptom_ids=symptom_ids,
    )


def test_symptom_mood_association_candidates_use_fdr_and_frequency_guards() -> None:
    symptom_id = uuid.uuid4()
    symptom = SymptomSnapshot(id=symptom_id, label="Headache", slug="headache")
    start = date(2026, 1, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=2 if offset < 10 else 5,
            energy=3,
            stress=3,
            symptom_ids=frozenset({symptom_id}) if offset < 10 else frozenset(),
        )
        for offset in range(30)
    ]

    candidates = generate_insight_candidates(
        entries,
        symptoms=[symptom],
        as_of=date(2026, 2, 1),
    )

    symptom_candidates = [
        candidate
        for candidate in candidates
        if candidate.insight_type == InsightType.SYMPTOM_MOOD_ASSOCIATION
    ]
    assert len(symptom_candidates) == 1
    candidate = symptom_candidates[0]
    assert candidate.metric == "mood_score"
    assert candidate.subject_type == "symptom"
    assert candidate.subject_id == symptom_id
    assert candidate.payload["symptom_slug"] == "headache"
    assert candidate.payload["symptom_n"] == 10
    assert candidate.flags["multiple_testing_correction"] == "fdr_bh"
    # #632: descriptive statement only; the "not a cause" hedge moved to the feed header.
    assert "line up with" in candidate.statement
    assert "cause" not in candidate.statement


def test_symptom_mood_association_skips_near_daily_symptoms() -> None:
    symptom_id = uuid.uuid4()
    symptom = SymptomSnapshot(id=symptom_id, label="Fatigue", slug="fatigue")
    start = date(2026, 1, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=2 if offset < 26 else 5,
            symptom_ids=frozenset({symptom_id}) if offset < 26 else frozenset(),
        )
        for offset in range(30)
    ]

    candidates = generate_insight_candidates(
        entries,
        symptoms=[symptom],
        as_of=date(2026, 2, 1),
    )

    assert all(
        candidate.insight_type != InsightType.SYMPTOM_MOOD_ASSOCIATION for candidate in candidates
    )


def test_symptom_tag_cooccurrence_candidates_surface_lift_and_fisher_result() -> None:
    symptom_id = uuid.uuid4()
    tag_id = uuid.uuid4()
    symptom = SymptomSnapshot(id=symptom_id, label="Headache", slug="headache")
    tag = TagSnapshot(id=tag_id, label="Stress", slug="stress")
    start = date(2026, 1, 1)
    entries: list[AnalyticsEntry] = []
    for offset in range(40):
        has_both = offset < 10
        has_symptom_only = 10 <= offset < 15
        has_tag_only = 15 <= offset < 20
        entries.append(
            _entry(
                start + timedelta(days=offset),
                mood=(offset % 5) + 1,
                energy=(offset % 4) + 1,
                stress=(offset % 3) + 1,
                symptom_ids=frozenset({symptom_id})
                if has_both or has_symptom_only
                else frozenset(),
                tag_ids=frozenset({tag_id}) if has_both or has_tag_only else frozenset(),
            )
        )

    candidates = generate_insight_candidates(
        entries,
        tags=[tag],
        symptoms=[symptom],
        as_of=date(2026, 2, 10),
    )

    candidate = next(
        candidate
        for candidate in candidates
        if candidate.insight_type == InsightType.SYMPTOM_TAG_COOCCURRENCE
    )
    assert candidate.subject_type == "symptom_tag"
    assert candidate.payload["symptom_slug"] == "headache"
    assert candidate.payload["tag_slug"] == "stress"
    assert candidate.payload["co_count"] == 10
    assert candidate.payload["lift"] > 1.67
    assert candidate.flags["multiple_testing_correction"] == "fdr_bh"


@pytest.mark.asyncio
async def test_symptom_tag_cooccurrence_service_returns_cells() -> None:
    user = make_user()
    symptom = make_symptom(user=None, is_default=True, slug="headache", name="Headache")
    tag = make_tag(user, slug="stress", name="Stress", category=TagCategory.WORK)
    start = date(2026, 1, 1)
    entries = [make_entry(user, entry_date=start + timedelta(days=offset)) for offset in range(40)]
    symptom_rows = [
        (entry.id, symptom)
        for offset, entry in enumerate(entries)
        if offset < 10 or 10 <= offset < 15
    ]
    tag_rows = [
        (entry.id, tag) for offset, entry in enumerate(entries) if offset < 10 or 15 <= offset < 20
    ]
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result(entries),
            _row_result(tag_rows),
            _row_result(symptom_rows),
        ]
    )

    response = await get_symptom_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=5,
        as_of=date(2026, 2, 9),
    )

    assert response.range == "90d"
    assert len(response.cells) == 1
    cell = response.cells[0]
    assert cell.symptom.slug == "headache"
    assert cell.tag.slug == "stress"
    assert cell.co_count == 10
    assert cell.lift > 1.67
    symptom_stmt = db.execute.await_args_list[3].args[0]
    assert "entry_symptoms.intensity > :intensity_1" in str(symptom_stmt.whereclause)


@pytest.mark.asyncio
async def test_symptom_tag_cooccurrence_service_applies_min_count_to_cells() -> None:
    user = make_user()
    symptom = make_symptom(user=None, is_default=True, slug="headache", name="Headache")
    tag = make_tag(user, slug="stress", name="Stress", category=TagCategory.WORK)
    start = date(2026, 1, 1)
    entries = [make_entry(user, entry_date=start + timedelta(days=offset)) for offset in range(40)]
    symptom_rows = [
        (entry.id, symptom)
        for offset, entry in enumerate(entries)
        if offset < 10 or 10 <= offset < 15
    ]
    tag_rows = [
        (entry.id, tag) for offset, entry in enumerate(entries) if offset < 10 or 15 <= offset < 20
    ]
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result(entries),
            _row_result(tag_rows),
            _row_result(symptom_rows),
        ]
    )

    response = await get_symptom_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=11,
        as_of=date(2026, 2, 9),
    )

    assert response.cells == []


@pytest.mark.asyncio
async def test_symptom_tag_cooccurrence_service_skips_when_analytics_disabled() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_one_or_none_result(False))

    response = await get_symptom_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=3,
        as_of=date(2026, 2, 9),
    )

    assert response.range == "90d"
    assert response.start_date == date(2025, 11, 12)
    assert response.end_date == date(2026, 2, 9)
    assert response.cells == []
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_symptom_tag_cooccurrence_service_canonicalizes_tag_overrides() -> None:
    user = make_user()
    symptom = make_symptom(user=None, is_default=True, slug="headache", name="Headache")
    default_tag = make_tag(user=None, is_default=True, slug="stress", name="Stress")
    override_tag = make_tag(user, slug="stress", name="Stress custom", category=TagCategory.WORK)
    start = date(2026, 1, 1)
    entries = [make_entry(user, entry_date=start + timedelta(days=offset)) for offset in range(40)]
    symptom_rows = [
        (entry.id, symptom)
        for offset, entry in enumerate(entries)
        if offset < 10 or 10 <= offset < 15
    ]
    tag_rows = []
    for offset, entry in enumerate(entries):
        if offset < 5:
            tag_rows.append((entry.id, default_tag))
        elif offset < 10 or 15 <= offset < 20:
            tag_rows.append((entry.id, override_tag))
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result(entries),
            _row_result(tag_rows),
            _row_result(symptom_rows),
        ]
    )

    response = await get_symptom_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=5,
        as_of=date(2026, 2, 9),
    )

    assert len(response.cells) == 1
    assert response.cells[0].tag.tag_id == override_tag.id
    assert response.cells[0].tag.slug == "stress"
    assert response.cells[0].co_count == 10


@pytest.mark.asyncio
async def test_symptom_tag_cooccurrence_service_collapses_multiple_slots_per_day() -> None:
    user = make_user()
    symptom = make_symptom(user=None, is_default=True, slug="headache", name="Headache")
    tag = make_tag(user, slug="stress", name="Stress", category=TagCategory.WORK)
    start = date(2026, 1, 1)
    entries = []
    symptom_rows = []
    tag_rows = []
    for offset in range(40):
        entry_date = start + timedelta(days=offset)
        if offset < 10:
            morning = make_entry(user, entry_date=entry_date, slot=EntrySlot.MORNING)
            evening = make_entry(user, entry_date=entry_date, slot=EntrySlot.EVENING)
            entries.extend([morning, evening])
            symptom_rows.append((morning.id, symptom))
            tag_rows.append((evening.id, tag))
        else:
            entries.append(make_entry(user, entry_date=entry_date))
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result(entries),
            _row_result(tag_rows),
            _row_result(symptom_rows),
        ]
    )

    response = await get_symptom_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=5,
        as_of=date(2026, 2, 9),
    )

    assert len(response.cells) == 1
    assert response.cells[0].co_count == 10
    assert response.cells[0].total_count == 40


@pytest.mark.asyncio
async def test_symptom_tag_cooccurrence_endpoint_returns_cells(
    async_client: AsyncClient,
    user: User,
) -> None:
    payload = SymptomTagCooccurrenceResponse(
        range="90d",
        start_date=date(2026, 2, 9),
        end_date=date(2026, 5, 9),
        min_count=3,
        cells=[],
    )

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.insights.get_symptom_tag_cooccurrence",
            new_callable=AsyncMock,
            return_value=payload,
        ) as service:
            response = await async_client.get(
                "/api/v1/insights/symptom-tag-cooccurrence?range=90d&min_count=3",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    service.assert_awaited_once()
    assert response.json()["range"] == "90d"


def test_symptom_associations_carry_real_metric_values() -> None:
    """#928 L2: the insight payload needs real G2 distributions, not synthesized ones.

    The UI accepts this family on the strength of symptom_n/comparison_n. With
    the histograms missing it substituted zero arrays, so every symptom card
    claimed "good on 0 of N days" — a fabricated count shown as evidence.
    """
    from app.services.symptom_analytics import (
        DailySymptomEntry,
        SymptomRef,
        compute_symptom_metric_associations,
    )

    symptom_id = uuid.uuid4()
    symptom = SymptomRef(id=symptom_id, label="Headache", slug="headache")
    start = date(2026, 1, 1)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=2 if offset % 2 == 0 else 5,
            energy=3,
            stress=3,
            tag_ids=frozenset(),
            symptom_ids=frozenset({symptom_id}) if offset % 2 == 0 else frozenset(),
        )
        for offset in range(40)
    ]

    associations = compute_symptom_metric_associations(entries, {symptom_id: symptom})
    mood = [item for item in associations if item.metric == "mood_score"]
    assert mood, "expected a mood association for the seeded pattern"
    finding = mood[0]

    assert len(finding.symptom_metric_values) == finding.symptom_count
    assert len(finding.comparison_metric_values) == finding.comparison_count
    # Real values, not placeholders: the present group logged 2, the absent one 5.
    assert set(finding.symptom_metric_values) == {2.0}
    assert set(finding.comparison_metric_values) == {5.0}


def test_symptom_stress_distribution_counts_calm_days_as_good() -> None:
    """#955: the G2 payload must read stress on its own scale.

    #954 populated real distributions for symptom cards (they previously showed
    a fabricated "good on 0 of N days"). That fix routed every metric target
    through a helper with a fixed `>= 4`, so the stress variant inherited the
    inversion defect — a symptom occurring on the most stressful days was
    reported as occurring on good ones.
    """
    from app.services.insights.shared import _with_without_distribution_payload

    stressed = [5, 5, 4, 5]
    calm = [1, 2, 1, 2]

    stress_payload = _with_without_distribution_payload(stressed, calm, metric="stress")
    assert stress_payload["with_good_count"] == 0
    assert stress_payload["without_good_count"] == 4
    assert stress_payload["good_direction"] == "lte"
    assert stress_payload["good_threshold"] == 2

    mood_payload = _with_without_distribution_payload(stressed, calm, metric="mood_score")
    assert mood_payload["with_good_count"] == 4
    assert mood_payload["without_good_count"] == 0
    assert mood_payload["good_direction"] == "gte"

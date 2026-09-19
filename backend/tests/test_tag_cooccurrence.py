"""Tests for M5.1 tag co-occurrence endpoint and Phase 10 statistical gate."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.entry import EntrySlot
from app.models.tag import TagCategory
from app.models.user import User
from app.schemas.stats import TagCooccurrenceResponse
from app.services.stats_service import get_tag_cooccurrence
from app.services.symptom_analytics import (
    DailySymptomEntry,
    TagRef,
    compute_tag_tag_associations,
    heatmap_tag_tag_associations,
)
from tests.conftest import make_entry, make_tag, make_user


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


def _lifted_pair_fixture(user, *, days: int = 40, co_days: int = 10):
    """Build entry + tag rows with a strong Sport×Focus co-occurrence."""

    sport = make_tag(user=None, is_default=True, slug="sport", name="Sport")
    focus = make_tag(user, slug="focus", name="Focus", category=TagCategory.WORK)
    start = date(2026, 1, 1)
    entries = [
        make_entry(user, entry_date=start + timedelta(days=offset)) for offset in range(days)
    ]
    tag_rows: list[tuple[object, object]] = []
    for offset, entry in enumerate(entries):
        if offset < co_days or co_days <= offset < co_days + 5:
            tag_rows.append((entry.id, sport))
        if offset < co_days or co_days + 5 <= offset < co_days + 10:
            tag_rows.append((entry.id, focus))
    return sport, focus, entries, tag_rows, start


@pytest.mark.asyncio
async def test_tag_cooccurrence_returns_gated_pairs_with_percentages() -> None:
    user = make_user()
    sport, focus, entries, tag_rows, _start = _lifted_pair_fixture(user)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result(entries),
            _row_result(tag_rows),
        ]
    )

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=5,
        as_of=date(2026, 2, 9),
    )

    assert out.range == "90d"
    assert out.start_date == date(2025, 11, 12)
    assert out.end_date == date(2026, 2, 9)
    assert len(out.pairs) == 1
    pair = out.pairs[0]
    assert pair.count == 10
    assert {pair.tag_a.slug, pair.tag_b.slug} == {"focus", "sport"}
    assert pair.pct_of_a == pytest.approx(66.7, abs=0.1)
    assert pair.pct_of_b == pytest.approx(66.7, abs=0.1)


@pytest.mark.asyncio
async def test_tag_cooccurrence_merges_default_and_override_aliases() -> None:
    user = make_user()
    default = make_tag(user=None, is_default=True, slug="alcohol", name="Alcohol")
    override = make_tag(user, slug="alcohol", name="Alkohol", category=TagCategory.CONSUMPTION)
    focus = make_tag(user, slug="focus", name="Focus", category=TagCategory.WORK)
    start = date(2026, 1, 1)
    entries = [make_entry(user, entry_date=start + timedelta(days=offset)) for offset in range(40)]
    tag_rows: list[tuple[object, object]] = []
    for offset, entry in enumerate(entries):
        alcohol = default if offset % 2 == 0 else override
        if offset < 10 or 10 <= offset < 15:
            tag_rows.append((entry.id, alcohol))
        if offset < 10 or 15 <= offset < 20:
            tag_rows.append((entry.id, focus))

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result(entries),
            _row_result(tag_rows),
        ]
    )

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=5,
        as_of=date(2026, 2, 9),
    )

    assert len(out.pairs) == 1
    pair = out.pairs[0]
    assert {pair.tag_a.slug, pair.tag_b.slug} == {"alcohol", "focus"}
    alcohol = pair.tag_a if pair.tag_a.slug == "alcohol" else pair.tag_b
    assert alcohol.tag_id == override.id
    assert alcohol.name == "Alkohol"


@pytest.mark.asyncio
async def test_tag_cooccurrence_applies_min_count_filter() -> None:
    user = make_user()
    _sport, _focus, entries, tag_rows, _start = _lifted_pair_fixture(user)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result(entries),
            _row_result(tag_rows),
        ]
    )

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=20,
        as_of=date(2026, 2, 9),
    )

    assert out.pairs == []


@pytest.mark.asyncio
async def test_tag_cooccurrence_skips_when_analytics_disabled() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_one_or_none_result(False))

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=2,
        as_of=date(2026, 5, 9),
    )

    assert out.range == "90d"
    assert out.start_date == date(2026, 2, 9)
    assert out.end_date == date(2026, 5, 9)
    assert out.pairs == []
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_tag_cooccurrence_excludes_hidden_tags_in_query() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result([]),
        ]
    )

    await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="30d",
        as_of=date(2026, 5, 9),
    )

    # Empty entries short-circuit before the tag query.
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_tag_cooccurrence_tag_query_uses_analytics_predicate() -> None:
    user = make_user()
    entry = make_entry(user, entry_date=date(2026, 5, 8))
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result([entry]),
            _row_result([]),
        ]
    )

    await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="30d",
        as_of=date(2026, 5, 9),
    )

    tag_stmt = db.execute.await_args_list[2].args[0]
    assert "tags.is_hidden IS false" in str(tag_stmt.whereclause)


@pytest.mark.asyncio
async def test_tag_cooccurrence_uses_range_window() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result([]),
        ]
    )

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="1y",
        as_of=date(2026, 5, 9),
    )

    assert out.start_date == date(2025, 5, 10)
    assert out.end_date == date(2026, 5, 9)


@pytest.mark.asyncio
async def test_tag_cooccurrence_collapses_multiple_slots_per_day() -> None:
    user = make_user()
    sport = make_tag(user=None, is_default=True, slug="sport", name="Sport")
    focus = make_tag(user, slug="focus", name="Focus", category=TagCategory.WORK)
    start = date(2026, 1, 1)
    entries = []
    tag_rows = []
    for offset in range(40):
        entry_date = start + timedelta(days=offset)
        if offset < 10:
            morning = make_entry(user, entry_date=entry_date, slot=EntrySlot.MORNING)
            evening = make_entry(user, entry_date=entry_date, slot=EntrySlot.EVENING)
            entries.extend([morning, evening])
            tag_rows.append((morning.id, sport))
            tag_rows.append((evening.id, focus))
        else:
            entries.append(make_entry(user, entry_date=entry_date))

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result(entries),
            _row_result(tag_rows),
        ]
    )

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=5,
        as_of=date(2026, 2, 9),
    )

    assert len(out.pairs) == 1
    assert out.pairs[0].count == 10


@pytest.mark.asyncio
async def test_tag_cooccurrence_drops_chance_pairs_without_lift() -> None:
    user = make_user()
    sport = make_tag(user=None, is_default=True, slug="sport", name="Sport")
    coffee = make_tag(user, slug="coffee", name="Coffee", category=TagCategory.CONSUMPTION)
    start = date(2026, 1, 1)
    entries = [make_entry(user, entry_date=start + timedelta(days=offset)) for offset in range(40)]
    # Independent tags: each on half the days, overlap ≈ expected → lift ≈ 1.
    tag_rows = []
    for offset, entry in enumerate(entries):
        if offset % 2 == 0:
            tag_rows.append((entry.id, sport))
        if offset % 2 == 1 or offset < 2:
            tag_rows.append((entry.id, coffee))

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(True),
            _scalar_result(entries),
            _row_result(tag_rows),
        ]
    )

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=2,
        as_of=date(2026, 2, 9),
    )

    assert out.pairs == []


def test_heatmap_tag_tag_associations_require_fdr_or_lift() -> None:
    tag_a_id = uuid4()
    tag_b_id = uuid4()
    tags = {
        tag_a_id: TagRef(id=tag_a_id, label="Sport", slug="sport"),
        tag_b_id: TagRef(id=tag_b_id, label="Focus", slug="focus"),
    }
    start = date(2026, 1, 1)
    entries: list[DailySymptomEntry] = []
    for offset in range(40):
        has_both = offset < 10
        has_a_only = 10 <= offset < 15
        has_b_only = 15 <= offset < 20
        tag_ids: set = set()
        if has_both or has_a_only:
            tag_ids.add(tag_a_id)
        if has_both or has_b_only:
            tag_ids.add(tag_b_id)
        entries.append(
            DailySymptomEntry(
                entry_date=start + timedelta(days=offset),
                mood_score=3,
                energy=3,
                stress=3,
                tag_ids=frozenset(tag_ids),
                symptom_ids=frozenset(),
            )
        )

    associations = heatmap_tag_tag_associations(entries, tags)
    assert len(associations) == 1
    assert associations[0].co_count == 10
    assert associations[0].lift > 1.5

    cards = compute_tag_tag_associations(entries, tags)
    assert len(cards) == 1
    assert cards[0].p_corrected <= 0.10


@pytest.mark.asyncio
async def test_tag_cooccurrence_endpoint_returns_pairs(
    async_client: AsyncClient,
    user: User,
) -> None:
    payload = TagCooccurrenceResponse(
        range="90d",
        start_date=date(2026, 2, 9),
        end_date=date(2026, 5, 9),
        min_count=2,
        pairs=[],
    )

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.insights.get_tag_cooccurrence",
            new_callable=AsyncMock,
            return_value=payload,
        ) as service:
            response = await async_client.get(
                "/api/v1/insights/tag-cooccurrence?range=90d&min_count=2",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    service.assert_awaited_once()
    assert response.json()["range"] == "90d"
    assert response.json()["min_count"] == 2


@pytest.mark.asyncio
async def test_tag_cooccurrence_endpoint_rejects_invalid_range(
    async_client: AsyncClient,
    user: User,
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        response = await async_client.get(
            "/api/v1/insights/tag-cooccurrence?range=28d",
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_tag_cooccurrence_endpoint_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/insights/tag-cooccurrence")

    assert response.status_code == 401

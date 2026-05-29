"""Tests for M5.1 tag co-occurrence endpoint and service."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.tag import TagCategory
from app.models.user import User
from app.schemas.stats import TagCooccurrenceResponse
from app.services.stats_service import get_tag_cooccurrence
from tests.conftest import make_entry, make_tag, make_user


def _row_result(values: list[tuple[object, ...]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values
    return result


@pytest.mark.asyncio
async def test_tag_cooccurrence_counts_pairs_and_percentages() -> None:
    user = make_user()
    entry_a = make_entry(user, entry_date=date(2026, 5, 8))
    entry_b = make_entry(user, entry_date=date(2026, 5, 9))
    sport = make_tag(user=None, is_default=True, slug="sport", name="Sport")
    focus = make_tag(user, slug="focus", name="Focus", category=TagCategory.WORK)
    coffee = make_tag(user, slug="coffee", name="Coffee", category=TagCategory.CONSUMPTION)

    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_row_result(
            [
                (entry_a.id, sport),
                (entry_a.id, focus),
                (entry_b.id, sport),
                (entry_b.id, focus),
                (entry_b.id, coffee),
            ]
        )
    )

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="30d",
        min_count=2,
        as_of=date(2026, 5, 9),
    )

    assert out.range == "30d"
    assert out.start_date == date(2026, 4, 10)
    assert out.end_date == date(2026, 5, 9)
    assert len(out.pairs) == 1
    pair = out.pairs[0]
    assert pair.count == 2
    assert {pair.tag_a.slug, pair.tag_b.slug} == {"focus", "sport"}
    assert pair.pct_of_a == 100.0
    assert pair.pct_of_b == 100.0


@pytest.mark.asyncio
async def test_tag_cooccurrence_applies_min_count_filter() -> None:
    user = make_user()
    entry = make_entry(user, entry_date=date(2026, 5, 8))
    sport = make_tag(user=None, is_default=True, slug="sport", name="Sport")
    focus = make_tag(user, slug="focus", name="Focus", category=TagCategory.WORK)
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_row_result(
            [
                (entry.id, sport),
                (entry.id, focus),
            ]
        )
    )

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="90d",
        min_count=2,
        as_of=date(2026, 5, 9),
    )

    assert out.pairs == []


@pytest.mark.asyncio
async def test_tag_cooccurrence_excludes_hidden_tags_in_query() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_row_result([]))

    await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="30d",
        as_of=date(2026, 5, 9),
    )

    stmt = db.execute.await_args.args[0]
    assert "tags.is_hidden IS false" in str(stmt.whereclause)


@pytest.mark.asyncio
async def test_tag_cooccurrence_uses_range_window() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_row_result([]))

    out = await get_tag_cooccurrence(
        db,
        user_id=user.id,
        range_="1y",
        as_of=date(2026, 5, 9),
    )

    assert out.start_date == date(2025, 5, 10)
    assert out.end_date == date(2026, 5, 9)


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

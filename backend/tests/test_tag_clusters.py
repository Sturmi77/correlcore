from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.tag import TagCategory
from app.models.user import User
from app.schemas.stats import TagClustersResponse
from app.services.tag_cluster_service import (
    DailyTagSet,
    build_tag_cluster_response,
    build_tag_vectors,
    get_tag_clusters,
    recompute_tag_vectors_and_clusters,
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


def _scalar_one_or_none_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _cluster_fixture() -> tuple[list[DailyTagSet], list[object]]:
    tags = [
        make_tag(slug="focus", name="Focus", category=TagCategory.WORK),
        make_tag(slug="deep-work", name="Deep work", category=TagCategory.WORK),
        make_tag(slug="walk", name="Walk", category=TagCategory.SPORT),
        make_tag(slug="stretch", name="Stretch", category=TagCategory.SPORT),
        make_tag(slug="coffee", name="Coffee", category=TagCategory.CONSUMPTION),
        make_tag(slug="reading", name="Reading", category=TagCategory.LEISURE),
    ]
    start = date(2026, 1, 1)
    daily: list[DailyTagSet] = []
    for offset in range(100):
        group = offset % 3
        if group == 0:
            tag_ids = {tags[0].id, tags[1].id}
        elif group == 1:
            tag_ids = {tags[2].id, tags[3].id}
        else:
            tag_ids = {tags[4].id, tags[5].id}
        daily.append(
            DailyTagSet(entry_date=start + timedelta(days=offset), tag_ids=frozenset(tag_ids))
        )
    return daily, tags


def test_tag_clusters_return_insufficient_data_below_entry_threshold() -> None:
    daily, tags = _cluster_fixture()
    response = build_tag_cluster_response(build_tag_vectors(daily[:89], tags))

    assert response.status == "insufficient_data"
    assert response.reason == "entry_count_below_90"
    assert response.entry_count == 89


def test_tag_clusters_group_tags_from_jaccard_vectors() -> None:
    daily, tags = _cluster_fixture()
    response = build_tag_cluster_response(build_tag_vectors(daily, tags))

    assert response.status == "ok"
    assert response.k is not None
    assert response.active_tag_count == 6
    assert response.entry_count == 100
    assert sum(len(cluster.tags) for cluster in response.clusters) == 6
    assert all(
        "AI" not in cluster.label and "ML" not in cluster.label for cluster in response.clusters
    )


@pytest.mark.asyncio
async def test_recompute_tag_vectors_upserts_vectors() -> None:
    user = make_user()
    daily, tags = _cluster_fixture()
    entries = [make_entry(user, entry_date=row.entry_date) for row in daily]
    tags_by_id = {tag.id: tag for tag in tags}
    tag_rows = [(row.entry_date, tags_by_id[tag_id]) for row in daily for tag_id in row.tag_ids]
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[_scalar_result(entries), _row_result(tag_rows), *[MagicMock() for _ in tags]]
    )

    response = await recompute_tag_vectors_and_clusters(
        db,
        user_id=user.id,
        as_of=date(2026, 4, 10),
    )

    assert response.status == "ok"
    assert db.execute.await_count == 2 + len(tags)


@pytest.mark.asyncio
async def test_get_tag_clusters_skips_recompute_when_analytics_disabled() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_one_or_none_result(False))

    response = await get_tag_clusters(db, user_id=user.id, as_of=date(2026, 4, 10))

    assert response.status == "insufficient_data"
    assert response.reason == "analytics_disabled"
    assert response.entry_count == 0
    assert response.active_tag_count == 0
    assert response.clusters == []
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_tag_clusters_endpoint_returns_response(
    async_client: AsyncClient,
    user: User,
) -> None:
    payload = TagClustersResponse(
        status="insufficient_data",
        entry_count=12,
        active_tag_count=3,
        window_days=90,
        reason="entry_count_below_90",
        clusters=[],
    )

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.insights.get_tag_clusters",
            new_callable=AsyncMock,
            return_value=payload,
        ) as service:
            response = await async_client.get(
                "/api/v1/insights/tag-clusters",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    service.assert_awaited_once()
    assert response.json()["status"] == "insufficient_data"

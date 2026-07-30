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
    _dominant_signal_name,
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
    response = build_tag_cluster_response(build_tag_vectors(daily[:29], tags))

    assert response.status == "insufficient_data"
    assert response.reason == "entry_count_below_30"
    assert response.entry_count == 29
    assert response.entries_until_robust == 61


def test_dominant_signal_name_prefers_frequency_then_slug() -> None:
    import uuid

    a, b = uuid.uuid4(), uuid.uuid4()
    names = {a: "Alpha", b: "Beta"}
    slugs = {a: "alpha", b: "beta"}
    # Beta occurs on 3 days, Alpha on 1 -> Beta dominates despite the later slug.
    entries = [
        DailyTagSet(entry_date=date(2026, 1, 1), tag_ids=frozenset({a, b})),
        DailyTagSet(entry_date=date(2026, 1, 2), tag_ids=frozenset({b})),
        DailyTagSet(entry_date=date(2026, 1, 3), tag_ids=frozenset({b})),
    ]
    assert (
        _dominant_signal_name([a, b], names_by_id=names, slugs_by_id=slugs, daily_entries=entries)
        == "Beta"
    )
    # Equal frequency -> deterministic tie-break on slug (alpha < beta).
    tie = [DailyTagSet(entry_date=date(2026, 1, 1), tag_ids=frozenset({a, b}))]
    assert (
        _dominant_signal_name([a, b], names_by_id=names, slugs_by_id=slugs, daily_entries=tie)
        == "Alpha"
    )


def test_tag_clusters_use_pair_mode_between_30_and_44_days() -> None:
    daily, tags = _cluster_fixture()
    response = build_tag_cluster_response(build_tag_vectors(daily[:35], tags))

    assert response.status == "ok"
    assert response.cluster_mode == "pair"
    assert response.cluster_maturity == "early"
    assert response.k is None
    assert response.clusters
    for cluster in response.clusters:
        assert cluster.label in {member.name for member in cluster.members}


def test_tag_clusters_use_provisional_kmeans_at_67_days() -> None:
    daily, tags = _cluster_fixture()
    response = build_tag_cluster_response(build_tag_vectors(daily[:67], tags))

    assert response.status == "ok"
    assert response.cluster_maturity == "provisional"
    assert response.cluster_mode == "kmeans"
    assert response.k is not None
    assert response.k <= 3
    assert response.silhouette_score is not None
    assert response.silhouette_score >= 0.08


def test_tag_clusters_group_tags_from_jaccard_vectors() -> None:
    daily, tags = _cluster_fixture()
    response = build_tag_cluster_response(build_tag_vectors(daily, tags))

    assert response.status == "ok"
    assert response.cluster_maturity == "robust"
    assert response.cluster_mode == "kmeans"
    assert response.k is not None
    assert response.active_tag_count == 6
    assert response.active_signal_count == 6
    assert response.entry_count == 100
    assert sum(len(cluster.tags) for cluster in response.clusters) == 6
    # #573: each group is named after one of its member tags, not "Tag group N".
    for cluster in response.clusters:
        member_names = {member.name for member in cluster.members}
        assert cluster.label in member_names
        assert not cluster.label.startswith("Tag group")
        assert not cluster.label.startswith("Signal group")


@pytest.mark.asyncio
async def test_recompute_tag_vectors_upserts_vectors() -> None:
    user = make_user()
    daily, tags = _cluster_fixture()
    entries = [make_entry(user, entry_date=row.entry_date) for row in daily]
    tags_by_id = {tag.id: tag for tag in tags}
    tag_rows = [(row.entry_date, tags_by_id[tag_id]) for row in daily for tag_id in row.tag_ids]
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entries),
            _row_result(tag_rows),
            _row_result([]),
            *[MagicMock() for _ in tags],
        ]
    )

    response = await recompute_tag_vectors_and_clusters(
        db,
        user_id=user.id,
        as_of=date(2026, 4, 10),
    )

    assert response.status == "ok"
    assert db.execute.await_count == 3 + len(tags)


@pytest.mark.asyncio
async def test_recompute_tag_vectors_canonicalizes_tag_overrides() -> None:
    user = make_user()
    daily, fixture_tags = _cluster_fixture()
    original_focus_id = fixture_tags[0].id
    default_focus = make_tag(user=None, is_default=True, slug="focus", name="Focus")
    override_focus = make_tag(user, slug="focus", name="Focus custom", category=TagCategory.WORK)
    tags = [override_focus, *fixture_tags[1:]]
    entries = [make_entry(user, entry_date=row.entry_date) for row in daily]
    tags_by_id = {tag.id: tag for tag in fixture_tags[1:]}
    tag_rows: list[tuple[date, object]] = []
    for index, row in enumerate(daily):
        for tag_id in row.tag_ids:
            if tag_id == original_focus_id:
                tag_rows.append((row.entry_date, default_focus if index < 5 else override_focus))
                continue
            tag = tags_by_id.get(tag_id)
            if tag is None:
                continue
            tag_rows.append((row.entry_date, tag))

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entries),
            _row_result(tag_rows),
            _row_result([]),
            *[MagicMock() for _ in tags],
        ]
    )

    response = await recompute_tag_vectors_and_clusters(
        db,
        user_id=user.id,
        as_of=date(2026, 4, 10),
    )

    assert response.active_tag_count == len(tags)
    upsert_params = [call.args[1] for call in db.execute.await_args_list[3:]]
    assert {params["tag_id"] for params in upsert_params} == {tag.id for tag in tags}
    assert default_focus.id not in {params["tag_id"] for params in upsert_params}


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
    assert response.active_signal_count == 0
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
        active_signal_count=3,
        window_days=90,
        reason="entry_count_below_30",
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

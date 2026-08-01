from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.insight import Insight, InsightTier, InsightType
from app.models.user import User
from app.services.insight_service import insight_subject_key, list_insight_history
from tests.conftest import make_entry, make_tag, make_user


def _scalars_result(values: list[object]) -> MagicMock:
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _rows_result(values: list[tuple[object, ...]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values
    return result


def _make_insight(
    user: User,
    *,
    generated_for_date: date,
    subject_label: str = "energy",
    generated_at: datetime | None = None,
) -> Insight:
    now = generated_at or datetime.combine(generated_for_date, datetime.min.time(), tzinfo=UTC)
    insight = Insight()
    insight.id = uuid.uuid4()
    insight.user_id = user.id
    insight.insight_type = InsightType.SPEARMAN
    insight.tier = InsightTier.DEVELOPING
    insight.metric = "mood_score"
    insight.subject_type = "metric"
    insight.subject_id = None
    insight.subject_label = subject_label
    insight.effect_size = 0.4
    insight.confidence = 0.7
    insight.sample_n = 20
    insight.statement_enc = f"Statement for {subject_label}"
    insight.flags = {}
    insight.payload = {}
    insight.generated_for_date = generated_for_date
    insight.generated_at = now
    insight.created_at = now
    insight.updated_at = now
    return insight


@pytest.mark.asyncio
async def test_list_insight_history_includes_active_and_dismissed_versions() -> None:
    user = make_user()
    older = _make_insight(user, generated_for_date=date(2026, 5, 1), subject_label="stress")
    newer = _make_insight(user, generated_for_date=date(2026, 5, 10), subject_label="stress")
    other = _make_insight(user, generated_for_date=date(2026, 5, 10), subject_label="energy")
    subject_key = insight_subject_key(newer, tag_slugs_by_id={})

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([newer, other, older]),
            _rows_result([]),
        ]
    )

    with (
        patch(
            "app.services.insight_dismissal_service.migrate_uuid_prefs_to_subject_dismissals",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.services.insight_dismissal_service.list_dismissed_subject_keys",
            new=AsyncMock(return_value={subject_key}),
        ),
        patch(
            "app.services.insight_dismissal_service.dismissed_uuid_keys_remaining",
            new=AsyncMock(return_value=set()),
        ),
    ):
        entries, total = await list_insight_history(db, user_id=user.id, status="all")

    assert total == 3
    by_id = {entry.insight.id: entry for entry in entries}
    assert by_id[newer.id].visibility == "dismissed"
    assert by_id[older.id].visibility == "dismissed"
    assert by_id[other.id].visibility == "active"
    assert by_id[newer.id].observation_count == 2
    assert by_id[newer.id].first_seen_on == date(2026, 5, 1)
    assert by_id[newer.id].last_seen_on == date(2026, 5, 10)


@pytest.mark.asyncio
async def test_list_insight_history_filters_dismissed_only() -> None:
    user = make_user()
    hidden = _make_insight(user, generated_for_date=date(2026, 5, 10), subject_label="stress")
    visible = _make_insight(user, generated_for_date=date(2026, 5, 10), subject_label="energy")
    subject_key = insight_subject_key(hidden, tag_slugs_by_id={})
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([hidden, visible]),
            _rows_result([]),
        ]
    )

    with (
        patch(
            "app.services.insight_dismissal_service.migrate_uuid_prefs_to_subject_dismissals",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.services.insight_dismissal_service.list_dismissed_subject_keys",
            new=AsyncMock(return_value={subject_key}),
        ),
        patch(
            "app.services.insight_dismissal_service.dismissed_uuid_keys_remaining",
            new=AsyncMock(return_value=set()),
        ),
    ):
        entries, total = await list_insight_history(db, user_id=user.id, status="dismissed")

    assert total == 1
    assert entries[0].insight.id == hidden.id


@pytest.mark.asyncio
async def test_history_endpoint_returns_paginated_envelope(
    async_client: AsyncClient,
    user: User,
) -> None:
    row = _make_insight(user, generated_for_date=date(2026, 5, 10))

    class _Entry:
        def __init__(self) -> None:
            self.insight = row
            self.subject_key = "sk"
            self.visibility = "active"
            self.first_seen_on = date(2026, 5, 10)
            self.last_seen_on = date(2026, 5, 10)
            self.observation_count = 1

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.insights.list_insight_history",
            new_callable=AsyncMock,
            return_value=([_Entry()], 1),
        ):
            response = await async_client.get(
                "/api/v1/insights/history?status=all&limit=10",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert body["insights"][0]["visibility"] == "active"
    assert body["insights"][0]["subject_key"] == "sk"


@pytest.mark.asyncio
async def test_generate_delete_targets_only_same_generated_for_date() -> None:
    """Same-day regen must not wipe older history (#601 Phase 2)."""
    from app.services.insight_engine import generate_and_store_insights

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

    def _load_result(values: list[object]) -> MagicMock:
        result = MagicMock()
        result.scalars.return_value.all.return_value = values
        return result

    def _pair_result(values: list[tuple[object, ...]]) -> MagicMock:
        result = MagicMock()
        result.all.return_value = values
        return result

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            _load_result(entries),
            _pair_result(tag_rows),
            _pair_result([]),
            _load_result(entries),
            _pair_result([]),
            MagicMock(),
        ]
    )
    db.flush = AsyncMock()

    await generate_and_store_insights(db, user_id=user.id, as_of=date(2026, 5, 1))

    delete_stmt = db.execute.await_args_list[6].args[0]
    assert "DELETE FROM insights" in str(delete_stmt)
    assert "generated_for_date" in str(delete_stmt)

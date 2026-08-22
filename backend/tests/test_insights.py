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
from app.services.insight_service import (
    _lag_onset_feature,
    _parse_uuid,
    calculate_insight_maturity,
    get_insight_event_windows,
    get_insight_maturity,
    list_insights,
    list_latest_insights,
    newest_insight_per_subject_stmt,
)
from tests.conftest import make_user


def _scalar_optional_result(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _dismissal_filter_executes(
    *,
    pref_keys: list[str] | None = None,
    subject_keys: list[str] | None = None,
) -> list[MagicMock]:
    """DB executes used by migrate + subject/uuid dismissal filters in list_latest."""
    return [
        _scalar_optional_result(pref_keys),
        _rows_result([(key,) for key in (subject_keys or [])]),
        _scalar_optional_result(pref_keys),
    ]


def _patch_dismissal_filters(
    *,
    subject_keys: set[str] | None = None,
    uuid_keys: set[str] | None = None,
):
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        with (
            patch(
                "app.services.insight_dismissal_service.migrate_uuid_prefs_to_subject_dismissals",
                new=AsyncMock(return_value=0),
            ),
            patch(
                "app.services.insight_dismissal_service.list_dismissed_subject_keys",
                new=AsyncMock(return_value=subject_keys or set()),
            ),
            patch(
                "app.services.insight_dismissal_service.dismissed_uuid_keys_remaining",
                new=AsyncMock(return_value=uuid_keys or set()),
            ),
        ):
            yield

    return _ctx()


def _scalars_result(values: list[object]) -> MagicMock:
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _rows_result(values: list[tuple[object, ...]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values
    return result


def _make_insight(
    user: User,
    *,
    generated_at: datetime | None = None,
    insight_type: InsightType = InsightType.SPEARMAN,
    tier: InsightTier = InsightTier.DEVELOPING,
    metric: str = "mood_score",
    subject_type: str | None = "metric",
    subject_id: uuid.UUID | None = None,
    subject_label: str | None = "energy",
    payload: dict[str, object] | None = None,
    statement: str = "Mood currently lines up with energy in your entries.",
) -> Insight:
    now = generated_at or datetime.now(UTC)
    insight = Insight()
    insight.id = uuid.uuid4()
    insight.user_id = user.id
    insight.insight_type = insight_type
    insight.tier = tier
    insight.metric = metric
    insight.subject_type = subject_type
    insight.subject_id = subject_id
    insight.subject_label = subject_label
    insight.effect_size = 0.42
    insight.confidence = 0.61
    insight.sample_n = 18
    insight.statement_enc = statement
    insight.flags = {"medical_disclaimer_required": True, "causal_claim": False}
    insight.payload = payload or {"window_days": 30}
    insight.generated_for_date = date(2026, 5, 12)
    insight.generated_at = now
    insight.created_at = now
    insight.updated_at = now
    return insight


@pytest.mark.parametrize(
    ("entry_count", "phase", "phase_index", "next_phase_at", "entries_until_next"),
    [
        (1, "collecting", 1, 7, 6),
        (6, "collecting", 1, 7, 1),
        (7, "early_patterns", 2, 14, 7),
        (13, "early_patterns", 2, 14, 1),
        (14, "provisional", 3, 30, 16),
        (29, "provisional", 3, 30, 1),
        (30, "robust", 4, None, None),
        (45, "robust", 4, None, None),
    ],
)
def test_calculate_insight_maturity_boundaries(
    entry_count: int,
    phase: str,
    phase_index: int,
    next_phase_at: int | None,
    entries_until_next: int | None,
) -> None:
    maturity = calculate_insight_maturity(entry_count)

    assert maturity.phase == phase
    assert maturity.phase_index == phase_index
    assert maturity.current_entries == entry_count
    assert maturity.next_phase_at == next_phase_at
    assert maturity.entries_until_next == entries_until_next
    assert maturity.user_message_key == f"maturity.{phase}.description"


@pytest.mark.asyncio
async def test_get_insight_maturity_counts_distinct_entry_days() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(14))

    maturity = await get_insight_maturity(db, user_id=user.id)

    assert maturity.phase == "provisional"
    stmt = db.execute.await_args.args[0]
    assert "count(distinct(entries.entry_date))" in str(stmt).lower()
    assert "entries.user_id = :user_id_1" in str(stmt.whereclause)


@pytest.mark.asyncio
async def test_list_insights_filters_by_user_and_orders_newest() -> None:
    user = make_user()
    rows = [_make_insight(user)]
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result(rows),
            _rows_result([]),
        ]
    )

    out = await list_insights(db, user_id=user.id, limit=500)

    assert out == rows
    stmt = db.execute.await_args_list[0].args[0]
    assert "insights.user_id = :user_id_1" in str(stmt.whereclause)
    assert "ORDER BY insights.generated_at DESC" in str(stmt)
    assert stmt._limit_clause.value == 200


@pytest.mark.asyncio
async def test_list_insights_omits_analytics_excluded_tag_subjects() -> None:
    user = make_user()
    kept_tag_id = uuid.uuid4()
    excluded_tag_id = uuid.uuid4()
    kept = _make_insight(
        user,
        insight_type=InsightType.POINTBISERIAL,
        subject_type="tag",
        subject_id=kept_tag_id,
        subject_label="Sport",
        payload={"tag_slug": "sport"},
    )
    excluded = _make_insight(
        user,
        insight_type=InsightType.POINTBISERIAL,
        subject_type="tag",
        subject_id=excluded_tag_id,
        subject_label="Medication",
        payload={"tag_slug": "medication"},
    )
    metric = _make_insight(user, subject_type="metric", subject_label="energy")
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([excluded, kept, metric]),
            _rows_result([(excluded_tag_id, "medication")]),
            _rows_result([(excluded_tag_id, "medication")]),
        ]
    )

    out = await list_insights(db, user_id=user.id, limit=50)

    assert out == [kept, metric]


@pytest.mark.asyncio
async def test_list_latest_insights_deduplicates_by_subject() -> None:
    user = make_user()
    tag_id = uuid.uuid4()
    newest_tag = _make_insight(
        user,
        generated_at=datetime(2026, 5, 12, tzinfo=UTC),
        insight_type=InsightType.POINTBISERIAL,
        subject_type="tag",
        subject_id=tag_id,
        subject_label="Sport",
    )
    older_same_tag = _make_insight(
        user,
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
        insight_type=InsightType.POINTBISERIAL,
        subject_type="tag",
        subject_id=tag_id,
        subject_label="Sport",
    )
    metric = _make_insight(
        user,
        generated_at=datetime(2026, 5, 10, tzinfo=UTC),
        insight_type=InsightType.SPEARMAN,
        subject_type="metric",
        subject_label="stress",
    )
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([newest_tag, older_same_tag, metric]),
            _rows_result([]),
            _rows_result([(tag_id, "sport")]),
        ]
    )

    with _patch_dismissal_filters():
        out = await list_latest_insights(db, user_id=user.id, limit=10)

    assert out == [newest_tag, metric]


def test_newest_insight_per_subject_stmt_collapses_per_subject_in_sql() -> None:
    """#725: the /latest fetch must collapse to the newest row per subject in SQL.

    Insights accumulate across generation dates, so a plain "newest N rows" fetch
    could starve a subject (e.g. hiding the correlation matrix). The window must
    partition per subject and stay at least as fine as the Python dedupe by also
    splitting on ``payload`` (lag / lasso variants share a subject id).
    """
    from sqlalchemy.dialects import postgresql

    stmt = newest_insight_per_subject_stmt(uuid.uuid4())
    sql = str(stmt.compile(dialect=postgresql.dialect()))

    assert "row_number() OVER" in sql
    partition = sql.split("PARTITION BY", 1)[1].split("ORDER BY", 1)[0]
    for column in (
        "insight_type",
        "metric",
        "subject_type",
        "subject_id",
        "payload",
    ):
        assert column in partition, f"partition must split on {column}"


@pytest.mark.asyncio
async def test_list_latest_insights_deduplicates_legacy_tag_overrides_by_loaded_slug() -> None:
    user = make_user()
    default_id = uuid.uuid4()
    override_id = uuid.uuid4()
    newest_override = _make_insight(
        user,
        generated_at=datetime(2026, 5, 12, tzinfo=UTC),
        insight_type=InsightType.POINTBISERIAL,
        metric="mood",
        subject_type="tag",
        subject_id=override_id,
        subject_label="Alkohol",
    )
    older_default = _make_insight(
        user,
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
        insight_type=InsightType.POINTBISERIAL,
        metric="mood_score",
        subject_type="tag",
        subject_id=default_id,
        subject_label="Alcohol",
    )
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([newest_override, older_default]),
            _rows_result([]),
            _rows_result([(default_id, "alcohol"), (override_id, "alcohol")]),
        ]
    )

    with _patch_dismissal_filters():
        out = await list_latest_insights(db, user_id=user.id, limit=10)

    assert out == [newest_override]


@pytest.mark.asyncio
async def test_list_latest_insights_deduplicates_tag_overrides_by_slug() -> None:
    user = make_user()
    newest_override = _make_insight(
        user,
        generated_at=datetime(2026, 5, 12, tzinfo=UTC),
        insight_type=InsightType.POINTBISERIAL,
        subject_type="tag",
        subject_id=uuid.uuid4(),
        subject_label="Alkohol",
        payload={"tag_slug": "alcohol"},
    )
    older_default = _make_insight(
        user,
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
        insight_type=InsightType.POINTBISERIAL,
        subject_type="tag",
        subject_id=uuid.uuid4(),
        subject_label="Alcohol",
        payload={"tag_slug": "alcohol"},
    )
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([newest_override, older_default]),
            _rows_result([]),
        ]
    )

    with _patch_dismissal_filters():
        out = await list_latest_insights(db, user_id=user.id, limit=10)

    assert out == [newest_override]


@pytest.mark.asyncio
async def test_insights_endpoint_returns_statement_field(
    async_client: AsyncClient,
    user: User,
) -> None:
    insight = _make_insight(user, statement="Energy and mood currently move together.")

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with (
            patch(
                "app.api.v1.endpoints.insights.list_insights",
                new_callable=AsyncMock,
                return_value=[insight],
            ),
            patch(
                "app.api.v1.endpoints.insights.get_insight_maturity",
                new_callable=AsyncMock,
                return_value=calculate_insight_maturity(18),
            ),
        ):
            response = await async_client.get(
                "/api/v1/insights?limit=5",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["insights"]) == 1
    item = body["insights"][0]
    assert item["statement"] == "Energy and mood currently move together."
    assert "statement_enc" not in item
    assert item["tier"] == "developing"
    assert item["flags"]["causal_claim"] is False
    maturity = body["insight_maturity"]
    assert maturity["phase"] == "provisional"
    assert maturity["current_entries"] == 18
    assert maturity["next_phase_at"] == 30


@pytest.mark.asyncio
async def test_list_latest_insights_keeps_lasso_and_lag_symptom_cluster_findings() -> None:
    user = make_user()
    lasso = _make_insight(
        user,
        generated_at=datetime(2026, 5, 12, 3, tzinfo=UTC),
        insight_type=InsightType.SYMPTOM_CLUSTER,
        metric="mood_score",
        subject_type="metric",
        subject_label="mood_score",
        payload={"method": "lasso", "target": "mood_score"},
    )
    lag = _make_insight(
        user,
        generated_at=datetime(2026, 5, 12, 2, tzinfo=UTC),
        insight_type=InsightType.SYMPTOM_CLUSTER,
        metric="mood_score",
        subject_type="metric",
        subject_label="mood_score",
        payload={
            "method": "lag",
            "target": {"kind": "metric", "key": "mood_score"},
            "feature": {"kind": "tag", "key": "tag:sport", "id": str(uuid.uuid4())},
            "lag_days": 1,
        },
    )
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([lasso, lag]),
            _rows_result([]),
        ]
    )

    with _patch_dismissal_filters():
        out = await list_latest_insights(db, user_id=user.id, limit=10)

    assert out == [lasso, lag]


@pytest.mark.asyncio
async def test_list_latest_insights_excludes_dismissed_uuid_keys() -> None:
    user = make_user()
    kept = _make_insight(
        user,
        generated_at=datetime(2026, 5, 12, tzinfo=UTC),
        insight_type=InsightType.SPEARMAN,
        subject_type="metric",
        subject_label="energy",
    )
    dismissed = _make_insight(
        user,
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
        insight_type=InsightType.SPEARMAN,
        subject_type="metric",
        subject_label="stress",
    )
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([kept, dismissed]),
            _rows_result([]),
        ]
    )

    with _patch_dismissal_filters(uuid_keys={str(dismissed.id)}):
        out = await list_latest_insights(db, user_id=user.id, limit=10)

    assert out == [kept]


@pytest.mark.asyncio
async def test_list_latest_insights_excludes_subject_stable_dismissals() -> None:
    user = make_user()
    kept = _make_insight(
        user,
        generated_at=datetime(2026, 5, 12, tzinfo=UTC),
        subject_type="metric",
        subject_label="energy",
    )
    hidden = _make_insight(
        user,
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
        subject_type="metric",
        subject_label="stress",
    )
    from app.services.insight_service import insight_subject_key

    subject_key = insight_subject_key(hidden, tag_slugs_by_id={})
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([kept, hidden]),
            _rows_result([]),
        ]
    )

    with _patch_dismissal_filters(subject_keys={subject_key}):
        out = await list_latest_insights(db, user_id=user.id, limit=10)

    assert out == [kept]


@pytest.mark.asyncio
async def test_latest_insights_endpoint_uses_latest_service(
    async_client: AsyncClient,
    user: User,
) -> None:
    row = _make_insight(
        user,
        generated_at=datetime.now(UTC) - timedelta(days=1),
        insight_type=InsightType.WEEKDAY_PATTERN,
        subject_type="weekday",
        subject_label="Monday",
    )

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with (
            patch(
                "app.api.v1.endpoints.insights.list_latest_insights",
                new_callable=AsyncMock,
                return_value=[row],
            ) as latest,
            patch(
                "app.api.v1.endpoints.insights.get_insight_maturity",
                new_callable=AsyncMock,
                return_value=calculate_insight_maturity(30),
            ),
        ):
            response = await async_client.get(
                "/api/v1/insights/latest?limit=3",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    latest.assert_awaited_once()
    body = response.json()
    assert body["insights"][0]["insight_type"] == "weekday_pattern"
    assert body["insight_maturity"]["phase"] == "robust"


@pytest.mark.asyncio
async def test_regenerate_insights_endpoint_returns_payload(
    async_client: AsyncClient,
    user: User,
) -> None:
    from datetime import date

    from app.services.insight_worker_service import InsightPipelineResult

    payload = InsightPipelineResult(
        generated_for_date=date(2026, 7, 13),
        insight_count=5,
        tag_clusters_status="ok",
        trigger_source="user_regenerate",
    )

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with (
            patch(
                "app.api.v1.endpoints.insights.try_acquire_regenerate_slot",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.insights.regenerate_insights_for_user",
                new_callable=AsyncMock,
                return_value=payload,
            ) as regenerate,
        ):
            response = await async_client.post(
                "/api/v1/insights/regenerate",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    regenerate.assert_awaited_once()
    body = response.json()
    assert body["insight_count"] == 5
    assert body["tag_clusters_status"] == "ok"
    assert body["trigger_source"] == "user_regenerate"


@pytest.mark.asyncio
async def test_regenerate_insights_endpoint_rate_limited(
    async_client: AsyncClient,
    user: User,
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.insights.try_acquire_regenerate_slot",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = await async_client.post(
                "/api/v1/insights/regenerate",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_regenerate_insights_endpoint_rejects_disabled_analytics(
    async_client: AsyncClient,
    user: User,
) -> None:
    from app.db.redis_client import get_redis
    from app.services.insight_worker_service import AnalyticsDisabledError

    async def override() -> User:
        return user

    redis = AsyncMock()
    redis.delete = AsyncMock()

    async def redis_override():
        yield redis

    app.dependency_overrides[get_current_verified_user] = override
    app.dependency_overrides[get_redis] = redis_override
    try:
        with (
            patch(
                "app.api.v1.endpoints.insights.try_acquire_regenerate_slot",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.insights.regenerate_insights_for_user",
                new_callable=AsyncMock,
                side_effect=AnalyticsDisabledError(user.id),
            ),
        ):
            response = await async_client.post(
                "/api/v1/insights/regenerate",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    redis.delete.assert_awaited_once_with(f"insight:regenerate:{user.id}")


@pytest.mark.asyncio
async def test_regenerate_insights_endpoint_returns_friendly_error_on_unexpected_failure(
    async_client: AsyncClient,
    user: User,
) -> None:
    """#754: an unclassified worker/DB failure surfaces a friendly 503, not a raw 500,
    and frees the hourly cooldown slot instead of penalizing the user for it.
    """
    from app.db.redis_client import get_redis

    async def override() -> User:
        return user

    redis = AsyncMock()
    redis.delete = AsyncMock()

    async def redis_override():
        yield redis

    app.dependency_overrides[get_current_verified_user] = override
    app.dependency_overrides[get_redis] = redis_override
    try:
        with (
            patch(
                "app.api.v1.endpoints.insights.try_acquire_regenerate_slot",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.insights.regenerate_insights_for_user",
                new_callable=AsyncMock,
                side_effect=RuntimeError("db exploded"),
            ),
        ):
            response = await async_client.post(
                "/api/v1/insights/regenerate",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "try again" in response.json()["detail"].lower()
    redis.delete.assert_awaited_once_with(f"insight:regenerate:{user.id}")


@pytest.mark.asyncio
async def test_regenerate_insights_endpoint_keeps_cooldown_during_lock_contention(
    async_client: AsyncClient,
    user: User,
) -> None:
    """Expected lock contention returns a retryable 503 without a retry storm."""

    from app.db.redis_client import get_redis
    from app.services.insight_engine import InsightLockTimeoutError

    async def override() -> User:
        return user

    redis = AsyncMock()
    redis.delete = AsyncMock()

    async def redis_override():
        yield redis

    app.dependency_overrides[get_current_verified_user] = override
    app.dependency_overrides[get_redis] = redis_override
    try:
        with (
            patch(
                "app.api.v1.endpoints.insights.try_acquire_regenerate_slot",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.insights.regenerate_insights_for_user",
                new_callable=AsyncMock,
                side_effect=InsightLockTimeoutError("held by another run"),
            ),
        ):
            response = await async_client.post(
                "/api/v1/insights/regenerate",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["retry-after"] == "3600"
    assert "already being refreshed" in response.json()["detail"].lower()
    redis.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_insights_endpoint_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/insights")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_insight_event_windows_endpoint_returns_payload(
    async_client: AsyncClient,
    user: User,
) -> None:
    from app.schemas.insight import InsightEventWindow, InsightEventWindowsResponse
    from app.schemas.stats import TimeseriesPoint

    insight_id = uuid.uuid4()
    payload = InsightEventWindowsResponse(
        range="90d",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 6, 30),
        events=[InsightEventWindow(onset=date(2026, 5, 10), label="Sport")],
        points=[
            TimeseriesPoint(
                period_start=date(2026, 5, 10),
                period_end=date(2026, 5, 10),
                entry_count=1,
                mood_avg=3.5,
                energy_avg=3.0,
                stress_avg=2.0,
            )
        ],
    )
    get_windows = AsyncMock(return_value=payload)

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.insights.get_insight_event_windows",
            new=get_windows,
        ):
            response = await async_client.get(
                f"/api/v1/insights/{insight_id}/event-windows?range=90d",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["range"] == "90d"
    assert body["events"][0]["onset"] == "2026-05-10"
    assert body["points"][0]["mood_avg"] == 3.5
    get_windows.assert_awaited_once()


@pytest.mark.asyncio
async def test_insight_event_windows_accepts_7d_range(
    async_client: AsyncClient,
    user: User,
) -> None:
    from app.schemas.insight import InsightEventWindowsResponse

    insight_id = uuid.uuid4()
    payload = InsightEventWindowsResponse(
        range="7d",
        start_date=date(2026, 6, 24),
        end_date=date(2026, 6, 30),
        events=[],
        points=[],
    )
    get_windows = AsyncMock(return_value=payload)

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.insights.get_insight_event_windows",
            new=get_windows,
        ):
            response = await async_client.get(
                f"/api/v1/insights/{insight_id}/event-windows?range=7d",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["range"] == "7d"
    get_windows.assert_awaited_once()


# --- #488: lag-aware event windows -----------------------------------------


def test_lag_onset_feature_extracts_feature_and_lag_days() -> None:
    user = make_user()
    insight = _make_insight(
        user,
        insight_type=InsightType.SYMPTOM_CLUSTER,
        subject_type="symptom",
        subject_label="Fatigue",
        payload={
            "method": "lag",
            "feature": {"kind": "tag", "slug": "cycling", "name": "Cycling"},
            "target": {"kind": "symptom", "name": "Fatigue"},
            "lag_days": 2,
        },
    )

    result = _lag_onset_feature(insight)

    assert result is not None
    feature, lag_days = result
    assert feature["slug"] == "cycling"
    assert lag_days == 2


def test_lag_onset_feature_none_for_non_lag_or_malformed() -> None:
    user = make_user()
    assert _lag_onset_feature(_make_insight(user, payload={"method": "spearman"})) is None
    # method=lag but lag_days missing → not a usable lag window.
    assert (
        _lag_onset_feature(
            _make_insight(user, payload={"method": "lag", "feature": {"kind": "tag"}})
        )
        is None
    )


def test_parse_uuid_roundtrips_and_rejects_junk() -> None:
    value = uuid.uuid4()
    assert _parse_uuid(value) == value
    assert _parse_uuid(str(value)) == value
    assert _parse_uuid("not-a-uuid") is None
    assert _parse_uuid(None) is None


@pytest.mark.asyncio
async def test_get_insight_event_windows_lag_aligns_on_feature() -> None:
    user = make_user()
    insight = _make_insight(
        user,
        insight_type=InsightType.SYMPTOM_CLUSTER,
        subject_type="symptom",  # subject = the outcome/target
        subject_label="Fatigue",
        payload={
            "method": "lag",
            "feature": {"kind": "tag", "slug": "cycling", "name": "Cycling"},
            "target": {"kind": "symptom", "name": "Fatigue"},
            "lag_days": 2,
        },
    )
    onset_dates = [date(2026, 5, 1), date(2026, 5, 5)]
    timeseries = MagicMock()
    timeseries.points = []
    db = AsyncMock()

    with (
        patch(
            "app.services.insight_service.get_insight_by_id",
            AsyncMock(return_value=insight),
        ),
        patch(
            "app.services.insight_service._analytics_enabled",
            AsyncMock(return_value=True),
        ),
        patch(
            "app.services.insight_service._analytics_excluded_tag_keys",
            AsyncMock(return_value=(set(), set())),
        ),
        patch(
            "app.services.insight_service.list_historical_tag_presence_dates_by_slug",
            AsyncMock(return_value=onset_dates),
        ) as presence,
        patch(
            "app.services.insight_service.get_timeseries",
            AsyncMock(return_value=timeseries),
        ),
    ):
        response = await get_insight_event_windows(
            db,
            user_id=user.id,
            insight_id=insight.id,
            range_="90d",
        )

    # Onsets are the feature's occurrences (labelled with the feature), and the
    # response carries lag_days so the sheet can mark t = +lag_days.
    assert [event.onset for event in response.events] == onset_dates
    assert response.events[0].label == "Cycling"
    assert response.lag_days == 2
    # Resolved via the feature slug, not the subject (outcome).
    presence.assert_awaited_once()
    assert presence.await_args.kwargs["tag_slug"] == "cycling"


@pytest.mark.asyncio
async def test_get_insight_event_windows_lag_respects_analytics_exclusion() -> None:
    # #581: a lag insight stores the tag as payload.feature, so it is not
    # subject-filtered; the feature-aligned path must still honour the tag's
    # include_in_analytics=False setting instead of leaking its presence dates.
    user = make_user()
    insight = _make_insight(
        user,
        insight_type=InsightType.SYMPTOM_CLUSTER,
        subject_type="symptom",
        subject_label="Fatigue",
        payload={
            "method": "lag",
            "feature": {"kind": "tag", "slug": "cycling", "name": "Cycling"},
            "target": {"kind": "symptom", "name": "Fatigue"},
            "lag_days": 2,
        },
    )
    timeseries = MagicMock()
    timeseries.points = []
    db = AsyncMock()

    with (
        patch(
            "app.services.insight_service.get_insight_by_id",
            AsyncMock(return_value=insight),
        ),
        patch(
            "app.services.insight_service._analytics_enabled",
            AsyncMock(return_value=True),
        ),
        patch(
            "app.services.insight_service._analytics_excluded_tag_keys",
            AsyncMock(return_value=(set(), {"cycling"})),
        ),
        patch(
            "app.services.insight_service.list_historical_tag_presence_dates_by_slug",
            AsyncMock(return_value=[date(2026, 5, 1)]),
        ) as presence,
        patch(
            "app.services.insight_service.get_timeseries",
            AsyncMock(return_value=timeseries),
        ),
    ):
        response = await get_insight_event_windows(
            db,
            user_id=user.id,
            insight_id=insight.id,
            range_="90d",
        )

    # Excluded feature tag → no windows surfaced, and we never query its dates.
    assert response.events == []
    assert response.lag_days == 2
    presence.assert_not_awaited()

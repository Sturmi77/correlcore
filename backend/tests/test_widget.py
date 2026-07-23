"""Tests for GET /api/v1/widget/summary (M11 Sprint 4)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.entry import EntrySlot
from app.models.user import User
from app.schemas.widget import WidgetSummaryResponse
from app.services.widget_service import (
    UTC_ZONE,
    _next_suggested_at,
    _suggest_hour_from_history,
    get_widget_summary,
    resolve_zone,
)
from tests.conftest import make_user


def _scalar_one_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _all_result(value: object) -> MagicMock:
    result = MagicMock()
    result.all.return_value = value
    return result


def test_suggest_hour_from_history_uses_modal_created_at_hour() -> None:
    rows = [
        (datetime(2026, 7, 1, 19, 0, tzinfo=UTC), EntrySlot.DAY),
        (datetime(2026, 7, 2, 19, 30, tzinfo=UTC), EntrySlot.DAY),
        (datetime(2026, 7, 3, 8, 0, tzinfo=UTC), EntrySlot.MORNING),
        (datetime(2026, 7, 4, 19, 15, tzinfo=UTC), EntrySlot.DAY),
    ]
    assert _suggest_hour_from_history(rows) == 19


def test_suggest_hour_from_history_empty() -> None:
    assert _suggest_hour_from_history([]) is None


def test_next_suggested_at_rolls_to_tomorrow_when_entry_exists() -> None:
    now = datetime(2026, 7, 18, 10, 0, tzinfo=UTC)
    out = _next_suggested_at(now=now, has_entry_today=True, suggest_hour=19)
    assert out == datetime(2026, 7, 19, 19, 0, tzinfo=UTC)


def test_next_suggested_at_stays_today_when_future_and_no_entry() -> None:
    now = datetime(2026, 7, 18, 10, 0, tzinfo=UTC)
    out = _next_suggested_at(now=now, has_entry_today=False, suggest_hour=19)
    assert out == datetime(2026, 7, 18, 19, 0, tzinfo=UTC)


def test_next_suggested_at_rolls_when_hour_already_passed() -> None:
    now = datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    out = _next_suggested_at(now=now, has_entry_today=False, suggest_hour=19)
    assert out == datetime(2026, 7, 19, 19, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_get_widget_summary_aggregates_mood_and_suggestion() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_result(1),
            _scalar_one_result(3.456),
            _all_result(
                [
                    (datetime(2026, 7, 17, 19, 0, tzinfo=UTC), EntrySlot.DAY),
                    (datetime(2026, 7, 16, 19, 10, tzinfo=UTC), EntrySlot.DAY),
                ]
            ),
        ]
    )

    out = await get_widget_summary(
        db,
        user_id=user.id,
        now=datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
    )

    assert out.has_entry is True
    assert out.mood_avg_7d == 3.46
    assert out.suggested_next_entry_at == datetime(2026, 7, 19, 19, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_get_widget_summary_empty_history_defaults_evening() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_result(0),
            _scalar_one_result(None),
            _all_result([]),
        ]
    )

    out = await get_widget_summary(
        db,
        user_id=user.id,
        now=datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
    )

    assert out.has_entry is False
    assert out.mood_avg_7d is None
    assert out.suggested_next_entry_at == datetime(2026, 7, 18, 19, 0, tzinfo=UTC)


def test_suggest_hour_uses_local_hour_not_utc() -> None:
    # 02:00 UTC is the previous evening (19:00) in Los Angeles.
    rows = [
        (datetime(2026, 7, 18, 2, 0, tzinfo=UTC), EntrySlot.DAY),
        (datetime(2026, 7, 17, 2, 30, tzinfo=UTC), EntrySlot.DAY),
    ]
    assert _suggest_hour_from_history(rows) == 2
    assert _suggest_hour_from_history(rows, ZoneInfo("America/Los_Angeles")) == 19


def test_next_suggested_at_keeps_wall_clock_hour_across_dst() -> None:
    # US DST ends 2026-11-01; adding 24h would land on 18:00 local.
    zone = ZoneInfo("America/Los_Angeles")
    now = datetime(2026, 11, 1, 3, 0, tzinfo=UTC)  # 2026-10-31 20:00 local
    out = _next_suggested_at(now=now, has_entry_today=True, suggest_hour=19, zone=zone)
    assert out is not None
    assert out.astimezone(zone).hour == 19
    assert out.astimezone(zone).date() == date(2026, 11, 1)


@pytest.mark.asyncio
async def test_get_widget_summary_uses_local_day_for_has_entry() -> None:
    """#445: a US evening after 00:00 UTC must not roll the widget to tomorrow."""

    user = make_user()
    statements: list[object] = []
    db = MagicMock()

    async def _execute(stmt: object) -> MagicMock:
        statements.append(stmt)
        return [
            _scalar_one_result(1),
            _scalar_one_result(4.0),
            _all_result([(datetime(2026, 7, 19, 2, 0, tzinfo=UTC), EntrySlot.DAY)]),
        ][len(statements) - 1]

    db.execute = AsyncMock(side_effect=_execute)

    # 2026-07-19 03:00 UTC is still 2026-07-18 20:00 in Los Angeles.
    out = await get_widget_summary(
        db,
        user_id=user.id,
        now=datetime(2026, 7, 19, 3, 0, tzinfo=UTC),
        tz="America/Los_Angeles",
    )

    compiled = str(statements[0].compile(compile_kwargs={"literal_binds": True}))  # type: ignore[attr-defined]
    assert "2026-07-18" in compiled, compiled
    assert "2026-07-19" not in compiled, compiled

    assert out.has_entry is True
    # Suggestion is tomorrow 19:00 *local* = 2026-07-20 02:00 UTC, not 19:00 UTC.
    assert out.suggested_next_entry_at == datetime(2026, 7, 20, 2, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_get_widget_summary_without_tz_stays_on_utc() -> None:
    user = make_user()
    statements: list[object] = []
    db = MagicMock()

    async def _execute(stmt: object) -> MagicMock:
        statements.append(stmt)
        return [
            _scalar_one_result(0),
            _scalar_one_result(None),
            _all_result([]),
        ][len(statements) - 1]

    db.execute = AsyncMock(side_effect=_execute)

    await get_widget_summary(
        db,
        user_id=user.id,
        now=datetime(2026, 7, 19, 3, 0, tzinfo=UTC),
    )

    compiled = str(statements[0].compile(compile_kwargs={"literal_binds": True}))  # type: ignore[attr-defined]
    assert "2026-07-19" in compiled, compiled


def test_resolve_zone_falls_back_to_utc_for_unusable_names() -> None:
    assert resolve_zone("America/Los_Angeles").key == "America/Los_Angeles"
    assert resolve_zone(None) is UTC_ZONE
    assert resolve_zone("") is UTC_ZONE
    assert resolve_zone("Mars/Olympus_Mons") is UTC_ZONE
    # Path-traversal-ish input must not escape the tzdata lookup.
    assert resolve_zone("../../etc/passwd") is UTC_ZONE


@pytest.mark.asyncio
async def test_widget_summary_endpoint_forwards_timezone(
    async_client: AsyncClient,
) -> None:
    user = make_user()
    app.dependency_overrides[get_current_verified_user] = lambda: user
    try:
        with patch(
            "app.api.v1.endpoints.widget.get_widget_summary",
            new=AsyncMock(
                return_value=WidgetSummaryResponse(
                    has_entry=False, mood_avg_7d=None, suggested_next_entry_at=None
                )
            ),
        ) as mocked:
            response = await async_client.get(
                "/api/v1/widget/summary", params={"tz": "America/Los_Angeles"}
            )
        assert response.status_code == 200
        assert mocked.await_args is not None
        assert mocked.await_args.kwargs["tz"] == "America/Los_Angeles"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_widget_summary_endpoint_returns_payload(
    async_client: AsyncClient,
    user: User,
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.widget.get_widget_summary",
            new_callable=AsyncMock,
            return_value=WidgetSummaryResponse(
                has_entry=False,
                mood_avg_7d=3.25,
                suggested_next_entry_at=datetime(2026, 7, 18, 19, 0, tzinfo=UTC),
            ),
        ) as summary:
            response = await async_client.get(
                "/api/v1/widget/summary",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    summary.assert_awaited_once()
    body = response.json()
    assert body["has_entry"] is False
    assert body["mood_avg_7d"] == 3.25
    assert body["suggested_next_entry_at"] == "2026-07-18T19:00:00Z"
    assert len(response.content) < 1024


@pytest.mark.asyncio
async def test_widget_summary_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/widget/summary")
    assert response.status_code in (401, 403)

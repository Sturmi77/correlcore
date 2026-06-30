"""Tests for M5 habit statistics."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.user import User
from app.schemas.habit import HabitListResponse, HabitStatsResponse
from app.services.habit_service import HabitNotFoundError, get_habit_stats, list_habit_stats
from tests.conftest import make_tag, make_user


def _scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_result(values: list[object]) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _row_one_result(value: object | None) -> MagicMock:
    result = MagicMock()
    result.one_or_none.return_value = value
    return result


def _row_result(values: list[tuple[object, ...]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values
    return result


@pytest.mark.asyncio
async def test_habit_stats_build_uses_target_frequency() -> None:
    user = make_user()
    habit = make_tag(user, habit_type="build", target_frequency=3)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(habit),
            _row_result([(date(2026, 5, 1),), (date(2026, 5, 2),)]),
            _row_one_result((0.42, "mood_score")),
        ]
    )

    out = await get_habit_stats(
        db,
        user_id=user.id,
        tag_id=habit.id,
        window=7,
        as_of=date(2026, 5, 7),
    )

    assert out.target_days == 3
    assert out.days_tracked == 2
    assert out.adherence_rate == 66.7
    assert out.correlation_score == 0.42
    assert out.correlation_metric == "mood"


@pytest.mark.asyncio
async def test_habit_stats_reduce_stays_full_when_within_target() -> None:
    user = make_user()
    habit = make_tag(user, habit_type="reduce", target_frequency=2)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(habit),
            _row_result([(date(2026, 5, 1),), (date(2026, 5, 2),)]),
            _row_one_result(None),
        ]
    )

    out = await get_habit_stats(
        db,
        user_id=user.id,
        tag_id=habit.id,
        window=7,
        as_of=date(2026, 5, 7),
    )

    assert out.target_days == 2
    assert out.days_tracked == 2
    assert out.adherence_rate == 100
    assert out.correlation_score is None


@pytest.mark.asyncio
async def test_habit_stats_reduce_decreases_after_target_range() -> None:
    user = make_user()
    habit = make_tag(user, habit_type="reduce", target_frequency=2)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(habit),
            _row_result(
                [
                    (date(2026, 5, 1),),
                    (date(2026, 5, 2),),
                    (date(2026, 5, 3),),
                ]
            ),
            _row_one_result(None),
        ]
    )

    out = await get_habit_stats(
        db,
        user_id=user.id,
        tag_id=habit.id,
        window=7,
        as_of=date(2026, 5, 7),
    )

    assert out.adherence_rate == 80


@pytest.mark.asyncio
async def test_habit_stats_raises_for_non_habit() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))

    with pytest.raises(HabitNotFoundError):
        await get_habit_stats(db, user_id=user.id, tag_id=uuid.uuid4(), window=28)


@pytest.mark.asyncio
async def test_list_habit_stats_returns_all_habits() -> None:
    user = make_user()
    habit = make_tag(user, habit_type="build", target_frequency=4)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([habit]),
            _scalar_result(habit),
            _row_result([]),
            _row_one_result(None),
        ]
    )

    out = await list_habit_stats(db, user_id=user.id, window=14, as_of=date(2026, 5, 14))

    assert len(out.habits) == 1
    assert out.habits[0].window == 14
    assert out.habits[0].target_days == 8


@pytest.mark.asyncio
async def test_get_habits_endpoint(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    response = HabitListResponse(
        habits=[
            HabitStatsResponse(
                tag_id=uuid.uuid4(),
                habit_type="build",
                target_frequency=4,
                window=28,
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 28),
                days_tracked=10,
                days_total=28,
                target_days=16,
                adherence_rate=62.5,
                correlation_score=None,
            )
        ]
    )

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.habits.list_habit_stats",
            new_callable=AsyncMock,
            return_value=response,
        ):
            r = await async_client.get(
                "/api/v1/habits?window=28",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json()["habits"][0]["adherence_rate"] == 62.5


@pytest.mark.asyncio
async def test_get_habit_stats_endpoint_404(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.habits.get_habit_stats",
            new_callable=AsyncMock,
            side_effect=HabitNotFoundError("missing"),
        ):
            r = await async_client.get(
                f"/api/v1/habits/{uuid.uuid4()}/stats",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 404

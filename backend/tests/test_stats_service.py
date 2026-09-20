"""Tests for M2 visualization statistics."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.tag import TagCategory
from app.services.stats_service import (
    get_symptom_heatmap,
    get_tag_heatmap,
    get_timeseries,
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


@pytest.mark.asyncio
async def test_timeseries_week_fills_missing_days() -> None:
    user = make_user()
    as_of = date(2026, 5, 9)
    entries = [
        make_entry(user, entry_date=as_of - timedelta(days=1), mood_score=4, energy=3, stress=2),
        make_entry(user, entry_date=as_of, mood_score=2, energy=5, stress=4),
    ]
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(entries))

    out = await get_timeseries(db, user_id=user.id, range_="week", as_of=as_of)

    assert len(out.points) == 7
    assert out.points[-1].period_start == as_of
    assert out.points[-1].mood_avg == 2
    assert out.points[0].entry_count == 0


@pytest.mark.asyncio
async def test_timeseries_averages_only_logged_sleep_minutes() -> None:
    # Sleep duration is optional: average only days with minutes; None when absent.
    user = make_user()
    as_of = date(2026, 5, 9)
    entries = [
        make_entry(user, entry_date=as_of - timedelta(days=1), sleep_minutes=420),
        make_entry(user, entry_date=as_of, sleep_minutes=360),
    ]
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(entries))

    out = await get_timeseries(db, user_id=user.id, range_="week", as_of=as_of)

    assert out.points[-1].sleep_minutes_avg == 360
    assert out.points[-2].sleep_minutes_avg == 420
    assert out.points[0].sleep_minutes_avg is None


@pytest.mark.asyncio
async def test_timeseries_averages_only_rated_sleep_quality() -> None:
    # Sleep quality is optional: a bucket averages only the days that carry a
    # rating, and stays None when no day in it has sleep quality (#653 B2).
    user = make_user()
    as_of = date(2026, 5, 9)
    entries = [
        make_entry(user, entry_date=as_of - timedelta(days=1), sleep_quality=4),
        make_entry(user, entry_date=as_of, sleep_quality=2),
    ]
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(entries))

    out = await get_timeseries(db, user_id=user.id, range_="week", as_of=as_of)

    assert out.points[-1].sleep_quality_avg == 2
    assert out.points[-2].sleep_quality_avg == 4
    # A day with an entry but no sleep rating averages to None, not 0.
    assert out.points[0].sleep_quality_avg is None


@pytest.mark.asyncio
async def test_timeseries_quarter_returns_90_daily_points() -> None:
    user = make_user()
    as_of = date(2026, 5, 9)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result([]))

    out = await get_timeseries(db, user_id=user.id, range_="quarter", as_of=as_of)

    assert len(out.points) == 90
    assert out.points[0].period_start == as_of - timedelta(days=89)
    assert out.points[-1].period_start == as_of


@pytest.mark.asyncio
async def test_timeseries_year_returns_365_daily_points() -> None:
    user = make_user()
    as_of = date(2026, 5, 9)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result([]))

    out = await get_timeseries(db, user_id=user.id, range_="year", as_of=as_of)

    assert len(out.points) == 365
    assert out.points[0].period_start == as_of - timedelta(days=364)
    assert out.points[-1].period_start == as_of


@pytest.mark.asyncio
async def test_tag_heatmap_groups_counts_by_tag_and_day() -> None:
    user = make_user()
    sport = make_tag(user=None, is_default=True, slug="sport", name="Sport")
    focus = make_tag(user, slug="focus", name="Focus", category=TagCategory.WORK)
    entry_a = uuid.uuid4()
    entry_b = uuid.uuid4()
    entry_c = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_row_result(
            [
                (sport, entry_a, date(2026, 5, 8)),
                (sport, entry_b, date(2026, 5, 8)),
                (focus, entry_c, date(2026, 5, 9)),
            ]
        )
    )

    out = await get_tag_heatmap(
        db,
        user_id=user.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 9),
    )

    sport_payload = next(tag for tag in out.tags if tag.slug == "sport")
    assert sport_payload.days[0].date == date(2026, 5, 8)
    assert sport_payload.days[0].count == 2


@pytest.mark.asyncio
async def test_tag_heatmap_merges_default_and_override_aliases() -> None:
    user = make_user()
    default = make_tag(user=None, is_default=True, slug="alcohol", name="Alcohol")
    override = make_tag(user, slug="alcohol", name="Alkohol", category=TagCategory.CONSUMPTION)
    entry_a = uuid.uuid4()
    entry_b = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_row_result(
            [
                (default, entry_a, date(2026, 5, 8)),
                (override, entry_b, date(2026, 5, 9)),
                # Same entry linked to both IDs must count once after canonicalize.
                (default, entry_b, date(2026, 5, 9)),
            ]
        )
    )

    out = await get_tag_heatmap(
        db,
        user_id=user.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 9),
    )

    assert len(out.tags) == 1
    row = out.tags[0]
    assert row.slug == "alcohol"
    assert row.tag_id == override.id
    assert row.name == "Alkohol"
    assert [(day.date, day.count) for day in row.days] == [
        (date(2026, 5, 8), 1),
        (date(2026, 5, 9), 1),
    ]


@pytest.mark.asyncio
async def test_tag_heatmap_filters_hidden_tags() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_row_result([]))

    await get_tag_heatmap(
        db,
        user_id=user.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 9),
    )

    stmt = db.execute.await_args.args[0]
    assert "tags.is_hidden IS false" in str(stmt.whereclause)


@pytest.mark.asyncio
async def test_tag_heatmap_include_non_analytics_drops_analytics_filter() -> None:
    """The entry-form recency cloud (#898) ranks by raw usage.

    Default (trends/analytics) keeps ``include_in_analytics``; the recency mode
    drops it so a visible tag excluded from analytics still surfaces, while the
    hidden-tag guard stays in both.
    """
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_row_result([]))

    await get_tag_heatmap(
        db, user_id=user.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 9)
    )
    default_where = str(db.execute.await_args.args[0].whereclause)
    assert "include_in_analytics" in default_where
    assert "tags.is_hidden IS false" in default_where

    await get_tag_heatmap(
        db,
        user_id=user.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 9),
        include_non_analytics=True,
    )
    recency_where = str(db.execute.await_args.args[0].whereclause)
    assert "include_in_analytics" not in recency_where
    assert "tags.is_hidden IS false" in recency_where


@pytest.mark.asyncio
async def test_symptom_heatmap_groups_counts_and_max_intensity() -> None:
    user = make_user()
    headache = make_symptom(is_default=True, slug="headache", name="Headache")
    fatigue = make_symptom(user, slug="fatigue-custom", name="Fatigue")
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_row_result(
            [
                (headache, date(2026, 5, 8), 1),
                (headache, date(2026, 5, 8), 3),
                (fatigue, date(2026, 5, 9), 2),
            ]
        )
    )

    out = await get_symptom_heatmap(
        db,
        user_id=user.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 9),
    )

    headache_payload = next(symptom for symptom in out.symptoms if symptom.slug == "headache")
    assert headache_payload.name == "Headache"
    assert headache_payload.days[0].date == date(2026, 5, 8)
    assert headache_payload.days[0].count == 2
    assert headache_payload.days[0].max_intensity == 3


@pytest.mark.asyncio
async def test_symptom_heatmap_scopes_visible_symptoms_to_user() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_row_result([]))

    await get_symptom_heatmap(
        db,
        user_id=user.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 9),
    )

    stmt = db.execute.await_args.args[0]
    whereclause = str(stmt.whereclause)
    assert "entry_symptoms.user_id" in whereclause
    assert "entries.user_id" in whereclause
    assert "symptoms.is_default IS true" in whereclause


@pytest.mark.asyncio
async def test_timeseries_days_returns_the_exact_window() -> None:
    """#867: the shared analysis window must not be rounded to a legacy enum.

    `range` only offers 7/30/90/365, so 14 resolved to `week` (7 days) and 28 to
    `month` (30). Trends and Home then plotted a different population than the
    label promised.
    """
    user = make_user()
    as_of = date(2026, 5, 9)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result([]))

    for days in (14, 28, 90):
        out = await get_timeseries(db, user_id=user.id, range_="month", as_of=as_of, days=days)
        assert len(out.points) == days, f"expected {days} buckets, got {len(out.points)}"
        assert out.days == days
        assert out.points[-1].period_start == as_of
        assert (out.points[-1].period_start - out.points[0].period_start).days == days - 1


@pytest.mark.asyncio
async def test_timeseries_without_days_keeps_the_legacy_range() -> None:
    user = make_user()
    as_of = date(2026, 5, 9)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result([]))

    out = await get_timeseries(db, user_id=user.id, range_="week", as_of=as_of)

    assert len(out.points) == 7
    assert out.days == 7

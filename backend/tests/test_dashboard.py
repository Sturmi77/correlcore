from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.entry import WorkContext
from app.models.insight import InsightTier
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import get_dashboard_summary, insight_confidence_score
from app.services.insight_engine import confidence_tier_for_sample
from tests.conftest import make_user


def _scalar_one_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _all_result(value: object) -> MagicMock:
    result = MagicMock()
    result.all.return_value = value
    return result


@pytest.mark.parametrize(
    ("entry_count", "expected_tier"),
    [
        (0, InsightTier.NONE),
        (3, InsightTier.EARLY),
        (8, InsightTier.PRELIMINARY),
        (15, InsightTier.DEVELOPING),
        (30, InsightTier.ROBUST),
        (100, InsightTier.ROBUST),
    ],
)
def test_insight_confidence_score_boundaries_are_log_scaled(
    entry_count: int,
    expected_tier: InsightTier,
) -> None:
    score = insight_confidence_score(entry_count)

    assert 0.0 <= score <= 1.0
    assert confidence_tier_for_sample(entry_count) == expected_tier


def test_insight_confidence_score_keeps_improving_after_robust_threshold() -> None:
    assert insight_confidence_score(30) < insight_confidence_score(100)
    assert insight_confidence_score(100) == 1.0


@pytest.mark.asyncio
async def test_dashboard_summary_counts_distinct_entry_dates() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_result(15),
            _all_result([(WorkContext.OFFICE, 8, 3.75, 3.5, 2.25)]),
            _all_result(
                [
                    (0, 2, 3.5),
                    (1, 2, 3.6),
                    (2, 2, 3.4),
                    (3, 2, 3.7),
                    (4, 2, 3.8),
                    (5, 2, 3.3),
                    (6, 3, 3.2),
                ]
            ),
        ]
    )

    out = await get_dashboard_summary(db, user_id=user.id, as_of=date(2026, 5, 12))

    assert out.entry_count == 15
    assert out.insight_tier == InsightTier.DEVELOPING
    assert out.confidence_score == insight_confidence_score(15)
    assert out.work_context_summary[0].work_context == WorkContext.OFFICE
    assert out.work_context_summary[0].entry_count == 8
    assert out.work_context_summary[0].mood_avg == 3.75
    assert len(out.weekday_summary) == 7
    assert out.weekday_summary[4].weekday == 4
    assert out.weekday_summary[4].mood_avg == 3.8
    count_stmt = db.execute.await_args_list[0].args[0]
    assert "count(distinct(entries.entry_date))" in str(count_stmt)
    assert "entries.entry_date <= :entry_date_1" in str(count_stmt.whereclause)


@pytest.mark.asyncio
async def test_dashboard_summary_omits_weekday_summary_without_full_week_coverage() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_result(9),
            _all_result([]),
            _all_result([(0, 3, 3.5), (1, 3, 3.6), (2, 3, 3.4)]),
        ]
    )

    out = await get_dashboard_summary(db, user_id=user.id, as_of=date(2026, 5, 12))

    assert out.entry_count == 9
    assert out.weekday_summary == []


@pytest.mark.asyncio
async def test_dashboard_summary_endpoint_returns_confidence_fields(
    async_client: AsyncClient,
    user: User,
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.dashboard.get_dashboard_summary",
            new_callable=AsyncMock,
            return_value=DashboardSummaryResponse(
                entry_count=30,
                insight_tier=InsightTier.ROBUST,
                confidence_score=0.9,
                work_context_summary=[
                    {
                        "work_context": WorkContext.OFFICE,
                        "entry_count": 12,
                        "mood_avg": 3.8,
                        "energy_avg": 3.4,
                        "stress_avg": 2.6,
                    }
                ],
                weekday_summary=[
                    {"weekday": 0, "entry_count": 4, "mood_avg": 3.2},
                    {"weekday": 4, "entry_count": 5, "mood_avg": 3.9},
                ],
            ),
        ) as summary:
            response = await async_client.get(
                "/api/v1/dashboard/summary?as_of=2026-05-12",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    summary.assert_awaited_once()
    assert response.json() == {
        "entry_count": 30,
        "insight_tier": "robust",
        "confidence_score": 0.9,
        "work_context_summary": [
            {
                "work_context": "office",
                "entry_count": 12,
                "mood_avg": 3.8,
                "energy_avg": 3.4,
                "stress_avg": 2.6,
            }
        ],
        "weekday_summary": [
            {"weekday": 0, "entry_count": 4, "mood_avg": 3.2},
            {"weekday": 4, "entry_count": 5, "mood_avg": 3.9},
        ],
    }

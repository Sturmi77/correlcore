"""Tests for lag_profile backfill helpers and service (#488)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.insight import Insight, InsightTier, InsightType
from app.models.user import User
from app.services.insight_engine import InsightCandidate
from app.services.lag_profile_backfill_service import (
    LagInsightRow,
    LagProfileBackfillSummary,
    apply_lag_profile_backfill,
    backfill_lag_profiles,
    build_backfilled_payload,
    build_profile_lookup_from_candidates,
    pair_key_from_payload,
    payload_needs_lag_profile,
)
from tests.conftest import make_user


def _lag_payload(
    *,
    lag_days: int = 2,
    lag_profile: list[dict[str, float | int]] | None = None,
    feature_key: str = "tag:sport",
    target_key: str = "mood_score",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "method": "lag",
        "lag_days": lag_days,
        "feature": {"kind": "tag", "key": feature_key, "name": "Sport"},
        "target": {"kind": "metric", "key": target_key, "name": "Mood"},
    }
    if lag_profile is not None:
        payload["lag_profile"] = lag_profile
    return payload


def _make_lag_insight(user: User, *, payload: dict[str, object] | None = None) -> Insight:
    now = datetime.now(UTC)
    insight = Insight()
    insight.id = uuid.uuid4()
    insight.user_id = user.id
    insight.insight_type = InsightType.SYMPTOM_CLUSTER
    insight.tier = InsightTier.DEVELOPING
    insight.metric = "mood_score"
    insight.subject_type = "metric"
    insight.subject_label = "mood_score"
    insight.effect_size = 0.4
    insight.confidence = 0.55
    insight.sample_n = 95
    insight.statement_enc = "Lag insight"
    insight.flags = {"method": "lag"}
    insight.payload = payload or _lag_payload()
    insight.generated_for_date = date(2026, 7, 20)
    insight.generated_at = now
    insight.created_at = now
    insight.updated_at = now
    return insight


def test_payload_needs_lag_profile_detects_missing_or_short_series() -> None:
    assert payload_needs_lag_profile(_lag_payload()) is True
    assert payload_needs_lag_profile(_lag_payload(lag_profile=[])) is True
    assert payload_needs_lag_profile(_lag_payload(lag_profile=[{"lag": 2, "r": 0.4}])) is True
    assert (
        payload_needs_lag_profile(
            _lag_payload(
                lag_profile=[
                    {"lag": 1, "r": 0.2},
                    {"lag": 2, "r": 0.4},
                ]
            )
        )
        is False
    )
    assert payload_needs_lag_profile({"method": "lasso"}) is False


def test_pair_key_from_payload_normalizes_tag_keys() -> None:
    payload = _lag_payload(feature_key="tag:sport", target_key="mood_score")
    assert pair_key_from_payload(payload) == (
        ("metric", "mood_score"),
        ("tag", "sport"),
    )


def test_build_profile_lookup_from_candidates_uses_pair_key() -> None:
    profile = [{"lag": 1, "r": 0.2}, {"lag": 2, "r": 0.4}]
    candidate = InsightCandidate(
        insight_type=InsightType.SYMPTOM_CLUSTER,
        tier=InsightTier.DEVELOPING,
        metric="mood_score",
        subject_type="metric",
        subject_id=None,
        subject_label="mood_score",
        effect_size=0.4,
        confidence=0.5,
        sample_n=95,
        statement="Lag",
        flags={"method": "lag"},
        payload=_lag_payload(lag_profile=profile),
        generated_for_date=date(2026, 7, 31),
    )

    lookup = build_profile_lookup_from_candidates([candidate])

    assert lookup[pair_key_from_payload(candidate.payload)] == profile


def test_build_backfilled_payload_returns_updated_dict() -> None:
    profile = [{"lag": 1, "r": 0.3}, {"lag": 2, "r": 0.5}]
    payload = _lag_payload()
    lookup = {pair_key_from_payload(payload): profile}

    updated = build_backfilled_payload(payload, lookup)

    assert updated is not None
    assert updated["lag_profile"] == profile
    assert build_backfilled_payload(_lag_payload(lag_profile=profile), lookup) is None


def test_apply_lag_profile_backfill_updates_payload_and_skips_complete_rows() -> None:
    user = make_user()
    insight = _make_lag_insight(user)
    profile = [{"lag": 1, "r": 0.3}, {"lag": 2, "r": 0.5}]
    lookup = {pair_key_from_payload(insight.payload): profile}

    assert apply_lag_profile_backfill(insight, lookup) is True
    assert insight.payload["lag_profile"] == profile

    complete = _make_lag_insight(user, payload=_lag_payload(lag_profile=profile))
    assert apply_lag_profile_backfill(complete, lookup) is False


@pytest.mark.asyncio
async def test_backfill_lag_profiles_updates_matching_rows() -> None:
    user = make_user()
    insight = _make_lag_insight(user)
    db = MagicMock()
    db.execute = AsyncMock()

    profile = [{"lag": 1, "r": 0.25}, {"lag": 2, "r": 0.45}]
    candidate = InsightCandidate(
        insight_type=InsightType.SYMPTOM_CLUSTER,
        tier=InsightTier.DEVELOPING,
        metric="mood_score",
        subject_type="metric",
        subject_id=None,
        subject_label="mood_score",
        effect_size=0.45,
        confidence=0.5,
        sample_n=95,
        statement="Lag",
        flags={"method": "lag"},
        payload=_lag_payload(lag_profile=profile),
        generated_for_date=date(2026, 7, 31),
    )

    with (
        patch(
            "app.services.lag_profile_backfill_service.bind_rls_current_user",
            new=AsyncMock(),
        ),
        patch(
            "app.services.lag_profile_backfill_service._lag_insights_needing_backfill",
            new=AsyncMock(
                return_value=[
                    LagInsightRow(
                        id=insight.id,
                        user_id=user.id,
                        payload=dict(insight.payload),
                        generated_for_date=date(2026, 7, 20),
                    )
                ]
            ),
        ),
        patch(
            "app.services.lag_profile_backfill_service._analytics_enabled",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.lag_profile_backfill_service.load_analytics_data",
            new=AsyncMock(return_value=([MagicMock()], [], [])),
        ),
        patch(
            "app.services.lag_profile_backfill_service.generate_insight_candidates",
            return_value=[candidate],
        ) as generate,
        patch(
            "app.services.lag_profile_backfill_service.set_current_user_dek",
            return_value="dek-token",
        ),
        patch(
            "app.services.lag_profile_backfill_service.unwrap_dek",
            return_value=b"dek-bytes",
        ),
        patch("app.services.lag_profile_backfill_service.reset_current_user_dek"),
    ):
        key_result = MagicMock()
        key_result.scalar_one_or_none.return_value = b"wrapped-dek"
        db.execute = AsyncMock(return_value=key_result)
        summary = await backfill_lag_profiles(db, user_id=user.id)

    generate.assert_called_once()
    assert generate.call_args.kwargs["as_of"] == date(2026, 7, 20)
    assert db.execute.await_count >= 1
    assert summary == LagProfileBackfillSummary(
        users_processed=1,
        insights_scanned=1,
        insights_updated=1,
        insights_skipped=0,
        insights_unmatched=0,
        user_ids=[user.id],
    )
    assert summary.insights_updated == 1
    assert "lag_profile" not in insight.payload


@pytest.mark.asyncio
async def test_backfill_lag_profiles_skips_analytics_disabled_users() -> None:
    user = make_user()
    insight = _make_lag_insight(user)
    db = MagicMock()
    db.execute = AsyncMock()

    with (
        patch(
            "app.services.lag_profile_backfill_service.bind_rls_current_user",
            new=AsyncMock(),
        ),
        patch(
            "app.services.lag_profile_backfill_service._lag_insights_needing_backfill",
            new=AsyncMock(
                return_value=[
                    LagInsightRow(
                        id=insight.id,
                        user_id=user.id,
                        payload=dict(insight.payload),
                        generated_for_date=date(2026, 7, 20),
                    )
                ]
            ),
        ),
        patch(
            "app.services.lag_profile_backfill_service._analytics_enabled",
            new=AsyncMock(return_value=False),
        ),
    ):
        summary = await backfill_lag_profiles(db, user_id=user.id)

    assert summary.insights_scanned == 1
    assert summary.insights_skipped == 1
    assert summary.insights_updated == 0
    db.execute.assert_not_awaited()

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.models import Insight, InsightTier, InsightType, UserPreference
from app.schemas.insight import InsightResponse
from app.schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate


def test_insight_schema_exposes_decrypted_statement_alias() -> None:
    now = datetime.now(UTC)
    insight = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        insight_type=InsightType.POINTBISERIAL,
        tier=InsightTier.EARLY,
        metric="mood_score",
        subject_type="tag",
        subject_id=uuid.uuid4(),
        subject_label="Sport",
        effect_size=0.42,
        confidence=0.7,
        sample_n=14,
        statement_enc="Sport days have slightly higher mood scores.",
        flags={"minimum_sample_met": False},
        payload={"window_days": 14},
        generated_for_date=date(2026, 5, 11),
        generated_at=now,
        created_at=now,
        updated_at=now,
    )

    response = InsightResponse.model_validate(insight)

    assert response.insight_type == InsightType.POINTBISERIAL
    assert response.tier == InsightTier.EARLY
    assert response.statement == "Sport days have slightly higher mood scores."
    assert response.flags["minimum_sample_met"] is False


def test_user_preferences_schema_defaults_keep_future_endpoints_sparse() -> None:
    now = datetime.now(UTC)
    preferences = SimpleNamespace(
        user_id=uuid.uuid4(),
        analytics_enabled=True,
        onboarding_retro_completed=False,
        onboarding_profile_completed=False,
        onboarding_maturity_intro_seen=False,
        dismissed_insight_keys=[],
        reached_milestone_keys=["first_week_numbers"],
        last_seen_insight_at=None,
        created_at=now,
        updated_at=now,
    )

    response = UserPreferencesResponse.model_validate(preferences)
    update = UserPreferencesUpdate(analytics_enabled=False)

    assert response.analytics_enabled is True
    assert response.reached_milestone_keys == ["first_week_numbers"]
    assert update.model_dump(exclude_none=True) == {"analytics_enabled": False}


def test_m3_models_are_registered_for_alembic_autodetect() -> None:
    assert Insight.__tablename__ == "insights"
    assert UserPreference.__tablename__ == "user_preferences"

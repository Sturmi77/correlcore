"""Contract projections from persisted JSON, including historical incomplete rows."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from app.models.insight import InsightTier, InsightType
from app.schemas.insight import InsightResponse
from app.schemas.insight_evidence import (
    AssociationEvidence,
    BelastungEvidence,
    ChangepointEvidence,
    LagEvidence,
    build_insight_evidence,
)


def test_association_evidence_preserves_unequal_groups_and_missing_histogram() -> None:
    evidence = build_insight_evidence(
        "pointbiserial",
        "mood_score",
        {
            "tagged_count": 5,
            "untagged_count": 95,
            "tagged_mood_avg": 0,
            "untagged_mood_avg": 3,
            "weekday_held_coefficient": -0.2,
            "with_distribution": [1, 1, 1, 1, 1],
        },
        -0.3,
    )
    assert isinstance(evidence, AssociationEvidence)
    assert (evidence.with_n, evidence.without_n) == (5, 95)
    assert evidence.with_mean_raw == 0
    assert evidence.with_distribution == [1, 1, 1, 1, 1]
    assert evidence.without_distribution is None
    assert evidence.weekday_held_coefficient == -0.2
    assert build_insight_evidence("pointbiserial", "mood_score", {"tagged_count": 5}, None) is None

    null_evidence = build_insight_evidence(
        "null_association", "stress",
        {"tagged_count": 5, "untagged_count": 95, "outcome": "null",
         "calendar_held_coefficient": 0.1},
        0.2,
    )
    assert isinstance(null_evidence, AssociationEvidence)
    assert null_evidence.outcome == "null"
    assert null_evidence.calendar_held_coefficient == 0.1
    assert null_evidence.with_mean_raw is None


def test_changepoint_evidence_separates_raw_and_display_directions() -> None:
    for before, after, raw, display in (
        (2, 5, "higher", "lower"),
        (5, 2, "lower", "higher"),
        (3, 3, "unchanged", "unchanged"),
    ):
        evidence = build_insight_evidence(
            "changepoint",
            "stress_changepoint",
            {
                "series": "stress",
                "before_avg": before,
                "after_avg": after,
                "changepoint_date": "2026-03-10",
                "shift_date": "2026-03-11",
            },
            None,
        )
        assert isinstance(evidence, ChangepointEvidence)
        assert (evidence.before_raw, evidence.after_raw) == (before, after)
        assert (evidence.before_display, evidence.after_display) == (6 - before, 6 - after)
        assert (evidence.raw_direction, evidence.display_direction) == (raw, display)
        assert evidence.boundary_after == date(2026, 3, 11)
    assert (
        build_insight_evidence("changepoint", "stress_changepoint", {"before_avg": 2}, None) is None
    )


def test_lag_identity_keeps_target_feature_and_evidence_window() -> None:
    evidence = build_insight_evidence(
        "symptom_cluster",
        "mood_score",
        {
            "method": "lag",
            "target": {"key": "mood_score"},
            "feature": {"key": "tag:sport"},
            "lag_days": 2,
            "p_value_corrected": 0.03,
            "evidence_start": "2026-01-01",
            "evidence_end": "2026-01-28",
        },
        0.4,
    )
    assert isinstance(evidence, LagEvidence)
    assert (evidence.target_key, evidence.feature_key, evidence.lag_days) == (
        "mood_score",
        "tag:sport",
        2,
    )
    assert evidence.evidence_end == date(2026, 1, 28)


def test_belastung_evidence_does_not_claim_joint_frequency() -> None:
    evidence = build_insight_evidence(
        "belastung_pattern",
        "belastung_composite",
        {
            "recent_n": 14,
            "prior_n": 14,
            "stress_avg_recent": 4,
            "stress_avg_prior": 2,
            "energy_avg_recent": 3,
            "energy_avg_prior": 3,
            "fatigue_days_recent": 4,
            "fatigue_days_prior": 4,
        },
        None,
    )
    assert isinstance(evidence, BelastungEvidence)
    assert evidence.stress_up is True
    assert evidence.energy_down is False
    assert evidence.fatigue_up is False
    assert evidence.joint_frequency_recent is None


def test_api_response_projects_evidence_without_requiring_it_in_old_json() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    fields = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "insight_type": InsightType.POINTBISERIAL,
        "tier": InsightTier.ROBUST,
        "metric": "mood_score",
        "sample_n": 100,
        "statement_enc": "Observed association",
        "generated_for_date": now.date(),
        "generated_at": now,
        "created_at": now,
        "updated_at": now,
    }
    current = InsightResponse.model_validate(
        {**fields, "payload": {"tagged_count": 5, "untagged_count": 95}}
    )
    historical = InsightResponse.model_validate({**fields, "payload": {"tagged_count": 5}})
    assert current.evidence is not None
    assert current.model_dump(mode="json")["evidence"]["family"] == "association"
    assert historical.evidence is None


def test_shared_api_render_fixture_is_projected_from_persisted_payload() -> None:
    fixture_path = (
        Path(__file__).parents[2]
        / "apps/web/src/lib/components/insights"
        / "insightContract.fixture.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    stored = {**fixture, "statement_enc": fixture["statement"]}
    stored.pop("evidence")
    stored.pop("statement")
    response = InsightResponse.model_validate(stored).model_dump(mode="json")
    assert response["evidence"] == fixture["evidence"]

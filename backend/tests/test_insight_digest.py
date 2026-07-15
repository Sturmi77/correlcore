from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.insight import Insight, InsightTier, InsightType
from app.services.insight_digest import (
    DIGEST_TOP_N,
    build_push_payload,
    build_weekly_digest,
    insight_has_sufficient_confidence,
    push_payload_is_scrubbed,
    rank_digest_insights,
)


def _make_insight(
    *,
    effect_size: float,
    confidence: float,
    tier: InsightTier = InsightTier.DEVELOPING,
    statement: str = "Mood currently lines up with energy in your entries.",
) -> Insight:
    insight = Insight()
    insight.id = uuid.uuid4()
    insight.insight_type = InsightType.SPEARMAN
    insight.tier = tier
    insight.metric = "mood_score"
    insight.effect_size = effect_size
    insight.confidence = confidence
    insight.statement_enc = statement
    insight.generated_at = datetime.now(UTC)
    return insight


def test_rank_digest_insights_orders_by_absolute_effect_size() -> None:
    insights = [
        _make_insight(effect_size=0.2, confidence=0.7),
        _make_insight(effect_size=-0.9, confidence=0.8),
        _make_insight(effect_size=0.5, confidence=0.75),
        _make_insight(effect_size=0.1, confidence=0.6, tier=InsightTier.EARLY),
    ]

    ranked = rank_digest_insights(insights)

    assert len(ranked) == DIGEST_TOP_N
    assert [abs(item.effect_size or 0) for item in ranked] == [0.9, 0.5, 0.2]


def test_build_weekly_digest_requires_three_confident_insights() -> None:
    insights = [
        _make_insight(effect_size=0.4, confidence=0.7),
        _make_insight(effect_size=0.3, confidence=0.65),
    ]

    assert (
        build_weekly_digest(
            insights, week_start=datetime.now(UTC).date(), week_end=datetime.now(UTC).date()
        )
        is None
    )


def test_push_payload_scrubs_health_specific_statement_text() -> None:
    digest = build_weekly_digest(
        [
            _make_insight(
                effect_size=0.8, confidence=0.9, statement="Mood dips after headache days."
            ),
            _make_insight(effect_size=0.6, confidence=0.8, statement="Stress tracks with fatigue."),
            _make_insight(effect_size=0.4, confidence=0.7, statement="Energy rises on sport days."),
        ],
        week_start=datetime.now(UTC).date(),
        week_end=datetime.now(UTC).date(),
    )
    assert digest is not None

    payload = build_push_payload(digest)
    statements = [item.statement or "" for item in digest.insights]

    assert push_payload_is_scrubbed(payload, statements=statements)
    assert "mood" not in payload["body"].casefold()
    assert "headache" not in payload["body"].casefold()


def test_insight_has_sufficient_confidence_rejects_early_tier() -> None:
    insight = _make_insight(effect_size=0.5, confidence=0.8, tier=InsightTier.EARLY)
    assert insight_has_sufficient_confidence(insight) is False

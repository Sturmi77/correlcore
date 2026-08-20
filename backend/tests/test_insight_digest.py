from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.insight import Insight, InsightTier, InsightType
from app.models.insight_digest import InsightDigest
from app.services.insight_digest import (
    DIGEST_TOP_N,
    DigestDisabledError,
    DigestNotAvailableError,
    build_push_payload,
    build_weekly_digest,
    get_latest_weekly_digest,
    hydrate_stored_digest,
    insight_has_sufficient_confidence,
    push_payload_is_scrubbed,
    rank_digest_insights,
    store_weekly_digest,
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


def test_build_weekly_digest_has_no_generated_at() -> None:
    # #739: freshly built (recompute) digests carry no generation timestamp, so
    # the on-demand fallback never triggers the one-time modal.
    insights = [
        _make_insight(effect_size=0.4, confidence=0.8),
        _make_insight(effect_size=0.35, confidence=0.75),
        _make_insight(effect_size=0.3, confidence=0.7),
    ]
    digest = build_weekly_digest(
        insights, week_start=datetime.now(UTC).date(), week_end=datetime.now(UTC).date()
    )
    assert digest is not None
    assert digest.generated_at is None


@pytest.mark.asyncio
async def test_compute_weekly_digest_excludes_dismissed_insight_ids() -> None:
    from app.services.insight_digest import compute_weekly_digest_for_user

    user_id = uuid.uuid4()
    week = datetime.now(UTC).date()
    insights = _three_insights()
    for insight in insights:
        insight.user_id = user_id
    dismissed_id = insights[0].id

    with (
        patch(
            "app.services.insight_digest._digest_enabled",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.insight_digest.load_recent_insights",
            new=AsyncMock(return_value=insights),
        ),
        patch(
            "app.services.insight_dismissal_service.migrate_uuid_prefs_to_subject_dismissals",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.services.insight_dismissal_service.list_dismissed_subject_keys",
            new=AsyncMock(return_value=set()),
        ),
        patch(
            "app.services.insight_dismissal_service.dismissed_uuid_keys_remaining",
            new=AsyncMock(return_value={str(dismissed_id)}),
        ),
        patch(
            "app.services.insight_service._tag_slugs_for_legacy_insights",
            new=AsyncMock(return_value={}),
        ),
    ):
        with pytest.raises(DigestNotAvailableError):
            await compute_weekly_digest_for_user(
                MagicMock(), user_id=user_id, as_of=datetime.now(UTC)
            )

    # With a fourth qualifying insight, dismissed top effect still excluded from ranking.
    extra = _make_insight(effect_size=0.35, confidence=0.7)
    extra.user_id = user_id
    with (
        patch(
            "app.services.insight_digest._digest_enabled",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.insight_digest.load_recent_insights",
            new=AsyncMock(return_value=[*insights, extra]),
        ),
        patch(
            "app.services.insight_dismissal_service.migrate_uuid_prefs_to_subject_dismissals",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.services.insight_dismissal_service.list_dismissed_subject_keys",
            new=AsyncMock(return_value=set()),
        ),
        patch(
            "app.services.insight_dismissal_service.dismissed_uuid_keys_remaining",
            new=AsyncMock(return_value={str(dismissed_id)}),
        ),
        patch(
            "app.services.insight_service._tag_slugs_for_legacy_insights",
            new=AsyncMock(return_value={}),
        ),
    ):
        digest = await compute_weekly_digest_for_user(
            MagicMock(),
            user_id=user_id,
            as_of=datetime.combine(week, datetime.min.time(), tzinfo=UTC),
        )

    assert digest.insight_count == DIGEST_TOP_N
    assert dismissed_id not in {item.id for item in digest.insights}


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


def _three_insights() -> list[Insight]:
    return [
        _make_insight(effect_size=0.8, confidence=0.9),
        _make_insight(effect_size=0.6, confidence=0.8),
        _make_insight(effect_size=0.4, confidence=0.7),
    ]


@pytest.mark.asyncio
async def test_hydrate_stored_digest_preserves_insight_order() -> None:
    user_id = uuid.uuid4()
    insights = _three_insights()
    for insight in insights:
        insight.user_id = user_id

    row = InsightDigest()
    row.user_id = user_id
    row.week_start = datetime.now(UTC).date()
    row.week_end = datetime.now(UTC).date()
    row.insight_ids = [str(insights[2].id), str(insights[0].id), str(insights[1].id)]
    row.insight_count = 3
    row.push_title = "t"
    row.push_body = "b"
    row.generated_at = datetime(2026, 8, 16, 3, tzinfo=UTC)

    result = MagicMock()
    # Return out of order — hydrate must follow insight_ids.
    result.scalars.return_value.all.return_value = [insights[0], insights[1], insights[2]]
    prefs = MagicMock()
    prefs.scalar_one_or_none.return_value = []
    empty_keys = MagicMock()
    empty_keys.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[result, prefs, empty_keys, prefs])

    digest = await hydrate_stored_digest(db, row=row)
    assert digest is not None
    assert [item.id for item in digest.insights] == [
        insights[2].id,
        insights[0].id,
        insights[1].id,
    ]
    # #739: the persisted generation timestamp is carried onto the envelope so
    # the client can drive the one-time modal.
    assert digest.generated_at == datetime(2026, 8, 16, 3, tzinfo=UTC)


@pytest.mark.asyncio
async def test_get_latest_prefers_stored_digest() -> None:
    user_id = uuid.uuid4()
    insights = _three_insights()
    for insight in insights:
        insight.user_id = user_id
    week = datetime.now(UTC).date()
    stored = build_weekly_digest(insights, week_start=week, week_end=week)
    assert stored is not None

    db = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    with (
        patch(
            "app.services.insight_digest._digest_enabled",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.insight_digest.load_latest_stored_digest",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.services.insight_digest.hydrate_stored_digest",
            new=AsyncMock(return_value=stored),
        ) as hydrate,
        patch(
            "app.services.insight_digest.compute_weekly_digest_for_user",
            new=AsyncMock(),
        ) as compute,
    ):
        out = await get_latest_weekly_digest(db, user_id=user_id)
        assert out is stored
        hydrate.assert_awaited_once()
        compute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_latest_falls_back_to_recompute_when_store_missing() -> None:
    user_id = uuid.uuid4()
    insights = _three_insights()
    week = datetime.now(UTC).date()
    recomputed = build_weekly_digest(insights, week_start=week, week_end=week)
    assert recomputed is not None

    db = MagicMock()
    with (
        patch(
            "app.services.insight_digest._digest_enabled",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.insight_digest.load_latest_stored_digest",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.insight_digest.compute_weekly_digest_for_user",
            new=AsyncMock(return_value=recomputed),
        ) as compute,
    ):
        out = await get_latest_weekly_digest(db, user_id=user_id)
        assert out is recomputed
        compute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_latest_disabled_raises() -> None:
    db = MagicMock()
    with patch(
        "app.services.insight_digest._digest_enabled",
        new=AsyncMock(return_value=False),
    ):
        with pytest.raises(DigestDisabledError):
            await get_latest_weekly_digest(db, user_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_store_then_get_roundtrip_via_hydrate() -> None:
    """Worker store → GET prefers hydrated snapshot (integration-style unit)."""

    user_id = uuid.uuid4()
    insights = _three_insights()
    for insight in insights:
        insight.user_id = user_id
    week = datetime.now(UTC).date()
    digest = build_weekly_digest(insights, week_start=week, week_end=week)
    assert digest is not None

    db = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    row = await store_weekly_digest(db, user_id=user_id, digest=digest)
    # store_weekly_digest builds a new InsightDigest; simulate persisted fields.
    row.user_id = user_id
    row.week_start = digest.week_start
    row.week_end = digest.week_end
    row.insight_ids = [str(item.id) for item in digest.insights]
    row.insight_count = digest.insight_count

    result = MagicMock()
    result.scalars.return_value.all.return_value = insights
    prefs = MagicMock()
    prefs.scalar_one_or_none.return_value = []
    empty_keys = MagicMock()
    empty_keys.all.return_value = []
    db.execute = AsyncMock(side_effect=[result, prefs, empty_keys, prefs])

    hydrated = await hydrate_stored_digest(db, row=row)
    assert hydrated is not None
    assert hydrated.insight_count == DIGEST_TOP_N
    assert [item.id for item in hydrated.insights] == [item.id for item in digest.insights]


@pytest.mark.asyncio
async def test_compute_raises_when_not_enough_insights() -> None:
    from app.services.insight_digest import compute_weekly_digest_for_user

    db = MagicMock()
    with (
        patch(
            "app.services.insight_digest._digest_enabled",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.insight_digest.load_recent_insights",
            new=AsyncMock(return_value=_three_insights()[:2]),
        ),
        patch(
            "app.services.insight_dismissal_service.migrate_uuid_prefs_to_subject_dismissals",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.services.insight_dismissal_service.list_dismissed_subject_keys",
            new=AsyncMock(return_value=set()),
        ),
        patch(
            "app.services.insight_dismissal_service.dismissed_uuid_keys_remaining",
            new=AsyncMock(return_value=set()),
        ),
    ):
        with pytest.raises(DigestNotAvailableError):
            await compute_weekly_digest_for_user(db, user_id=uuid.uuid4())

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.insight import Insight, InsightTier, InsightType
from app.models.insight_dismissal import InsightDismissal
from app.services.insight_dismissal_service import (
    create_insight_dismissal,
    delete_insight_dismissal_by_insight_id,
)
from app.services.insight_service import insight_subject_key
from tests.conftest import make_user


def _scalar_optional_result(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_insight(user, *, subject_label: str = "energy") -> Insight:
    now = datetime.now(UTC)
    insight = Insight()
    insight.id = uuid.uuid4()
    insight.user_id = user.id
    insight.insight_type = InsightType.SPEARMAN
    insight.tier = InsightTier.DEVELOPING
    insight.metric = "mood_score"
    insight.subject_type = "metric"
    insight.subject_id = None
    insight.subject_label = subject_label
    insight.effect_size = 0.4
    insight.confidence = 0.7
    insight.sample_n = 20
    insight.statement_enc = "Mood lines up with energy."
    insight.flags = {}
    insight.payload = {}
    insight.generated_for_date = now.date()
    insight.generated_at = now
    insight.created_at = now
    insight.updated_at = now
    return insight


@pytest.mark.asyncio
async def test_create_insight_dismissal_is_subject_stable_and_idempotent() -> None:
    user = make_user()
    insight = _make_insight(user)
    subject_key = insight_subject_key(insight, tag_slugs_by_id={})

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    prefs = MagicMock()
    prefs.dismissed_insight_keys = [str(insight.id)]
    db.execute = AsyncMock(
        side_effect=[
            _scalar_optional_result(insight),  # get_insight_by_id
            _scalar_optional_result(None),  # existing dismissal
            _scalar_optional_result(prefs),
        ]
    )

    row = await create_insight_dismissal(db, user_id=user.id, insight_id=insight.id)

    assert row.subject_key == subject_key
    assert row.insight_id == insight.id
    db.add.assert_called_once()

    existing = InsightDismissal(
        user_id=user.id,
        subject_key=subject_key,
        insight_id=insight.id,
    )
    existing.id = uuid.uuid4()
    prefs2 = MagicMock()
    prefs2.dismissed_insight_keys = []
    db.execute = AsyncMock(
        side_effect=[
            _scalar_optional_result(insight),
            _scalar_optional_result(existing),
            _scalar_optional_result(prefs2),
        ]
    )
    db.add.reset_mock()

    again = await create_insight_dismissal(db, user_id=user.id, insight_id=insight.id)

    assert again is existing
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_delete_dismissal_by_insight_removes_subject_row() -> None:
    user = make_user()
    insight = _make_insight(user, subject_label="stress")
    subject_key = insight_subject_key(insight, tag_slugs_by_id={})
    row = InsightDismissal(user_id=user.id, subject_key=subject_key, insight_id=insight.id)
    row.id = uuid.uuid4()

    db = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    prefs = MagicMock()
    prefs.dismissed_insight_keys = [str(insight.id)]
    db.execute = AsyncMock(
        side_effect=[
            _scalar_optional_result(row),  # by insight_id
            _scalar_optional_result(prefs),  # remove_dismissed get prefs
        ]
    )

    await delete_insight_dismissal_by_insight_id(db, user_id=user.id, insight_id=insight.id)

    db.delete.assert_awaited_once_with(row)


@pytest.mark.asyncio
async def test_subject_key_stable_across_new_insight_uuid() -> None:
    user = make_user()
    first = _make_insight(user, subject_label="stress")
    second = _make_insight(user, subject_label="stress")
    second.id = uuid.uuid4()

    assert insight_subject_key(first, tag_slugs_by_id={}) == insight_subject_key(
        second, tag_slugs_by_id={}
    )


@pytest.mark.asyncio
async def test_compute_digest_excludes_subject_dismissals() -> None:
    from app.services.insight_digest import DIGEST_TOP_N, compute_weekly_digest_for_user

    user_id = uuid.uuid4()
    week = datetime.now(UTC).date()

    def _make(
        *,
        effect: float,
        confidence: float,
        label: str,
    ) -> Insight:
        insight = Insight()
        insight.id = uuid.uuid4()
        insight.user_id = user_id
        insight.insight_type = InsightType.SPEARMAN
        insight.tier = InsightTier.DEVELOPING
        insight.metric = "mood_score"
        insight.subject_type = "metric"
        insight.subject_id = None
        insight.subject_label = label
        insight.effect_size = effect
        insight.confidence = confidence
        insight.sample_n = 20
        insight.statement_enc = label
        insight.flags = {}
        insight.payload = {}
        insight.generated_at = datetime.now(UTC)
        return insight

    insights = [
        _make(effect=0.9, confidence=0.9, label="a"),
        _make(effect=0.6, confidence=0.8, label="b"),
        _make(effect=0.5, confidence=0.7, label="c"),
        _make(effect=0.4, confidence=0.7, label="d"),
    ]
    hidden_key = insight_subject_key(insights[0], tag_slugs_by_id={})

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
            new=AsyncMock(return_value={hidden_key}),
        ),
        patch(
            "app.services.insight_dismissal_service.dismissed_uuid_keys_remaining",
            new=AsyncMock(return_value=set()),
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
    assert insights[0].id not in {item.id for item in digest.insights}

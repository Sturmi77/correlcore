from __future__ import annotations

import importlib.util
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.insight import Insight, InsightTier, InsightType
from app.models.insight_dismissal import InsightDismissal
from app.services.insight_dismissal_service import (
    canonical_dismissal_subject_key,
    create_insight_dismissal,
    delete_insight_dismissal,
    delete_insight_dismissal_by_insight_id,
    list_dismissed_subject_keys,
    rewrite_lag_dismissal_subject_key,
)
from app.services.insight_service import insight_subject_key
from tests.conftest import make_user


def _scalar_optional_result(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_result(values: list[object]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
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
            _scalars_result([]),  # existing dismissals
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
            _scalars_result([existing]),
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
            _scalars_result([row]),  # all equivalent subject keys
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


def _make_lag_insight_for_key(user) -> Insight:
    insight = Insight()
    insight.id = uuid.uuid4()
    insight.user_id = user.id
    insight.insight_type = InsightType.SYMPTOM_CLUSTER
    insight.tier = InsightTier.DEVELOPING
    insight.metric = "mood_score"
    insight.subject_type = "metric"
    insight.subject_id = None
    insight.subject_label = "mood_score"
    insight.payload = {
        "method": "lag",
        "target": {"kind": "metric", "key": "mood_score"},
        "feature": {"kind": "tag", "key": "tag:sport", "id": str(uuid.uuid4())},
        "lag_days": 2,
    }
    return insight


def test_rewrite_lag_dismissal_subject_key_collapses_to_pair() -> None:
    """#853 Q2: a legacy per-lag dismissal key is rewritten onto its pair key."""
    user = make_user()
    insight = _make_lag_insight_for_key(user)
    pair_key = insight_subject_key(insight)  # already pair-scoped after #853

    # Reconstruct a legacy key whose subject list still carried a trailing lag.
    payload = json.loads(pair_key)
    payload["subject"] = [*payload["subject"], 2]
    legacy_key = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True)

    assert legacy_key != pair_key
    assert rewrite_lag_dismissal_subject_key(legacy_key) == pair_key


def test_rewrite_lag_dismissal_subject_key_ignores_non_lag_and_collapsed() -> None:
    user = make_user()
    insight = _make_lag_insight_for_key(user)
    pair_key = insight_subject_key(insight)

    # Already collapsed (4-element subject) → nothing to do.
    assert rewrite_lag_dismissal_subject_key(pair_key) is None
    # A non-lag subject key is left untouched.
    non_lag = json.dumps(
        {
            "insight_type": "spearman",
            "metric": "mood_score",
            "subject_type": "metric",
            "subject": ["subject", None, "energy"],
        },
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
    )
    assert rewrite_lag_dismissal_subject_key(non_lag) is None
    # Malformed input is tolerated.
    assert rewrite_lag_dismissal_subject_key("not json") is None


def _key(**changes: object) -> str:
    payload: dict[str, object] = {
        "insight_type": "changepoint",
        "metric": "stress_changepoint",
        "subject_type": "changepoint",
        "subject": ["subject", None, "entry_42"],
    }
    payload.update(changes)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def test_canonical_dismissal_key_preserves_series_and_metric_boundaries() -> None:
    old = _key()
    current = _key(subject=["changepoint", "stress"])
    assert canonical_dismissal_subject_key(old) == current
    assert canonical_dismissal_subject_key(current) == current
    assert canonical_dismissal_subject_key(_key(metric="mood_changepoint")) != current
    assert canonical_dismissal_subject_key(_key(metric="unknown_changepoint")) != current


def test_canonical_dismissal_key_handles_association_and_lag_history() -> None:
    old_association = _key(
        insight_type="null_association",
        metric="mood_avg",
        subject_type="tag",
        subject=["tag_slug", "sport"],
    )
    current_association = _key(
        insight_type="pointbiserial",
        metric="mood_score",
        subject_type="tag",
        subject=["tag_slug", "sport"],
    )
    assert canonical_dismissal_subject_key(old_association) == current_association
    assert (
        canonical_dismissal_subject_key(
            _key(
                insight_type="null_association",
                metric="stress",
                subject_type="tag",
                subject=["tag_slug", "sport"],
            )
        )
        != current_association
    )
    old_lag = _key(
        insight_type="symptom_cluster",
        metric="mood_score",
        subject_type="metric",
        subject=["symptom_cluster", "lag", [["key", "mood_score"]], "tag:sport", 2],
    )
    assert json.loads(canonical_dismissal_subject_key(old_lag))["subject"] == [
        "symptom_cluster",
        "lag",
        [["key", "mood_score"]],
        "tag:sport",
    ]


@pytest.mark.asyncio
async def test_old_dismissal_key_is_read_as_current_identity_for_one_user() -> None:
    user_id = uuid.uuid4()
    db = MagicMock()
    result = MagicMock()
    result.all.return_value = [(_key(),)]
    db.execute = AsyncMock(return_value=result)
    assert await list_dismissed_subject_keys(db, user_id=user_id) == {
        _key(subject=["changepoint", "stress"])
    }


@pytest.mark.asyncio
async def test_targeted_unhide_removes_legacy_collision_only() -> None:
    user_id = uuid.uuid4()
    old = InsightDismissal(user_id=user_id, subject_key=_key())
    old.id = uuid.uuid4()
    current = InsightDismissal(user_id=user_id, subject_key=_key(subject=["changepoint", "stress"]))
    current.id = uuid.uuid4()
    other = InsightDismissal(user_id=user_id, subject_key=_key(metric="mood_changepoint"))
    other.id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[_scalar_optional_result(old), _scalars_result([old, current, other])]
    )
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    await delete_insight_dismissal(db, user_id=user_id, dismissal_id=old.id)
    assert {call.args[0].id for call in db.delete.await_args_list} == {old.id, current.id}


@pytest.mark.asyncio
async def test_create_reuses_legacy_changepoint_dismissal() -> None:
    user = make_user()
    insight = _make_insight(user)
    insight.insight_type = InsightType.CHANGEPOINT
    insight.metric = "stress_changepoint"
    insight.subject_type = "changepoint"
    insight.subject_label = "2026-03-07"
    insight.payload = {"series": "stress"}
    old = InsightDismissal(user_id=user.id, subject_key=_key(), insight_id=uuid.uuid4())
    old.id = uuid.uuid4()
    prefs = MagicMock()
    prefs.dismissed_insight_keys = []
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_optional_result(insight),
            _scalars_result([old]),
            _scalar_optional_result(prefs),
        ]
    )
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    result = await create_insight_dismissal(db, user_id=user.id, insight_id=insight.id)
    assert result is old
    assert old.subject_key == insight_subject_key(insight)
    assert old.insight_id == insight.id
    db.add.assert_not_called()


def test_055_migration_resolves_collisions_per_user_and_is_idempotent(monkeypatch) -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations/versions/055_canonical_insight_dismissals.py"
    )
    spec = importlib.util.spec_from_file_location("migration_055", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    first_user, second_user = uuid.uuid4(), uuid.uuid4()
    old_key, current_key = _key(), _key(subject=["changepoint", "stress"])
    rows = [
        {
            "id": uuid.uuid4(),
            "user_id": first_user,
            "subject_key": old_key,
            "dismissed_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
        {
            "id": uuid.uuid4(),
            "user_id": first_user,
            "subject_key": current_key,
            "dismissed_at": datetime(2026, 1, 2, tzinfo=UTC),
        },
        {
            "id": uuid.uuid4(),
            "user_id": second_user,
            "subject_key": old_key,
            "dismissed_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
    ]

    class FakeConnection:
        def execute(self, statement, params=None):
            sql = str(statement)
            if sql.startswith("SELECT"):
                result = MagicMock()
                result.mappings.return_value = [dict(row) for row in rows]
                return result
            if sql.startswith("DELETE"):
                rows[:] = [row for row in rows if row["id"] not in params["ids"]]
            if sql.startswith("UPDATE"):
                next(row for row in rows if row["id"] == params["id"])["subject_key"] = params[
                    "key"
                ]
            return MagicMock()

    monkeypatch.setattr(migration.op, "get_bind", lambda: FakeConnection())
    migration.upgrade()
    assert len(rows) == 2
    assert all(row["subject_key"] == current_key for row in rows)
    assert {row["user_id"] for row in rows} == {first_user, second_user}
    snapshot = [dict(row) for row in rows]
    migration.upgrade()
    assert rows == snapshot

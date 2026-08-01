"""Tests for M2 data export."""

from __future__ import annotations

import json
import uuid
import zipfile
from datetime import UTC, date, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.insight import Insight, InsightTier, InsightType
from app.models.insight_dismissal import InsightDismissal
from app.services.export_service import build_export_envelope, render_export_csv, render_export_zip
from app.services.insight_service import insight_subject_key
from tests.conftest import (
    make_entry,
    make_entry_symptom,
    make_entry_tag,
    make_symptom,
    make_tag,
    make_user,
)


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


def _scalar_optional_result(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _prefs_keys_result(keys: list[str] | None = None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = keys or []
    return result


def _make_insight(user, *, subject_label: str = "energy") -> Insight:
    now = datetime(2026, 5, 14, tzinfo=UTC)
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
    insight.statement_enc = f"Statement for {subject_label}"
    insight.flags = {}
    insight.payload = {"note": "ok"}
    insight.generated_for_date = date(2026, 5, 14)
    insight.generated_at = now
    insight.created_at = now
    insight.updated_at = now
    return insight


def _make_dismissal(
    user, *, subject_key: str, insight_id: uuid.UUID | None = None
) -> InsightDismissal:
    now = datetime(2026, 5, 15, tzinfo=UTC)
    row = InsightDismissal()
    row.id = uuid.uuid4()
    row.user_id = user.id
    row.subject_key = subject_key
    row.insight_id = insight_id
    row.dismissed_at = now
    row.created_at = now
    return row


@pytest.mark.asyncio
async def test_export_omits_internal_ids_and_includes_assigned_data() -> None:
    user = make_user(email="me@example.test")
    entry = make_entry(user, mood_score=5, cycle_day=12, note="private note")
    tag = make_tag(user, slug="focus", name="Focus")
    symptom = make_symptom(user, slug="migraine", name="Migraine")
    entry_tag = make_entry_tag(entry=entry, tag=tag)
    entry_symptom = make_entry_symptom(entry=entry, symptom=symptom, intensity=2)

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result([entry]),
            _scalar_optional_result(None),
            _row_result([(entry_tag.entry_id, tag)]),
            _row_result([(entry_symptom.entry_id, entry_symptom.intensity, symptom)]),
            _scalar_result([]),
            _prefs_keys_result([]),
            _scalar_result([]),
        ]
    )

    envelope = await build_export_envelope(db, user=user)
    payload = envelope.model_dump(mode="json")

    assert payload["user"]["email"] == "me@example.test"
    assert payload["app_version"] == "1.1.7"
    assert payload["format_version"] == "1.3"
    assert payload["score_legend"]["stress"] == {
        "min": 1,
        "max": 5,
        "min_label": "relaxed",
        "max_label": "very stressed",
    }
    assert payload["entries"][0]["note"] == "private note"
    assert payload["entries"][0]["cycle_day"] == 12
    assert payload["entries"][0]["tags"][0]["name"] == "Focus"
    assert payload["entries"][0]["symptoms"][0]["intensity"] == 2
    assert payload["insights"] == []
    assert payload["insight_dismissals"] == []
    serialized = json.dumps(payload)
    forbidden_values = [
        str(user.id),
        str(entry.id),
        str(tag.id),
        str(symptom.id),
        str(entry_tag.entry_id),
        str(entry_tag.tag_id),
        str(entry_symptom.entry_id),
        str(entry_symptom.symptom_id),
    ]
    for value in forbidden_values:
        assert value not in serialized
    for forbidden_key in ["user_id", "entry_id", "tag_id", "symptom_id"]:
        assert forbidden_key not in serialized


@pytest.mark.asyncio
async def test_export_includes_insights_and_dismissals_without_ids() -> None:
    user = make_user()
    entry = make_entry(user)
    insight = _make_insight(user)
    subject_key = insight_subject_key(insight)
    dismissal = _make_dismissal(user, subject_key=subject_key, insight_id=insight.id)

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result([entry]),
            _scalar_optional_result(None),
            _row_result([]),
            _row_result([]),
            _scalar_result([insight]),
            _prefs_keys_result([]),
            _scalar_result([dismissal]),
        ]
    )

    envelope = await build_export_envelope(db, user=user)
    payload = envelope.model_dump(mode="json")

    assert payload["format_version"] == "1.3"
    assert len(payload["insights"]) == 1
    assert payload["insights"][0]["statement"] == "Statement for energy"
    assert payload["insights"][0]["visibility"] == "dismissed"
    assert payload["insights"][0]["subject_key"] == subject_key
    assert "id" not in payload["insights"][0]
    assert payload["insight_dismissals"] == [
        {
            "subject_key": subject_key,
            "dismissed_at": dismissal.dismissed_at.isoformat(),
            "created_at": dismissal.created_at.isoformat(),
        }
    ]
    serialized = json.dumps(payload)
    assert str(insight.id) not in serialized
    assert str(dismissal.id) not in serialized
    assert str(user.id) not in serialized
    assert "insight_id" not in serialized


@pytest.mark.asyncio
async def test_export_csv_and_zip_render() -> None:
    user = make_user()
    entry = make_entry(user, cycle_day=8, note=None)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result([entry]),
            _scalar_optional_result(None),
            _row_result([]),
            _row_result([]),
            _scalar_result([]),
            _prefs_keys_result([]),
            _scalar_result([]),
        ]
    )

    envelope = await build_export_envelope(db, user=user)
    csv_bytes = render_export_csv(envelope)
    zip_bytes = render_export_zip(envelope)

    csv_text = csv_bytes.decode("utf-8-sig")
    assert "mood_score" in csv_text
    assert "cycle_day" in csv_text
    assert ",8," in csv_text
    assert "mood_scale" in csv_text
    assert "1=very bad; 5=very good" in csv_text
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        assert sorted(archive.namelist()) == ["README.txt", "export.json"]
        readme = archive.read("README.txt").decode("utf-8")
        assert "stress: 1=relaxed; 5=very stressed" in readme
        assert "insight_dismissals" in readme
        data = json.loads(archive.read("export.json"))
        assert data["format_version"] == "1.3"
        assert data["score_legend"]["energy"]["max_label"] == "full of energy"
        assert data["entries"][0]["date"] == entry.entry_date.isoformat()
        assert "insight_dismissals" in data

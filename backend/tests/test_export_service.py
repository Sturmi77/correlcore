"""Tests for M2 data export."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.export_service import build_export_envelope, render_export_csv, render_export_zip
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


@pytest.mark.asyncio
async def test_export_omits_internal_ids_and_includes_assigned_data() -> None:
    user = make_user(email="me@example.test")
    entry = make_entry(user, mood_score=5, note="private note")
    tag = make_tag(user, slug="focus", name="Focus")
    symptom = make_symptom(user, slug="migraine", name="Migraine")
    entry_tag = make_entry_tag(entry=entry, tag=tag)
    entry_symptom = make_entry_symptom(entry=entry, symptom=symptom, intensity=2)

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result([entry]),
            _row_result([(entry_tag.entry_id, tag)]),
            _row_result([(entry_symptom.entry_id, entry_symptom.intensity, symptom)]),
        ]
    )

    envelope = await build_export_envelope(db, user=user)
    payload = envelope.model_dump(mode="json")

    assert payload["user"]["email"] == "me@example.test"
    assert payload["entries"][0]["note"] == "private note"
    assert payload["entries"][0]["tags"][0]["name"] == "Focus"
    assert payload["entries"][0]["symptoms"][0]["intensity"] == 2
    serialized = json.dumps(payload)
    assert str(user.id) not in serialized
    assert str(entry.id) not in serialized


@pytest.mark.asyncio
async def test_export_csv_and_zip_render() -> None:
    user = make_user()
    entry = make_entry(user, note=None)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_result([entry]), _row_result([]), _row_result([])])

    envelope = await build_export_envelope(db, user=user)
    csv_bytes = render_export_csv(envelope)
    zip_bytes = render_export_zip(envelope)

    assert b"mood_score" in csv_bytes
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        assert sorted(archive.namelist()) == ["README.txt", "export.json"]
        data = json.loads(archive.read("export.json"))
        assert data["entries"][0]["date"] == entry.entry_date.isoformat()

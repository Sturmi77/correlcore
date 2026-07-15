"""Unit tests for note signal extraction (#201)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import settings
from app.models.entry import NoteVisibility
from app.services.note_signal_extractor import (
    DICTIONARY_CONFIDENCE,
    EXTRACTOR_V,
    extract_and_store_signals_for_entry,
    extract_signals_from_text,
    filter_signals_for_insight,
    meets_insight_threshold,
    preprocess_note,
)
from tests.conftest import make_entry, make_user


def test_preprocess_note_lowercases_and_strips_html() -> None:
    assert preprocess_note("<p>Stress</p> im <b>Büro</b>") == "stress im büro"


def test_extract_signals_dictionary_match() -> None:
    signals = extract_signals_from_text("Hatte heute einen Streit mit Kollegen")
    keys = {item.signal for item in signals}
    assert "konflikt" in keys
    konflikt = next(item for item in signals if item.signal == "konflikt")
    assert konflikt.confidence == DICTIONARY_CONFIDENCE
    assert konflikt.source_span == "streit"


def test_extract_signals_regex_match() -> None:
    signals = extract_signals_from_text("Schlechter Schlaf nach Deadline")
    keys = {item.signal for item in signals}
    assert "schlechter_schlaf" in keys
    assert "arbeit" in keys
    schlaf = next(item for item in signals if item.signal == "schlechter_schlaf")
    assert schlaf.confidence == 0.80


def test_extract_signals_english_dictionary_terms() -> None:
    signals = extract_signals_from_text("Went for a walk outside, headache later")
    keys = {item.signal for item in signals}
    assert "spaziergang" in keys
    assert "kopfschmerz" in keys


def test_filter_signals_for_insight_respects_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "NOTE_SIGNAL_MIN_CONFIDENCE", 0.70)
    signals = extract_signals_from_text("deprimiert und nur 5 h")
    low = next(item for item in signals if item.signal == "niedergeschlagen")
    assert low.confidence == 0.65
    assert meets_insight_threshold(low.confidence) is False
    included = filter_signals_for_insight(signals)
    assert all(item.confidence >= 0.70 for item in included)
    assert all(item.signal != "niedergeschlagen" for item in included)


@pytest.mark.asyncio
async def test_extract_and_store_skips_hidden_notes() -> None:
    user = make_user()
    entry = make_entry(user, note="Stress im Büro")
    entry.note_visibility = NoteVisibility.HIDDEN

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=entry)),
            MagicMock(),
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()

    stored = await extract_and_store_signals_for_entry(
        db,
        user_id=user.id,
        entry_id=entry.id,
    )

    assert stored == []
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_extract_and_store_persists_signals_with_extractor_version() -> None:
    user = make_user()
    entry = make_entry(user, note="Stress und Streit")
    entry.note_visibility = NoteVisibility.FULL

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=entry)),
            MagicMock(),
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()

    stored = await extract_and_store_signals_for_entry(
        db,
        user_id=user.id,
        entry_id=entry.id,
    )

    assert len(stored) >= 2
    assert all(row.extractor_v == EXTRACTOR_V for row in stored)
    assert all(row.user_id == user.id for row in stored)
    assert all(row.entry_id == entry.id for row in stored)
    db.add.assert_called()


@pytest.mark.asyncio
async def test_extract_and_store_returns_empty_for_missing_entry() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    stored = await extract_and_store_signals_for_entry(
        db,
        user_id=user.id,
        entry_id=uuid.uuid4(),
    )
    assert stored == []

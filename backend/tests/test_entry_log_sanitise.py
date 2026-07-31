"""Tests for entry SHD log sanitisation (#547 Stage 1)."""

from __future__ import annotations

import uuid
from datetime import date

from app.models.entry import BleedingLevel, Entry, EntrySlot, WorkContext
from app.utils.entry_log_sanitise import sanitise_entry_for_log


def test_sanitise_entry_for_log_redacts_cycle_fields() -> None:
    entry = Entry(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        entry_date=date(2026, 7, 31),
        slot=EntrySlot.DAY,
        mood_score=3,
        energy=3,
        stress=3,
        work_context=WorkContext.HOMEOFFICE,
        cycle_day=12,
        cycle_bleeding_level=BleedingLevel.MEDIUM,
    )

    payload = sanitise_entry_for_log(entry)

    assert payload["cycle_day"] == "<redacted>"
    assert payload["cycle_bleeding_level"] == "<redacted>"
    assert payload["entry_date"] == "2026-07-31"
    assert "mood_score" not in payload
    assert "note" not in payload


def test_sanitise_entry_for_log_dict_uses_metadata_allowlist() -> None:
    entry_id = uuid.uuid4()
    user_id = uuid.uuid4()
    dump = {
        "id": entry_id,
        "user_id": user_id,
        "entry_date": date(2026, 7, 31),
        "slot": EntrySlot.DAY,
        "mood_score": 5,
        "energy": 4,
        "stress": 2,
        "note": "secret",
        "cycle_day": 8,
        "cycle_bleeding_level": BleedingLevel.HEAVY,
        "symptoms": {"x": 2},
    }

    payload = sanitise_entry_for_log(dump)

    assert payload == {
        "id": str(entry_id),
        "user_id": str(user_id),
        "entry_date": "2026-07-31",
        "slot": "day",
        "cycle_day": "<redacted>",
        "cycle_bleeding_level": "<redacted>",
    }

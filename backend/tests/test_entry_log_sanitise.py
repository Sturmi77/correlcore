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

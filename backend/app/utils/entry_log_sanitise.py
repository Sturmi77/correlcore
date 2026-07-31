"""Redact Sensitive Health Data (SHD) before logging entries (ADR-0033)."""

from __future__ import annotations

from typing import Any

from app.models.entry import BleedingLevel, Entry

SHD_ENTRY_FIELDS = frozenset({"cycle_day", "cycle_bleeding_level"})


def sanitise_entry_for_log(entry: Entry | dict[str, Any]) -> dict[str, Any]:
    """Return a log-safe snapshot with cycle SHD fields redacted."""
    if isinstance(entry, Entry):
        payload: dict[str, Any] = {
            "id": str(entry.id),
            "user_id": str(entry.user_id),
            "entry_date": entry.entry_date.isoformat(),
            "slot": entry.slot.value,
        }
        for field in SHD_ENTRY_FIELDS:
            value = getattr(entry, field, None)
            if value is not None:
                if isinstance(value, BleedingLevel):
                    payload[field] = "<redacted>"
                else:
                    payload[field] = "<redacted>"
        return payload

    redacted = dict(entry)
    for field in SHD_ENTRY_FIELDS:
        if field in redacted and redacted[field] is not None:
            redacted[field] = "<redacted>"
    return redacted

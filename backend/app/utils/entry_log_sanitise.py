"""Redact Sensitive Health Data (SHD) before logging entries (ADR-0033)."""

from __future__ import annotations

from typing import Any

from app.models.entry import Entry

SHD_ENTRY_FIELDS = frozenset({"cycle_day", "cycle_bleeding_level"})

# Metadata allowed in log-safe snapshots — never mood/energy/stress/note/symptoms.
_LOG_SAFE_META_FIELDS = ("id", "user_id", "entry_date", "slot")


def _stringify_meta(field: str, value: Any) -> Any:
    if value is None:
        return None
    if field in {"id", "user_id"}:
        return str(value)
    if field == "entry_date":
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    if field == "slot":
        return getattr(value, "value", value)
    return value


def sanitise_entry_for_log(entry: Entry | dict[str, Any]) -> dict[str, Any]:
    """Return a log-safe snapshot with cycle SHD fields redacted.

    Only metadata plus redacted SHD markers are included. Mood, energy, stress,
    notes, and symptom payloads are never echoed — including when the caller
    passes a full ``model_dump()`` dictionary.
    """
    if isinstance(entry, Entry):
        source: dict[str, Any] = {
            "id": entry.id,
            "user_id": entry.user_id,
            "entry_date": entry.entry_date,
            "slot": entry.slot,
            "cycle_day": entry.cycle_day,
            "cycle_bleeding_level": entry.cycle_bleeding_level,
        }
    else:
        source = entry

    payload: dict[str, Any] = {}
    for field in _LOG_SAFE_META_FIELDS:
        if field in source:
            payload[field] = _stringify_meta(field, source[field])

    for field in SHD_ENTRY_FIELDS:
        if field in source and source[field] is not None:
            payload[field] = "<redacted>"
    return payload

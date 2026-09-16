"""Short note preview helper (ADR-N-01)."""

from __future__ import annotations

import re

from app.models.entry import Entry

NOTE_SUMMARY_MAX_LENGTH = 120

_SENTENCE_END = re.compile(r"[.!?]\s")


def compute_note_summary_short(
    note: str | None, *, max_length: int = NOTE_SUMMARY_MAX_LENGTH
) -> str | None:
    """Return a truncated preview of ``note`` (first sentence or max_length chars)."""

    if note is None:
        return None
    text = note.strip()
    if not text:
        return None

    match = _SENTENCE_END.search(text)
    if match and match.start() + 1 <= max_length:
        candidate = text[: match.start() + 1].strip()
    else:
        candidate = text

    if len(candidate) <= max_length:
        return candidate
    return candidate[: max_length - 1].rstrip() + "…"


def entry_has_note(entry: Entry) -> bool:
    """True when the entry has ciphertext or a short summary preview."""
    return bool(entry.note_enc and str(entry.note_enc).strip()) or bool(
        entry.note_summary_short and entry.note_summary_short.strip()
    )

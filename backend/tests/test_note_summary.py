"""Unit tests for note summary truncation (ADR-N-01)."""

from __future__ import annotations

from app.services.note_summary import NOTE_SUMMARY_MAX_LENGTH, compute_note_summary_short


def test_compute_note_summary_short_returns_none_for_empty() -> None:
    assert compute_note_summary_short(None) is None
    assert compute_note_summary_short("   ") is None


def test_compute_note_summary_short_uses_first_sentence() -> None:
    text = "Guter Tag. Danach wurde es stressig."
    assert compute_note_summary_short(text) == "Guter Tag."


def test_compute_note_summary_short_truncates_long_text() -> None:
    text = "a" * 200
    summary = compute_note_summary_short(text)
    assert summary is not None
    assert len(summary) <= NOTE_SUMMARY_MAX_LENGTH
    assert summary.endswith("…")


def test_compute_note_summary_short_keeps_short_text() -> None:
    text = "Kurze Notiz"
    assert compute_note_summary_short(text) == text

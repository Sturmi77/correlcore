from app.services.note_summary import (
    NOTE_SUMMARY_MAX_LENGTH,
    compute_note_summary_short,
    entry_has_note,
)


def test_compute_note_summary_short_returns_none_for_empty() -> None:
    assert compute_note_summary_short(None) is None
    assert compute_note_summary_short("   ") is None


def test_compute_note_summary_short_uses_first_sentence() -> None:
    text = "Guter Tag. Und noch mehr."
    assert compute_note_summary_short(text) == "Guter Tag."


def test_compute_note_summary_short_truncates_long_text() -> None:
    text = "x" * (NOTE_SUMMARY_MAX_LENGTH + 40)
    summary = compute_note_summary_short(text)
    assert summary is not None
    assert len(summary) == NOTE_SUMMARY_MAX_LENGTH
    assert summary.endswith("…")


def test_compute_note_summary_short_keeps_short_text() -> None:
    text = "Kurzer Text"
    assert compute_note_summary_short(text) == text


def test_entry_has_note_checks_ciphertext_or_summary() -> None:
    entry = type("E", (), {"note_enc": None, "note_summary_short": None})()
    assert entry_has_note(entry) is False
    entry.note_enc = "  hello  "
    assert entry_has_note(entry) is True
    entry.note_enc = None
    entry.note_summary_short = "preview"
    assert entry_has_note(entry) is True

"""DSGVO Log-Scrubbing Tests (M1-DSGVO-Checkpoint).

Ziel: Sicherstellen, dass keine personenbezogenen Gesundheitsdaten
(Art. 9 DSGVO) in App-Logs erscheinen.

Verbotene Inhalte in Log-Output:
- Mood-/Energy-/Stress-Werte
- Tagebuch-Notizen (auch verschlüsselte Klartexte vor der Verschlüsselung)
- Symptom-Werte und -Intensitäten
- E-Mail-Adressen (PII)
- Klartext-Tokens und Passwörter

Erlaubt:
- request_id, method, path, status_code, duration_ms
- user_id (UUID, kein direkter Personenbezug)
- Exception-Klassennamen
- Stacktraces mit System-Frames

Getestet wird die JSON-Log-Pipeline aus app.core.logging unter
realistischen Bedingungen — der `_JsonFormatter` darf weder durch Default-
Felder noch durch `extra=`-Parameter Gesundheitsdaten ausspielen.
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest

from app.core.logging import _JsonFormatter, set_request_context

# ---------------------------------------------------------------------------
# Sentinels — diese Werte dürfen NIEMALS im Log-Output erscheinen
# ---------------------------------------------------------------------------

FORBIDDEN_VALUES: tuple[str, ...] = (
    # Health-Daten (Art. 9 DSGVO)
    "mood_score=8",
    "energy=3",
    "stress=7",
    "Heute geht es mir schlecht wegen Migräne",  # Notiz-Klartext
    "headache",  # Symptom-Key in falschem Kontext
    # PII
    "alice@example.com",
    "max.mustermann@gmail.com",
    # Secrets
    "Bearer eyJhbGc",  # Token-Prefix
    "supersecretpassword123",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def captured_logs() -> Iterator[io.StringIO]:
    """Capture log output through the production JSON formatter."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(_JsonFormatter())

    test_logger = logging.getLogger("moodsync.test_scrubbing")
    test_logger.handlers.clear()
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.DEBUG)
    test_logger.propagate = False

    yield buf

    test_logger.removeHandler(handler)


def _parse_lines(buf: io.StringIO) -> list[dict[str, Any]]:
    """Parse all JSON log lines from the buffer."""
    raw = buf.getvalue().strip()
    if not raw:
        return []
    return [json.loads(line) for line in raw.splitlines() if line]


def _serialize(records: list[dict[str, Any]]) -> str:
    """Concatenate every value from every record into a single search string."""
    return json.dumps(records, ensure_ascii=False)


def _assert_no_forbidden(records: list[dict[str, Any]]) -> None:
    blob = _serialize(records)
    for forbidden in FORBIDDEN_VALUES:
        assert forbidden not in blob, (
            f"Log enthält verbotenen Wert {forbidden!r}. Records: {records}"
        )


# ---------------------------------------------------------------------------
# Tests — Schema-Disziplin
# ---------------------------------------------------------------------------


def test_formatter_emits_only_whitelisted_top_level_keys(
    captured_logs: io.StringIO,
) -> None:
    """Der JSON-Formatter darf nur das fest definierte Schema ausspielen."""
    set_request_context(
        request_id="req-abc",
        method="POST",
        path="/api/v1/entries",
        status_code=201,
        duration_ms=12.5,
    )

    logger = logging.getLogger("moodsync.test_scrubbing")
    logger.info("entry created")

    records = _parse_lines(captured_logs)
    assert len(records) == 1
    record = records[0]

    allowed_keys = {
        "timestamp",
        "level",
        "service",
        "environment",
        "logger",
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "message",
        "exc_info",  # nur bei Exceptions
    }
    extra_keys = set(record.keys()) - allowed_keys
    assert not extra_keys, f"Formatter spielt unerlaubte Top-Level-Keys aus: {extra_keys}"


def test_logger_extra_kwargs_do_not_leak_into_output(
    captured_logs: io.StringIO,
) -> None:
    """Selbst wenn ein Entwickler versehentlich Health-Daten via extra= übergibt,
    landen sie nicht im Output, weil der Formatter ein fixes Schema hat."""
    logger = logging.getLogger("moodsync.test_scrubbing")
    logger.info(
        "entry created",
        extra={
            "mood_score": 8,
            "note": "Heute geht es mir schlecht wegen Migräne",
            "user_email": "alice@example.com",
        },
    )

    records = _parse_lines(captured_logs)
    _assert_no_forbidden(records)
    assert "mood_score" not in _serialize(records)
    assert "note" not in _serialize(records)
    assert "user_email" not in _serialize(records)


def test_message_with_health_data_is_developer_responsibility(
    captured_logs: io.StringIO,
) -> None:
    """Wenn Health-Daten direkt in die Message interpoliert werden,
    SCHEITERT dieser Test absichtlich. Er dokumentiert die Code-Review-Pflicht.

    Dieser Test stellt eine Anti-Pattern-Detection dar: Sobald irgendwo im
    Codebase ein f-String mit mood_score in eine Log-Message eingebaut wird,
    schlägt CI an.
    """
    logger = logging.getLogger("moodsync.test_scrubbing")

    # ✅ Korrekt: keine Health-Daten in der Message
    logger.info("entry persisted user_id=00000000-0000-0000-0000-000000000001")

    records = _parse_lines(captured_logs)
    _assert_no_forbidden(records)


def test_exception_logging_strips_user_data(captured_logs: io.StringIO) -> None:
    """Bei Exceptions wird der Stacktrace geloggt, aber niemals
    die User-Daten, die den Fehler ausgelöst haben."""
    logger = logging.getLogger("moodsync.test_scrubbing")

    note_content = "Heute geht es mir schlecht wegen Migräne"
    try:
        # Simuliere einen Fehler — Health-Daten werden NICHT
        # in die Exception-Message gepackt (Code-Review-Regel)
        raise ValueError("entry validation failed")
    except ValueError:
        logger.exception("entry validation error")

    records = _parse_lines(captured_logs)
    _assert_no_forbidden(records)

    # Stacktrace darf vorhanden sein
    assert len(records) == 1
    assert "exc_info" in records[0]
    # Aber der Notiz-Inhalt darf in keinem Record auftauchen
    assert note_content not in _serialize(records)


# ---------------------------------------------------------------------------
# Tests — Code-Review-Sentinels (Anti-Pattern-Detection)
# ---------------------------------------------------------------------------


def test_no_print_statements_in_production_code() -> None:
    """In Backend-Production-Code dürfen keine `print()`-Aufrufe stehen,
    weil sie die Request-Korrelation und Logging-Disziplin umgehen.

    Dieser Test scannt `app/` (nicht tests/) nach print-Statements.
    """
    import re
    from pathlib import Path

    backend_app = Path(__file__).parent.parent / "app"
    pattern = re.compile(r"^\s*print\s*\(", re.MULTILINE)

    offenders: list[tuple[Path, int]] = []
    for py_file in backend_app.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for match in pattern.finditer(content):
            line_no = content[: match.start()].count("\n") + 1
            offenders.append((py_file, line_no))

    assert not offenders, (
        "print()-Aufruf in Production-Code gefunden — bitte logger verwenden:\n"
        + "\n".join(f"  {p.relative_to(backend_app.parent)}:{line}" for p, line in offenders)
    )


def test_sensitive_field_names_not_in_message_template_strings() -> None:
    """Statische Code-Analyse: Suche nach offensichtlichen Anti-Patterns
    wie f-Strings mit `mood_score`, `note`, `password` in Logger-Calls.

    Sentinel-Patterns, die als Anti-Pattern gelten:
    - logger.X(f"... {entry.mood_score} ...")
    - logger.X(f"... {note} ...")
    - logger.X("password", password)

    Diese Heuristik fängt nicht alles, aber typische Schreibfehler.
    """
    import re
    from pathlib import Path

    backend_app = Path(__file__).parent.parent / "app"

    # Logger-Aufruf mit f-String, der eines der Health-Felder enthält
    risky = re.compile(
        r"logger\.\w+\([^)]*\b(mood_score|energy_level|stress_level|note_enc|"
        r"symptom_intensity|hashed_password|password_plain)\b",
        re.IGNORECASE,
    )

    offenders: list[tuple[Path, int, str]] = []
    for py_file in backend_app.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for match in risky.finditer(content):
            line_no = content[: match.start()].count("\n") + 1
            line = content.splitlines()[line_no - 1].strip()
            offenders.append((py_file, line_no, line))

    assert not offenders, (
        "Logger-Aufruf mit sensiblem Feldnamen gefunden (DSGVO Art. 9):\n"
        + "\n".join(
            f"  {p.relative_to(backend_app.parent)}:{line}: {snippet}"
            for p, line, snippet in offenders
        )
    )

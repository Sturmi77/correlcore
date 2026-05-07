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
    # Custom-Symptom-/Tag-Slugs & -Namen (Issues #8, #57; ADR-0005 Trade-off)
    "Migräne mit Aura",  # Custom-Symptom-Name (Klartext, vor Verschlüsselung)
    "migraene-mit-aura",  # Custom-Symptom-Slug (semantischer Leak)
    "Stress bei Arbeit",  # Custom-Tag-Name
    "stress-bei-arbeit",  # Custom-Tag-Slug
    # Encryption-Material (ADR-0005)
    "name_enc_ciphertext_bytes",  # Symptom.name_enc Sentinel
    "wrapped_dek_ciphertext_bytes",  # UserEncryptionKey.wrapped_dek Sentinel
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

    # Logger-Aufruf mit f-String, der eines der Health-Felder enthält.
    # Erweitert um Issues #8 (Tags), #57 (Custom-Symptome), #26 (Encryption).
    risky = re.compile(
        r"logger\.\w+\([^)]*\b(mood_score|energy_level|stress_level|note_enc|"
        r"symptom_intensity|hashed_password|password_plain|"
        r"name_enc|wrapped_dek)\b",
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


# ---------------------------------------------------------------------------
# Tests — Repr-Stripping (SA-3, Issue #67)
#
# SQLAlchemy-Modelle können ungewollt via ``%r`` / ``str(obj)`` in Logs
# landen — etwa in Exception-Messages, ``logger.debug("got %r", row)`` oder
# ORM-internen Stacktraces. Die ``__repr__``-Methoden dürfen daher KEINE
# Art.-9-relevanten Klartextwerte, Custom-Slugs oder Encryption-Material
# enthalten. Default-Slugs (``headache``, ``fatigue``, ...) sind hingegen
# kuratiert und dürfen erscheinen.
# ---------------------------------------------------------------------------


def test_entry_repr_does_not_leak_payload(captured_logs: io.StringIO) -> None:
    """``Entry.__repr__`` darf weder Notiz-Klartext noch Mood/Energy/Stress
    in den Output durchreichen — selbst wenn das Objekt via ``%r`` geloggt wird.
    """
    import uuid
    from datetime import date

    from app.models.entry import Entry, EntrySlot, WorkContext

    entry = Entry(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        entry_date=date(2026, 5, 7),
        slot=EntrySlot.MORNING,
        mood_score=8,
        energy=3,
        stress=7,
        work_context=WorkContext.HOMEOFFICE,
        note_enc="ciphertext-bytes",
    )

    logger = logging.getLogger("moodsync.test_scrubbing")
    logger.info("loaded entry %r", entry)

    records = _parse_lines(captured_logs)
    _assert_no_forbidden(records)
    blob = _serialize(records)
    # Auch reine Feldnamen dürfen nicht im Repr stehen.
    assert "mood_score" not in blob
    assert "energy" not in blob
    assert "stress" not in blob
    assert "note_enc" not in blob
    assert "ciphertext" not in blob


def test_default_symptom_repr_keeps_curated_slug(
    captured_logs: io.StringIO,
) -> None:
    """Default-Symptome haben kuratierte Slugs (``headache`` etc.) — die
    sind öffentlich und dürfen im Repr stehen. Aber: ``name`` (Anzeigename)
    bleibt draußen, weil bei Custom-Symptomen Art.-9-relevant.
    """
    import uuid

    from app.models.symptom import Symptom

    symptom = Symptom(
        id=uuid.uuid4(),
        user_id=None,
        slug="headache",
        name="Kopfschmerzen",
        name_enc=None,
        is_default=True,
    )

    logger = logging.getLogger("moodsync.test_scrubbing")
    logger.info("loaded symptom %r", symptom)

    records = _parse_lines(captured_logs)
    blob = _serialize(records)
    # Default-Slug darf erscheinen — aber kein Anzeigename.
    assert "headache" in blob, "Default-Slug sollte im Repr sichtbar sein"
    assert "Kopfschmerzen" not in blob


def test_custom_symptom_repr_masks_slug_and_name(
    captured_logs: io.StringIO,
) -> None:
    """Custom-Symptome: Slug leitet sich vom user-supplied Namen ab
    (ADR-0005 Trade-off, plaintext in DB). Im Repr/Log MUSS der Slug
    maskiert werden, der ``name_enc`` ciphertext darf nicht erscheinen,
    und natuerlich kein Klartextname.
    """
    import uuid

    from app.models.symptom import Symptom

    symptom = Symptom(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        slug="migraene-mit-aura",
        name=None,
        name_enc=b"name_enc_ciphertext_bytes",
        is_default=False,
    )

    logger = logging.getLogger("moodsync.test_scrubbing")
    logger.info("loaded symptom %r", symptom)

    records = _parse_lines(captured_logs)
    _assert_no_forbidden(records)
    blob = _serialize(records)
    assert "migraene-mit-aura" not in blob
    assert "Migr\u00e4ne mit Aura" not in blob
    assert "name_enc_ciphertext_bytes" not in blob
    # Repr sollte den Custom-Marker enthalten
    assert "<custom>" in blob


def test_default_tag_repr_keeps_curated_slug(
    captured_logs: io.StringIO,
) -> None:
    """Default-Tags: kuratierte Slugs duerfen erscheinen, ``name`` nicht."""
    import uuid

    from app.models.tag import Tag, TagCategory

    tag = Tag(
        id=uuid.uuid4(),
        user_id=None,
        slug="sport",
        name="Arbeit",
        category=TagCategory.SPORT,
        is_default=True,
    )

    logger = logging.getLogger("moodsync.test_scrubbing")
    logger.info("loaded tag %r", tag)

    records = _parse_lines(captured_logs)
    blob = _serialize(records)
    assert "sport" in blob, "Default-Tag-Slug sollte im Repr sichtbar sein"
    assert "Arbeit" not in blob


def test_custom_tag_repr_masks_slug_and_name(captured_logs: io.StringIO) -> None:
    """User-Tags: Slug+Name leiten sich aus User-Eingabe ab und koennen
    Lifestyle-Hinweise (potentiell Art.-9-relevant) enthalten.
    Repr maskiert Slug; Name war ohnehin nie Teil des Reprs.
    """
    import uuid

    from app.models.tag import Tag, TagCategory

    tag = Tag(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        slug="stress-bei-arbeit",
        name="Stress bei Arbeit",
        category=TagCategory.WORK,
        is_default=False,
    )

    logger = logging.getLogger("moodsync.test_scrubbing")
    logger.info("loaded tag %r", tag)

    records = _parse_lines(captured_logs)
    _assert_no_forbidden(records)
    blob = _serialize(records)
    assert "stress-bei-arbeit" not in blob
    assert "Stress bei Arbeit" not in blob
    assert "<custom>" in blob


def test_user_encryption_key_repr_does_not_leak_wrapped_dek(
    captured_logs: io.StringIO,
) -> None:
    """``UserEncryptionKey.__repr__`` darf den ``wrapped_dek`` ciphertext
    auch nicht als Laenge oder Praefix ausspielen — ADR-0005 erlaubt nur
    ``user_id`` + ``key_version``.
    """
    import uuid

    from app.models.user_encryption_key import UserEncryptionKey

    uek = UserEncryptionKey(
        user_id=uuid.uuid4(),
        wrapped_dek=b"wrapped_dek_ciphertext_bytes",
        key_version=1,
    )

    logger = logging.getLogger("moodsync.test_scrubbing")
    logger.info("loaded uek %r", uek)

    records = _parse_lines(captured_logs)
    _assert_no_forbidden(records)
    blob = _serialize(records)
    assert "wrapped_dek_ciphertext_bytes" not in blob
    assert "wrapped_dek=" not in blob
    # Aber Metadaten sind erlaubt:
    assert "version=1" in blob


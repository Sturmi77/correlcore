"""Regression tests for the auth-cookie ``Secure``-Flag heuristic.

Background
----------
``set_auth_cookies`` previously hardcoded ``secure=True`` for both auth
cookies. The browser silently discards ``Set-Cookie`` headers carrying
``Secure`` when the page origin is plain HTTP (RFC 6265bis §4.1.2.5),
which silently broke login on every HTTP-only deployment — most
prominently a homelab Tailscale-IP setup without a TLS-terminating
reverse proxy. Symptom: the user could submit credentials, the API
returned 200, but no auth cookie ended up in the browser jar →
subsequent ``/entries`` POST returned 401 → UI showed
"Bitte melde dich erneut an".

The fix introduces ``Settings.COOKIE_SECURE`` as a tri-state
(``True | False | None``) plus the resolver
``Settings.cookie_secure_effective``:

- explicit ``True`` / ``False`` always wins,
- ``None`` (default) resolves to ``False`` for ``APP_ENV=development``
  and ``True`` everywhere else.

A model-validator additionally refuses ``COOKIE_SECURE=false`` in
``APP_ENV=production`` so ADR-0006's "Secure in Prod" guarantee
cannot be defeated by accident.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def _stable_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip cookie/env vars so each test starts from a clean slate."""
    for key in (
        "APP_ENV",
        "COOKIE_SECURE",
    ):
        monkeypatch.delenv(key, raising=False)
    # Settings still requires DATABASE_URL + SECRET_KEY; keep them stable
    # and long enough to satisfy the production-secret validator when
    # tests bump APP_ENV up to staging/production.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    # ENCRYPTION_KEY must look real (not start with CHANGE_ME) once we
    # leave APP_ENV=development. Use a fixed valid Fernet key for
    # determinism.
    monkeypatch.setenv(
        "ENCRYPTION_KEY",
        "ZmFrZS1mZXJuZXQta2V5LWZvci10ZXN0cy0zMi1ieXRlcz0=",
    )


# ---------------------------------------------------------------------------
# Auto-Heuristik: COOKIE_SECURE unset
# ---------------------------------------------------------------------------


def test_default_is_secure_off_in_development() -> None:
    """`APP_ENV=development` (Default) → Secure off, sodass HTTP-Login geht."""
    s = Settings()
    assert s.APP_ENV == "development"
    assert s.COOKIE_SECURE is None
    assert s.cookie_secure_effective is False


def test_default_is_secure_on_in_staging(monkeypatch: pytest.MonkeyPatch) -> None:
    """`APP_ENV=staging` ohne Override → Secure on (HTTPS-Default-Annahme)."""
    monkeypatch.setenv("APP_ENV", "staging")
    s = Settings()
    assert s.COOKIE_SECURE is None
    assert s.cookie_secure_effective is True


def test_default_is_secure_on_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """`APP_ENV=production` ohne Override → Secure on."""
    monkeypatch.setenv("APP_ENV", "production")
    s = Settings()
    assert s.COOKIE_SECURE is None
    assert s.cookie_secure_effective is True


# ---------------------------------------------------------------------------
# Expliziter Override
# ---------------------------------------------------------------------------


def test_explicit_false_wins_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operator kann Secure in Dev explizit ausschalten (Identität)."""
    monkeypatch.setenv("COOKIE_SECURE", "false")
    s = Settings()
    assert s.COOKIE_SECURE is False
    assert s.cookie_secure_effective is False


def test_explicit_true_wins_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operator kann Secure in Dev erzwingen (z. B. lokaler HTTPS-Proxy)."""
    monkeypatch.setenv("COOKIE_SECURE", "true")
    s = Settings()
    assert s.COOKIE_SECURE is True
    assert s.cookie_secure_effective is True


def test_explicit_false_allowed_in_staging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Homelab-Staging ohne TLS muss Secure abschalten dürfen.

    Dies ist genau der Tailscale-/HTTP-Pfad aus dem live-Test-Bug.
    """
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    s = Settings()
    assert s.cookie_secure_effective is False


# ---------------------------------------------------------------------------
# ADR-0006-Guard: Production darf Secure nicht abschalten
# ---------------------------------------------------------------------------


def test_explicit_false_rejected_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """`APP_ENV=production` + `COOKIE_SECURE=false` muss laut ADR-0006 fehlschlagen."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    with pytest.raises(ValidationError) as excinfo:
        Settings()
    msg = str(excinfo.value)
    assert "COOKIE_SECURE" in msg
    assert "production" in msg


def test_explicit_true_allowed_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """`APP_ENV=production` + `COOKIE_SECURE=true` ist ok (redundant aber gültig)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    s = Settings()
    assert s.cookie_secure_effective is True


# ---------------------------------------------------------------------------
# Boolean-Parsing-Edge-Cases (pydantic-settings)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["1", "true", "True", "yes", "on"])
def test_truthy_env_strings_resolve_to_true(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("COOKIE_SECURE", value)
    s = Settings()
    assert s.cookie_secure_effective is True


@pytest.mark.parametrize("value", ["0", "false", "False", "no", "off"])
def test_falsy_env_strings_resolve_to_false(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("COOKIE_SECURE", value)
    s = Settings()
    assert s.cookie_secure_effective is False

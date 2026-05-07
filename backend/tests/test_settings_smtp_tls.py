"""Regression tests for the SMTP-TLS auto-default.

Background
----------
``SMTP_USE_TLS`` was previously hardcoded to ``True``. Mailpit and MailHog
(the standard dev/staging mail catchers in our homelab Compose-Stacks)
listen on port 1025 in *plain* SMTP mode and do not advertise STARTTLS,
so ``aiosmtplib.send(start_tls=True)`` raised ``SMTPException`` and
``email_service._send`` swallowed it. Result: registration succeeded but
no verification mail was ever delivered, and the user got no error
feedback (deliberate, to avoid email enumeration).

The fix turns ``SMTP_USE_TLS`` into a tri-state (``True | False | None``)
with ``None`` as default. The ``smtp_should_use_tls`` property resolves
``None`` via a heuristic: STARTTLS on when ``SMTP_USER`` is non-empty
(real relay = needs auth = needs TLS), STARTTLS off when no auth is
configured (dev catcher = plain). Operators can still pin the value
explicitly via the ``.env``.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def _stable_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every SMTP-related env so tests can set them deterministically."""
    for key in (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "SMTP_USE_TLS",
    ):
        monkeypatch.delenv(key, raising=False)
    # Required by Settings — keep them stable, irrelevant for these tests.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)


def test_default_is_auto_off_without_user() -> None:
    """Default (`SMTP_USE_TLS` unset, no `SMTP_USER`): TLS off — Mailpit-Pfad."""
    s = Settings()
    assert s.SMTP_USE_TLS is None
    assert s.smtp_should_use_tls is False


def test_default_is_auto_on_with_user(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default + `SMTP_USER` set → TLS on — Production-Relay-Pfad."""
    monkeypatch.setenv("SMTP_USER", "noreply@example.com")
    s = Settings()
    assert s.SMTP_USE_TLS is None
    assert s.smtp_should_use_tls is True


def test_explicit_true_wins_over_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operator forces TLS on even without auth (e.g. trusted-network relay)."""
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    s = Settings()
    assert s.SMTP_USE_TLS is True
    assert s.smtp_should_use_tls is True


def test_explicit_false_wins_over_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operator forces TLS off even with auth (debugging / local relay)."""
    monkeypatch.setenv("SMTP_USER", "noreply@example.com")
    monkeypatch.setenv("SMTP_USE_TLS", "false")
    s = Settings()
    assert s.SMTP_USE_TLS is False
    assert s.smtp_should_use_tls is False


@pytest.mark.parametrize("value", ["1", "true", "True", "yes", "on"])
def test_truthy_env_strings_resolve_to_true(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("SMTP_USE_TLS", value)
    s = Settings()
    assert s.smtp_should_use_tls is True


@pytest.mark.parametrize("value", ["0", "false", "False", "no", "off"])
def test_falsy_env_strings_resolve_to_false(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("SMTP_USE_TLS", value)
    # Even with SMTP_USER set, an explicit false must stick.
    monkeypatch.setenv("SMTP_USER", "noreply@example.com")
    s = Settings()
    assert s.smtp_should_use_tls is False


def test_empty_user_does_not_trigger_tls_heuristic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty SMTP_USER string is functionally equivalent to unset."""
    monkeypatch.setenv("SMTP_USER", "")
    s = Settings()
    assert s.SMTP_USE_TLS is None
    assert s.smtp_should_use_tls is False

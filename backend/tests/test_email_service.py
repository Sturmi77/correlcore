"""Tests for `app.services.email_service` — Issue #70 (CQR-4).

Targets the SMTP-error code paths that were previously uncovered:

- `_send` swallows `SMTPException` (5xx response, auth failure, …) and
  logs `error_type=type(exc).__name__` instead of raising. Critical:
  registration must never fail because the relay is broken.
- `_send` swallows `OSError`/`ConnectionRefusedError` for the same
  reason (TCP-level failure, e.g. relay container is down).
- `_send` swallows `TimeoutError` (slow relay / hung handshake).
- `_send` short-circuits when `SMTP_HOST` is empty (dev/test fallback)
  and emits an INFO log entry without touching the network.
- Successful path: payload is forwarded to `aiosmtplib.send` with the
  configured host/port/auth/TLS settings.
- `send_verification_email` and `send_already_registered_email` build
  multipart/alternative messages with the correct subject, To-header,
  and verification URL derived from `FRONTEND_BASE_URL`.

Network is mocked at the `aiosmtplib.send` boundary — these are unit
tests, not integration tests against a live relay.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage
from unittest.mock import AsyncMock, patch

import aiosmtplib
import pytest

from app.services.email_service import (
    _send,
    build_login_url,
    build_verify_url,
    send_already_registered_email,
    send_verification_email,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_message(to: str = "alice@example.com") -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "test"
    msg["From"] = "sender@example.com"
    msg["To"] = to
    msg.set_content("body")
    return msg


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def test_build_verify_url_strips_trailing_slash() -> None:
    with patch("app.services.email_service.settings") as s:
        s.FRONTEND_BASE_URL = "https://moodsync.example.com/"
        url = build_verify_url("tok-123")
    assert url == "https://moodsync.example.com/auth/verify-email?token=tok-123"


def test_build_verify_url_no_trailing_slash() -> None:
    with patch("app.services.email_service.settings") as s:
        s.FRONTEND_BASE_URL = "http://localhost:5173"
        url = build_verify_url("xyz")
    assert url == "http://localhost:5173/auth/verify-email?token=xyz"


def test_build_login_url() -> None:
    with patch("app.services.email_service.settings") as s:
        s.FRONTEND_BASE_URL = "https://moodsync.example.com"
        assert build_login_url() == "https://moodsync.example.com/auth/login"


# ---------------------------------------------------------------------------
# _send — SMTP_HOST empty → short-circuit, no network call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_noop_when_smtp_host_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        patch("app.services.email_service.settings") as s,
        patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send,
    ):
        s.SMTP_HOST = ""
        with caplog.at_level(logging.INFO, logger="app.services.email_service"):
            await _send(_build_message("user@example.org"))

    mock_send.assert_not_awaited()
    # Recipient domain is logged (not full address) for DSGVO.
    record = next(r for r in caplog.records if "not sent" in r.getMessage())
    assert getattr(record, "to_domain", None) == "example.org"


@pytest.mark.asyncio
async def test_send_noop_when_smtp_host_missing_handles_no_to_header() -> None:
    """Defensive: a malformed message without `To` should not crash the log path."""
    msg = EmailMessage()
    msg["Subject"] = "x"
    msg["From"] = "from@example.com"
    msg.set_content("body")

    with (
        patch("app.services.email_service.settings") as s,
        patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send,
    ):
        s.SMTP_HOST = ""
        # Should not raise even though `message["To"]` is None.
        await _send(msg)

    mock_send.assert_not_awaited()


# ---------------------------------------------------------------------------
# _send — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_forwards_settings_to_aiosmtplib(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        patch("app.services.email_service.settings") as s,
        patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send,
    ):
        s.SMTP_HOST = "mail.relay.example.com"
        s.SMTP_PORT = 587
        s.SMTP_USER = "noreply@example.com"
        s.SMTP_PASSWORD = "s3cret"
        s.smtp_should_use_tls = True
        s.SMTP_TIMEOUT = 10

        msg = _build_message("user@example.com")
        with caplog.at_level(logging.INFO, logger="app.services.email_service"):
            await _send(msg)

    mock_send.assert_awaited_once()
    assert mock_send.await_args is not None
    kwargs = mock_send.await_args.kwargs
    assert kwargs["hostname"] == "mail.relay.example.com"
    assert kwargs["port"] == 587
    assert kwargs["username"] == "noreply@example.com"
    assert kwargs["password"] == "s3cret"
    assert kwargs["start_tls"] is True
    assert kwargs["timeout"] == 10

    sent_record = next(r for r in caplog.records if "sent" in r.getMessage())
    assert getattr(sent_record, "to_domain", None) == "example.com"


@pytest.mark.asyncio
async def test_send_passes_none_for_empty_credentials() -> None:
    """Empty SMTP_USER/SMTP_PASSWORD must surface as `None` — not as
    empty strings — so aiosmtplib skips the AUTH handshake (Mailpit-style
    catchers don't support AUTH and would error on empty creds)."""
    with (
        patch("app.services.email_service.settings") as s,
        patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send,
    ):
        s.SMTP_HOST = "mailpit"
        s.SMTP_PORT = 1025
        s.SMTP_USER = ""
        s.SMTP_PASSWORD = ""
        s.smtp_should_use_tls = False
        s.SMTP_TIMEOUT = 5

        await _send(_build_message())

    assert mock_send.await_args is not None
    kwargs = mock_send.await_args.kwargs
    assert kwargs["username"] is None
    assert kwargs["password"] is None
    assert kwargs["start_tls"] is False


# ---------------------------------------------------------------------------
# _send — error paths must be swallowed and logged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_swallows_smtp_response_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """5xx response from the relay (auth failure, mailbox full, blocked
    sender) must not propagate. Issue #70 / SA-Note #65 — registration
    must stay enumeration-safe even when the relay rejects."""
    err = aiosmtplib.SMTPResponseException(550, "Mailbox unavailable")
    with (
        patch("app.services.email_service.settings") as s,
        patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=err,
        ),
    ):
        s.SMTP_HOST = "relay.example.com"
        s.SMTP_PORT = 587
        s.SMTP_USER = "u"
        s.SMTP_PASSWORD = "p"
        s.smtp_should_use_tls = True
        s.SMTP_TIMEOUT = 10

        with caplog.at_level(logging.ERROR, logger="app.services.email_service"):
            await _send(_build_message("user@example.net"))

    record = next(r for r in caplog.records if r.levelno == logging.ERROR)
    assert "smtp send failed" in record.getMessage()
    # Privacy: error_type by class name; recipient domain only, no full address.
    assert getattr(record, "error_type", None) == "SMTPResponseException"
    assert getattr(record, "to_domain", None) == "example.net"


@pytest.mark.asyncio
async def test_send_swallows_smtp_connect_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Generic SMTPException subclass (e.g. SMTPConnectError) — covers
    handshake / banner / EHLO failures."""
    err = aiosmtplib.SMTPConnectError("could not establish connection")
    with (
        patch("app.services.email_service.settings") as s,
        patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=err,
        ),
    ):
        s.SMTP_HOST = "relay.example.com"
        s.SMTP_PORT = 587
        s.SMTP_USER = ""
        s.SMTP_PASSWORD = ""
        s.smtp_should_use_tls = False
        s.SMTP_TIMEOUT = 5

        with caplog.at_level(logging.ERROR, logger="app.services.email_service"):
            await _send(_build_message())

    record = next(r for r in caplog.records if r.levelno == logging.ERROR)
    assert getattr(record, "error_type", None) == "SMTPConnectError"


@pytest.mark.asyncio
async def test_send_swallows_connection_refused(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """OSError subclass — TCP-level failure, e.g. relay container is down."""
    with (
        patch("app.services.email_service.settings") as s,
        patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=ConnectionRefusedError(111, "Connection refused"),
        ),
    ):
        s.SMTP_HOST = "relay.example.com"
        s.SMTP_PORT = 587
        s.SMTP_USER = ""
        s.SMTP_PASSWORD = ""
        s.smtp_should_use_tls = False
        s.SMTP_TIMEOUT = 5

        with caplog.at_level(logging.ERROR, logger="app.services.email_service"):
            await _send(_build_message())

    record = next(r for r in caplog.records if r.levelno == logging.ERROR)
    assert getattr(record, "error_type", None) == "ConnectionRefusedError"


@pytest.mark.asyncio
async def test_send_swallows_timeout_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TimeoutError — slow relay or hung TLS handshake."""
    with (
        patch("app.services.email_service.settings") as s,
        patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=TimeoutError("handshake took too long"),
        ),
    ):
        s.SMTP_HOST = "relay.example.com"
        s.SMTP_PORT = 587
        s.SMTP_USER = ""
        s.SMTP_PASSWORD = ""
        s.smtp_should_use_tls = False
        s.SMTP_TIMEOUT = 5

        with caplog.at_level(logging.ERROR, logger="app.services.email_service"):
            await _send(_build_message())

    record = next(r for r in caplog.records if r.levelno == logging.ERROR)
    assert getattr(record, "error_type", None) == "TimeoutError"


# ---------------------------------------------------------------------------
# send_verification_email — composes multipart and routes through _send
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_verification_email_renders_and_dispatches() -> None:
    captured: dict[str, EmailMessage] = {}

    async def fake_send(msg: EmailMessage) -> None:
        captured["msg"] = msg

    with (
        patch("app.services.email_service.settings") as s,
        patch("app.services.email_service._send", side_effect=fake_send),
    ):
        s.FRONTEND_BASE_URL = "https://moodsync.example.com"
        s.SMTP_FROM = "noreply@example.com"
        s.EMAIL_VERIFICATION_TTL_HOURS = 24

        await send_verification_email(
            to_email="alice@example.org",
            display_name="Alice",
            token="abc-123",
        )

    msg = captured["msg"]
    assert msg["From"] == "noreply@example.com"
    assert msg["To"] == "alice@example.org"
    assert "bestätige" in msg["Subject"].lower()
    # Multipart with text + HTML alternative
    parts = list(msg.walk())
    payloads = [p.get_payload() for p in parts if not p.is_multipart()]
    body_text = "\n".join(str(p) for p in payloads)
    assert "https://moodsync.example.com/auth/verify-email?token=abc-123" in body_text


@pytest.mark.asyncio
async def test_send_verification_email_handles_none_display_name() -> None:
    """Should not crash if the user signed up without a display name."""
    captured: dict[str, EmailMessage] = {}

    async def fake_send(msg: EmailMessage) -> None:
        captured["msg"] = msg

    with (
        patch("app.services.email_service.settings") as s,
        patch("app.services.email_service._send", side_effect=fake_send),
    ):
        s.FRONTEND_BASE_URL = "https://moodsync.example.com"
        s.SMTP_FROM = "noreply@example.com"
        s.EMAIL_VERIFICATION_TTL_HOURS = 24

        await send_verification_email(
            to_email="bob@example.com",
            display_name=None,
            token="xyz",
        )

    assert captured["msg"]["To"] == "bob@example.com"


# ---------------------------------------------------------------------------
# send_already_registered_email — Issue #65 enumeration-safe register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_already_registered_email_renders_and_dispatches() -> None:
    captured: dict[str, EmailMessage] = {}

    async def fake_send(msg: EmailMessage) -> None:
        captured["msg"] = msg

    with (
        patch("app.services.email_service.settings") as s,
        patch("app.services.email_service._send", side_effect=fake_send),
    ):
        s.FRONTEND_BASE_URL = "https://moodsync.example.com"
        s.SMTP_FROM = "noreply@example.com"

        await send_already_registered_email(
            to_email="existing@example.com",
            display_name="Carol",
        )

    msg = captured["msg"]
    assert msg["From"] == "noreply@example.com"
    assert msg["To"] == "existing@example.com"
    assert "bereits registriert" in msg["Subject"].lower()
    payloads = [p.get_payload() for p in msg.walk() if not p.is_multipart()]
    body_text = "\n".join(str(p) for p in payloads)
    # Carries no token — only the login URL.
    assert "https://moodsync.example.com/auth/login" in body_text
    assert "token=" not in body_text

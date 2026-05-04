"""EmailService — async SMTP delivery for transactional mails.

Design (Issue #39):
- Async with aiosmtplib so the API request is not blocked by the SMTP
  handshake. In practice we still call this from a BackgroundTask so
  registration responds in <100ms even if the relay is slow.
- Templates are rendered with Jinja2 and shipped as both HTML and
  plaintext (multipart/alternative).
- Privacy by Design (DESIGN_DOCUMENT § 2.14):
    * No tracking pixels.
    * No external CSS/font/image references — everything is inline or
      omitted. (DSGVO-Checkpoint M0 § "keine externen Fonts/CDN".)
    * No content data (mood / symptoms / notes) is ever in any mail.
- Failure mode: if SMTP_HOST is empty (e.g. tests, dev without MailPit),
  the service logs the rendered mail at INFO and returns successfully
  instead of raising. Never raises in normal operation — registration
  must not fail because of a transient mail outage.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"

_jinja_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "html.j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _render(template: str, **context: object) -> str:
    return _jinja_env.get_template(template).render(**context)


def build_verify_url(token: str) -> str:
    """Build the verify URL the user clicks in the email.

    The frontend route owns this URL and POSTs to /api/v1/auth/verify-email
    with the token; this gives us a friendly UX page on success or error.
    """
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return f"{base}/auth/verify-email?token={token}"


def build_login_url() -> str:
    """Build the public login URL for transactional mails."""
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return f"{base}/auth/login"


async def _send(message: EmailMessage) -> None:
    """Send an EmailMessage. Swallows errors (logs them) so business flows
    are never broken by transient SMTP issues. Always log the recipient
    domain only — never full address — to keep logs DSGVO-clean."""
    if not settings.SMTP_HOST:
        # Dev / test fallback — emit at INFO so it's visible in logs but
        # never blocks registration.
        logger.info(
            "SMTP_HOST not configured — email not sent",
            extra={"to_domain": message["To"].split("@")[-1] if message["To"] else "?"},
        )
        return

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_USE_TLS,
            timeout=settings.SMTP_TIMEOUT,
        )
        logger.info(
            "verification email sent",
            extra={"to_domain": message["To"].split("@")[-1] if message["To"] else "?"},
        )
    except (aiosmtplib.SMTPException, OSError, TimeoutError) as exc:
        # Do NOT raise — let the user retry via /resend-verification.
        logger.error(
            "smtp send failed",
            extra={
                "error_type": type(exc).__name__,
                "to_domain": message["To"].split("@")[-1] if message["To"] else "?",
            },
        )


async def send_verification_email(
    *,
    to_email: str,
    display_name: str | None,
    token: str,
) -> None:
    """Compose and send the email verification mail."""
    verify_url = build_verify_url(token)
    ctx = {
        "display_name": display_name,
        "verify_url": verify_url,
        "ttl_hours": settings.EMAIL_VERIFICATION_TTL_HOURS,
    }

    text_body = _render("verify_email.txt.j2", **ctx)
    html_body = _render("verify_email.html.j2", **ctx)

    msg = EmailMessage()
    msg["Subject"] = "MoodSync — Bitte bestätige deine E-Mail-Adresse"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    await _send(msg)


async def send_already_registered_email(
    *,
    to_email: str,
    display_name: str | None,
) -> None:
    """Notify a user that someone tried to register with their address.

    Sent from the enumeration-safe ``POST /auth/register`` branch when
    the email already exists (Issue #65). Carries no token; the user is
    pointed to the login URL. Subject and body are intentionally written
    so they read sensibly whether the recipient initiated the attempt or
    not.
    """
    ctx = {
        "display_name": display_name,
        "login_url": build_login_url(),
    }

    text_body = _render("already_registered.txt.j2", **ctx)
    html_body = _render("already_registered.html.j2", **ctx)

    msg = EmailMessage()
    msg["Subject"] = "MoodSync — Diese Adresse ist bereits registriert"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    await _send(msg)

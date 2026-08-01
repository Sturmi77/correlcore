"""Optional GlitchTip / Sentry error tracking (M9 Sprint 2).

Selfhosted GlitchTip speaks the Sentry ingest protocol. When ``GLITCHTIP_DSN`` is
unset, nothing is initialised and no outbound error-reporting traffic occurs.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

# Field names that must never leave the instance (Art. 9 / secrets).
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "hashed_password",
        "current_password",
        "new_password",
        "note",
        "note_enc",
        "mood_score",
        "energy",
        "stress",
        # ADR-0033 Art. 9 cycle SHD — must match sanitise_entry_for_log allowlist.
        "cycle_day",
        "cycle_bleeding_level",
        "symptoms",
        "symptom_intensity",
        "intensity",
        "email",
        "display_name",
        "authorization",
        "cookie",
        "access_token",
        "refresh_token",
        "token",
        "name_enc",
        "wrapped_dek",
        "encryption_key",
        "secret_key",
    }
)

_REDACTED = "[Filtered]"


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in _SENSITIVE_KEYS or any(
        fragment in normalized for fragment in ("password", "token", "note", "email")
    )


def _scrub_string(value: str) -> str:
    if _EMAIL_RE.search(value):
        return _EMAIL_RE.sub(_REDACTED, value)
    return value


def _scrub_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, dict):
        return scrub_mapping(value)
    if isinstance(value, list):
        return [_scrub_value(key, item) for item in value]
    if isinstance(value, str):
        return _scrub_string(value)
    return value


def scrub_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive keys in a mapping."""
    scrubbed: dict[str, Any] = {}
    for key, value in data.items():
        scrubbed[key] = _scrub_value(key, value)
    return scrubbed


def scrub_sentry_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """``before_send`` hook — strip health data and credentials from Sentry events."""
    _ = hint

    request = event.get("request")
    if isinstance(request, dict):
        if isinstance(request.get("data"), dict):
            request["data"] = scrub_mapping(request["data"])
        if isinstance(request.get("cookies"), dict):
            request["cookies"] = dict.fromkeys(request["cookies"], _REDACTED)
        if isinstance(request.get("headers"), dict):
            request["headers"] = scrub_mapping(request["headers"])

    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = {
            key: (_REDACTED if key in {"email", "username", "ip_address"} else value)
            for key, value in user.items()
        }

    extra = event.get("extra")
    if isinstance(extra, dict):
        event["extra"] = scrub_mapping(extra)

    contexts = event.get("contexts")
    if isinstance(contexts, dict):
        event["contexts"] = scrub_mapping(contexts)

    breadcrumbs = event.get("breadcrumbs")
    if isinstance(breadcrumbs, dict):
        values = breadcrumbs.get("values")
        if isinstance(values, list):
            for crumb in values:
                if isinstance(crumb, dict) and isinstance(crumb.get("data"), dict):
                    crumb["data"] = scrub_mapping(crumb["data"])
                if isinstance(crumb, dict) and isinstance(crumb.get("message"), str):
                    crumb["message"] = _scrub_string(crumb["message"])

    if isinstance(event.get("message"), str):
        event["message"] = _scrub_string(event["message"])

    return event


def _before_send(event: Any, hint: dict[str, Any]) -> Any:
    """Adapter for sentry_sdk ``before_send`` — scrub in place, preserve Event type."""
    if isinstance(event, dict):
        scrub_sentry_event(event, hint)
    return event


def init_error_tracking(settings: Settings) -> bool:
    """Initialise Sentry/GlitchTip when ``GLITCHTIP_DSN`` is configured."""
    dsn = settings.GLITCHTIP_DSN.strip()
    if not dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    environment = settings.GLITCHTIP_ENVIRONMENT.strip() or settings.APP_ENV

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=settings.APP_VERSION,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        before_send=_before_send,
        send_default_pii=False,
        traces_sample_rate=settings.GLITCHTIP_TRACES_SAMPLE_RATE,
    )
    logger.info("error tracking enabled (environment=%s)", environment)
    return True

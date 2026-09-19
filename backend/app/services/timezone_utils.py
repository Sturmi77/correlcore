"""Timezone helpers shared by widgets and entry write-time covariates (#892)."""

from __future__ import annotations

import logging
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

UTC_ZONE = ZoneInfo("UTC")

# `tz` arrives from a client query parameter, so it must never reach the log
# verbatim (CodeQL py/log-injection). IANA names only use these characters.
_UNSAFE_TZ_CHARS = re.compile(r"[^A-Za-z0-9_+\-/]")


def _log_safe_tz(tz: str) -> str:
    return _UNSAFE_TZ_CHARS.sub("?", tz)[:64]


def resolve_zone(tz: str | None) -> ZoneInfo:
    """Resolve an IANA timezone name, falling back to UTC.

    Unknown or empty names degrade to UTC so a device TZ quirk never breaks
    entry create or widget summaries.
    """

    if not tz:
        return UTC_ZONE
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        logger.info("timezone.unknown", extra={"timezone": _log_safe_tz(tz)})
        return UTC_ZONE

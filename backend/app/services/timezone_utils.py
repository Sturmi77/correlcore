"""Timezone helpers shared by widgets and entry write-time covariates (#892)."""

from __future__ import annotations

import logging
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

UTC_ZONE = ZoneInfo("UTC")

# `tz` arrives from a client query parameter, so it must never reach the log
# verbatim (CodeQL py/log-injection). Substituting the unsafe characters away is
# not enough: `re.sub` is not modelled as a sanitizer, so the alert survived the
# rewrite. Match the whole string against the IANA shape instead and log a
# constant when it does not fit — the logged value is then either a literal or
# one proven to hold nothing but these characters.
_IANA_TZ_NAME = re.compile(r"[A-Za-z0-9_+\-]+(?:/[A-Za-z0-9_+\-]+){0,2}")
_TZ_REJECTED = "<invalid>"
_MAX_LOGGED_TZ_LEN = 64


def _log_safe_tz(tz: str) -> str:
    """Return `tz` only when it is shaped like an IANA name, else a constant."""

    if len(tz) > _MAX_LOGGED_TZ_LEN or _IANA_TZ_NAME.fullmatch(tz) is None:
        return _TZ_REJECTED
    return tz


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

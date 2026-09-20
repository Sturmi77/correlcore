"""Timezone helpers shared by widgets and entry write-time covariates (#892)."""

from __future__ import annotations

import logging
import string
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

UTC_ZONE = ZoneInfo("UTC")

# `tz` arrives from a client query parameter, so it must never reach the log
# verbatim (CodeQL py/log-injection). Two earlier attempts were not enough:
# `re.sub` over the unsafe characters is not modelled as a sanitizer, and a
# `fullmatch` against the IANA shape traded that alert for a polynomial-regex
# one (py/polynomial-redos) because the segment class itself contains `+`.
#
# So: no regex at all. A whitelist membership test over at most three slash
# separated segments is linear in the input, cannot backtrack, and is a plain
# guard that returns a constant on failure.
_TZ_SEGMENT_CHARS = frozenset(string.ascii_letters + string.digits + "_+-")
_TZ_SEGMENT_INITIALS = frozenset(string.ascii_letters)
_TZ_MAX_SEGMENTS = 3
_TZ_REJECTED = "<invalid>"
_MAX_LOGGED_TZ_LEN = 64


def _log_safe_tz(tz: str) -> str:
    """Return `tz` only when it is shaped like an IANA name, else a constant."""

    if len(tz) > _MAX_LOGGED_TZ_LEN:
        return _TZ_REJECTED
    segments = tz.split("/")
    if len(segments) > _TZ_MAX_SEGMENTS:
        return _TZ_REJECTED
    for segment in segments:
        # Every real IANA segment starts with a letter ("Europe", "Etc",
        # "GMT+5"). Requiring that keeps punctuation-only noise like "+++++"
        # out of the log even though `+` is legal inside a segment.
        if not segment or segment[0] not in _TZ_SEGMENT_INITIALS:
            return _TZ_REJECTED
        if not _TZ_SEGMENT_CHARS.issuperset(segment):
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

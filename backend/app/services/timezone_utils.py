"""Timezone helpers shared by widgets and entry write-time covariates (#892)."""

from __future__ import annotations

import errno
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

# `zoneinfo` normally converts a missing tzfile into ZoneInfoNotFoundError.
# Windows can surface malformed or overlong client input as an OSError first.
# Only errors that describe an invalid/missing path are input failures; access
# and general filesystem errors must remain visible to operators.
_INVALID_ZONE_ERRNOS = frozenset(
    value
    for value in (
        errno.EINVAL,
        errno.ENOENT,
        getattr(errno, "ENAMETOOLONG", None),
    )
    if value is not None
)
_INVALID_ZONE_WINERRORS = frozenset(
    {
        2,  # ERROR_FILE_NOT_FOUND
        3,  # ERROR_PATH_NOT_FOUND
        123,  # ERROR_INVALID_NAME
        206,  # ERROR_FILENAME_EXCED_RANGE
    }
)


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


def _is_expected_invalid_zone_error(exc: OSError) -> bool:
    """Return whether an OS error represents invalid client zone input."""

    winerror = getattr(exc, "winerror", None)
    return exc.errno in _INVALID_ZONE_ERRNOS or winerror in _INVALID_ZONE_WINERRORS


def _invalid_zone(tz: str) -> ZoneInfo:
    logger.info("timezone.unknown", extra={"timezone": _log_safe_tz(tz)})
    return UTC_ZONE


def resolve_zone(tz: str | None) -> ZoneInfo:
    """Resolve an IANA timezone name, falling back to UTC.

    Unknown or empty names degrade to UTC so a device TZ quirk never breaks
    entry create or widget summaries.
    """

    if not tz:
        return UTC_ZONE
    # Reject path-like, control-character and oversized input before it reaches
    # platform path handling. `_log_safe_tz` uses the same bounded whitelist.
    if _log_safe_tz(tz) == _TZ_REJECTED:
        return _invalid_zone(tz)
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        return _invalid_zone(tz)
    except OSError as exc:
        if not _is_expected_invalid_zone_error(exc):
            raise
        return _invalid_zone(tz)

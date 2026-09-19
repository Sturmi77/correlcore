"""Timezone helpers shared by widgets and entry write-time covariates (#892)."""

from __future__ import annotations

import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

UTC_ZONE = ZoneInfo("UTC")


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
        logger.info("timezone.unknown", extra={"timezone": tz})
        return UTC_ZONE

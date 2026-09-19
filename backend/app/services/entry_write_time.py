"""Derive logged_local_hour / inferred_period from first local write (#892 Option 3).

ADR-0016: write time is a covariate of ``entry_date``, never a time index.
``entries.slot`` stays ``day`` — these fields must not be written into ``slot``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.entry import InferredPeriod
from app.services.timezone_utils import resolve_zone


def inferred_period_for_hour(hour: int) -> InferredPeriod:
    if 5 <= hour <= 11:
        return InferredPeriod.MORNING
    if 12 <= hour <= 16:
        return InferredPeriod.DAYTIME
    if 17 <= hour <= 21:
        return InferredPeriod.EVENING
    return InferredPeriod.AFTER_HOURS


def derive_write_time_covariates(
    *,
    written_at: datetime | None = None,
    client_timezone: str | None = None,
) -> tuple[int, InferredPeriod]:
    """Return ``(logged_local_hour, inferred_period)`` for the first local write."""

    ts = written_at or datetime.now(UTC)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    local = ts.astimezone(resolve_zone(client_timezone))
    hour = local.hour
    return hour, inferred_period_for_hour(hour)

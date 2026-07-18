"""Pydantic schemas for the Android homescreen widget (M11 Sprint 4)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WidgetSummaryResponse(BaseModel):
    """Compact payload for Glance / WorkManager polling (≤1 KB)."""

    has_entry: bool
    mood_avg_7d: float | None = None
    suggested_next_entry_at: datetime | None = Field(
        default=None,
        description=(
            "Next suggested check-in instant (UTC), derived from the user's "
            "historical entry creation hours / slots."
        ),
    )

"""Pydantic schemas for user preferences and M3 onboarding state."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Documented allowed keys — validated in ``normalize_home_sections`` before persist.
HomeSectionKey = Literal[
    "first_week_banner",
    "daily_brief",
    "work_context",
    "weekday_overview",
    "trends_summary",
]

# Documented allowed keys — validated in ``normalize_insight_sections`` (#821).
InsightSectionKey = Literal[
    "stage_header",
    "correlation_matrix",
    "insight_feed",
    "lag_heatmap",
    "dismissed",
    "symptom_analytics",
    "tag_groups",
    "tag_cooccurrence",
]

TrendWindowDays = Literal[14, 28, 90]
TREND_WINDOW_DAYS_VALUES: tuple[int, ...] = (14, 28, 90)
TREND_WINDOW_DAYS_DEFAULT: TrendWindowDays = 28


class HomeSectionPreference(BaseModel):
    """One configurable Home screen block."""

    key: str
    enabled: bool


class InsightSectionPreference(BaseModel):
    """One configurable Insights page block."""

    key: str
    enabled: bool


class UserPreferencesUpdate(BaseModel):
    """Patch payload for future user preference endpoints."""

    analytics_enabled: bool | None = None
    digest_enabled: bool | None = None
    onboarding_retro_completed: bool | None = None
    onboarding_profile_completed: bool | None = None
    onboarding_maturity_intro_seen: bool | None = None
    cycle_tracking_enabled: bool | None = None
    belastung_overlay_enabled: bool | None = None
    home_weekday_day_trend_enabled: bool | None = None
    trend_window_days: TrendWindowDays | None = None
    health_connect_sync_sleep_enabled: bool | None = None
    dismissed_insight_keys: list[str] | None = Field(default=None, max_length=128)
    reached_milestone_keys: list[str] | None = Field(default=None, max_length=128)
    last_seen_insight_at: datetime | None = None
    last_seen_digest_at: datetime | None = None
    home_sections: list[HomeSectionPreference] | None = Field(default=None, max_length=16)
    insight_sections: list[InsightSectionPreference] | None = Field(default=None, max_length=16)
    # Upper bound is generous on purpose — a newer client may legitimately send a
    # version this server does not know yet. The service clamps it to the version
    # it can actually honour (#957); accepting it here and silently pinning the
    # row beyond CURRENT is what disabled future migrations.
    insight_sections_version: int | None = Field(default=None, ge=1, le=32)

    @field_validator("trend_window_days")
    @classmethod
    def _validate_trend_window_days(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value not in TREND_WINDOW_DAYS_VALUES:
            raise ValueError("trend_window_days must be one of 14, 28, 90")
        return value


class UserPreferencesResponse(BaseModel):
    """Stored user preferences."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    analytics_enabled: bool
    digest_enabled: bool = False
    onboarding_retro_completed: bool
    onboarding_profile_completed: bool
    onboarding_maturity_intro_seen: bool = False
    cycle_tracking_enabled: bool = True
    belastung_overlay_enabled: bool = False
    home_weekday_day_trend_enabled: bool = True
    trend_window_days: TrendWindowDays = TREND_WINDOW_DAYS_DEFAULT
    health_connect_sync_sleep_enabled: bool = True
    dismissed_insight_keys: list[str] = Field(default_factory=list)
    reached_milestone_keys: list[str] = Field(default_factory=list)
    last_seen_insight_at: datetime | None = None
    last_seen_digest_at: datetime | None = None
    home_sections: list[HomeSectionPreference] | None = None
    insight_sections: list[InsightSectionPreference] | None = None
    insight_sections_version: int = 2
    created_at: datetime
    updated_at: datetime

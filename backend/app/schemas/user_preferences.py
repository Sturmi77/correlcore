"""Pydantic schemas for user preferences and M3 onboarding state."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Documented allowed keys — validated in ``normalize_home_sections`` before persist.
HomeSectionKey = Literal[
    "first_week_banner",
    "daily_brief",
    "work_context",
    "weekday_overview",
]

# Documented allowed keys — validated in ``normalize_insight_sections`` (#821).
InsightSectionKey = Literal[
    "correlation_matrix",
    "insight_feed",
    "lag_heatmap",
    "dismissed",
    "symptom_analytics",
    "tag_groups",
    "tag_cooccurrence",
]


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
    health_connect_sync_sleep_enabled: bool | None = None
    dismissed_insight_keys: list[str] | None = Field(default=None, max_length=128)
    reached_milestone_keys: list[str] | None = Field(default=None, max_length=128)
    last_seen_insight_at: datetime | None = None
    last_seen_digest_at: datetime | None = None
    home_sections: list[HomeSectionPreference] | None = Field(default=None, max_length=16)
    insight_sections: list[InsightSectionPreference] | None = Field(default=None, max_length=16)


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
    health_connect_sync_sleep_enabled: bool = True
    dismissed_insight_keys: list[str] = Field(default_factory=list)
    reached_milestone_keys: list[str] = Field(default_factory=list)
    last_seen_insight_at: datetime | None = None
    last_seen_digest_at: datetime | None = None
    home_sections: list[HomeSectionPreference] | None = None
    insight_sections: list[InsightSectionPreference] | None = None
    created_at: datetime
    updated_at: datetime

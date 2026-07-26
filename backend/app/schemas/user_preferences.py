"""Pydantic schemas for user preferences and M3 onboarding state."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserPreferencesUpdate(BaseModel):
    """Patch payload for future user preference endpoints."""

    analytics_enabled: bool | None = None
    digest_enabled: bool | None = None
    onboarding_retro_completed: bool | None = None
    onboarding_profile_completed: bool | None = None
    onboarding_maturity_intro_seen: bool | None = None
    cycle_tracking_enabled: bool | None = None
    dismissed_insight_keys: list[str] | None = Field(default=None, max_length=128)
    reached_milestone_keys: list[str] | None = Field(default=None, max_length=128)
    last_seen_insight_at: datetime | None = None


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
    dismissed_insight_keys: list[str] = Field(default_factory=list)
    reached_milestone_keys: list[str] = Field(default_factory=list)
    last_seen_insight_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

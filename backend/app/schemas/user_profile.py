"""Schemas for optional onboarding profile data."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user_profile import (
    InsightCuriosity,
    SleepHoursTypical,
    SportFrequency,
    WorkContextTypical,
)


class UserProfileUpsert(BaseModel):
    sleep_hours_typical: SleepHoursTypical | None = None
    work_context_typical: WorkContextTypical | None = None
    sport_frequency: SportFrequency | None = None
    insight_curiosity: InsightCuriosity | None = None


class UserProfileResponse(UserProfileUpsert):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

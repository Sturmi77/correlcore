"""Pydantic schemas for M5 habit statistics."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.tag import HabitType

HabitWindow = Literal[7, 14, 28, 90]


class HabitStatsResponse(BaseModel):
    tag_id: uuid.UUID
    habit_type: HabitType
    target_frequency: int
    window: HabitWindow
    start_date: date_type
    end_date: date_type
    days_tracked: int = Field(ge=0)
    days_total: int = Field(ge=0)
    target_days: int = Field(ge=0)
    adherence_rate: float = Field(ge=0, le=100)
    correlation_score: float | None = None
    correlation_metric: str | None = None


class HabitListResponse(BaseModel):
    habits: list[HabitStatsResponse] = Field(default_factory=list)

"""Pydantic schemas for M2 visualization statistics."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field

from app.models.tag import TagCategory

TimeseriesRange = Literal["week", "month", "quarter", "year"]


class TimeseriesPoint(BaseModel):
    period_start: date_type
    period_end: date_type
    entry_count: int
    mood_avg: float | None = None
    energy_avg: float | None = None
    stress_avg: float | None = None


class TimeseriesResponse(BaseModel):
    range: TimeseriesRange
    points: list[TimeseriesPoint]


class TagHeatmapDay(BaseModel):
    date: date_type
    count: int


class TagHeatmapTag(BaseModel):
    tag_id: uuid.UUID
    slug: str
    name: str
    category: TagCategory
    color: str | None = None
    days: list[TagHeatmapDay] = Field(default_factory=list)


class TagHeatmapResponse(BaseModel):
    start_date: date_type
    end_date: date_type
    tags: list[TagHeatmapTag] = Field(default_factory=list)


class SymptomHeatmapDay(BaseModel):
    date: date_type
    count: int
    max_intensity: int


class SymptomHeatmapSymptom(BaseModel):
    symptom_id: uuid.UUID
    slug: str
    name: str
    icon: str | None = None
    days: list[SymptomHeatmapDay] = Field(default_factory=list)


class SymptomHeatmapResponse(BaseModel):
    start_date: date_type
    end_date: date_type
    symptoms: list[SymptomHeatmapSymptom] = Field(default_factory=list)


class EntryStreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_entry_days: int
    last_entry_date: date_type | None = None
    as_of: date_type

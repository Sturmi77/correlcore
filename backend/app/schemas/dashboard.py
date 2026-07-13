"""Pydantic schemas for dashboard summary data."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.entry import WorkContext
from app.models.insight import InsightTier


class WorkContextSummaryItem(BaseModel):
    work_context: WorkContext
    entry_count: int = Field(ge=0)
    mood_avg: float | None = None
    energy_avg: float | None = None
    stress_avg: float | None = None


class WeekdaySummaryItem(BaseModel):
    """Per-weekday descriptive mood stats (Monday=0 … Sunday=6, Python convention)."""

    weekday: int = Field(ge=0, le=6)
    entry_count: int = Field(ge=0)
    mood_avg: float | None = None


class DashboardSummaryResponse(BaseModel):
    entry_count: int = Field(ge=0)
    insight_tier: InsightTier
    confidence_score: float = Field(ge=0.0, le=1.0)
    work_context_summary: list[WorkContextSummaryItem] = Field(default_factory=list)
    weekday_summary: list[WeekdaySummaryItem] = Field(default_factory=list)

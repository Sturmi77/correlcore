"""Pydantic schemas for dashboard summary data."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.models.entry import WorkContext
from app.models.insight import InsightTier


class WorkContextSummaryItem(BaseModel):
    work_context: WorkContext
    entry_count: int = Field(ge=0)
    mood_avg: float | None = None
    energy_avg: float | None = None
    stress_avg: float | None = None


class WeekdayTopSignal(BaseModel):
    """The signal that occurs most often on a given weekday (#487).

    Descriptive only — this says "X usually happens on Mondays", not that X
    causes anything. Suppressed below :data:`MIN_TOP_SIGNAL_COUNT` /
    :data:`MIN_TOP_SIGNAL_SHARE` so a single stray entry cannot become a
    "typical" day.
    """

    kind: Literal["tag", "symptom", "work_context"]
    id: uuid.UUID | None = None
    label: str
    count: int = Field(ge=0)
    share: float = Field(ge=0.0, le=1.0)


class WeekdaySummaryItem(BaseModel):
    """Per-weekday descriptive mood stats (Monday=0 … Sunday=6, Python convention)."""

    weekday: int = Field(ge=0, le=6)
    entry_count: int = Field(ge=0)
    mood_avg: float | None = None
    top_signal: WeekdayTopSignal | None = None


class DashboardSummaryResponse(BaseModel):
    entry_count: int = Field(ge=0)
    insight_tier: InsightTier
    confidence_score: float = Field(ge=0.0, le=1.0)
    work_context_summary: list[WorkContextSummaryItem] = Field(default_factory=list)
    weekday_summary: list[WeekdaySummaryItem] = Field(default_factory=list)

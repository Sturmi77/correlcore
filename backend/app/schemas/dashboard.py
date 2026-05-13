"""Pydantic schemas for dashboard summary data."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.insight import InsightTier


class DashboardSummaryResponse(BaseModel):
    entry_count: int = Field(ge=0)
    insight_tier: InsightTier
    confidence_score: float = Field(ge=0.0, le=1.0)

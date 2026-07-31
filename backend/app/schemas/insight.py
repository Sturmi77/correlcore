"""Pydantic schemas for the M3 insight foundation."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.insight import InsightTier, InsightType
from app.schemas.stats import TagCooccurrenceRange, TimeseriesPoint


class InsightMaturityPhase(StrEnum):
    COLLECTING = "collecting"
    EARLY_PATTERNS = "early_patterns"
    PROVISIONAL = "provisional"
    ROBUST = "robust"


class InsightMaturity(BaseModel):
    """Shared API contract for the user's current insight journey phase."""

    phase: InsightMaturityPhase
    phase_index: int = Field(ge=1, le=4)
    current_entries: int = Field(ge=0)
    next_phase_at: int | None = Field(default=None, ge=1)
    next_phase_label: str | None = None
    entries_until_next: int | None = Field(default=None, ge=0)
    user_message_key: str


class InsightResponse(BaseModel):
    """Public shape for a persisted insight.

    The database stores ``statement_enc`` as ciphertext. The API field remains
    ``statement`` once the authenticated request has decrypted the ORM value.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    insight_type: InsightType
    tier: InsightTier
    metric: str
    subject_type: str | None = None
    subject_id: uuid.UUID | None = None
    subject_label: str | None = None
    effect_size: float | None = None
    confidence: float | None = None
    sample_n: int
    statement: str | None = Field(default=None, validation_alias="statement_enc")
    flags: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    generated_for_date: date_type
    generated_at: datetime
    created_at: datetime
    updated_at: datetime


class InsightListResponse(BaseModel):
    """Envelope for future insight list endpoints."""

    insight_maturity: InsightMaturity
    insights: list[InsightResponse] = Field(default_factory=list)


class InsightEventWindow(BaseModel):
    """Single tag/symptom occurrence aligned at t = 0 (ADR-0035 §6)."""

    onset: date_type
    label: str | None = None


class InsightEventWindowsResponse(BaseModel):
    """Event onsets plus timeseries points for Explore-Events small multiples."""

    range: TagCooccurrenceRange
    start_date: date_type
    end_date: date_type
    events: list[InsightEventWindow] = Field(default_factory=list)
    points: list[TimeseriesPoint] = Field(default_factory=list)
    # #488: for lag insights the onsets are the *feature* occurrences and the
    # outcome is expected at t = +lag_days; None for non-lag (co-occurrence) windows.
    lag_days: int | None = None


class InsightRegenerateResponse(BaseModel):
    """Outcome of an on-demand insight + tag-cluster regeneration run."""

    status: Literal["ok"] = "ok"
    generated_for_date: date_type
    insight_count: int = Field(ge=0)
    tag_clusters_status: Literal["ok", "insufficient_data"]
    trigger_source: str


class InsightTriggerResponse(BaseModel):
    """Aggregated outcome when an admin manually runs the insight worker."""

    status: Literal["ok"] = "ok"
    eligible_users: int = Field(ge=0)
    processed_users: int = Field(ge=0)
    failed_users: int = Field(ge=0)
    generated_insights: int = Field(ge=0)


class InsightDigestItemResponse(BaseModel):
    """One insight row included in a weekly digest."""

    id: uuid.UUID
    insight_type: InsightType
    metric: str
    effect_size: float | None = None
    confidence: float | None = None
    statement: str | None = None


class InsightDigestResponse(BaseModel):
    """Weekly digest envelope for the authenticated user."""

    week_start: date_type
    week_end: date_type
    insight_count: int = Field(ge=0)
    insights: list[InsightDigestItemResponse] = Field(default_factory=list)
    push_title: str
    push_body: str

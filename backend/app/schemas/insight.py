"""Pydantic schemas for the M3 insight foundation."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.insight import InsightTier, InsightType


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

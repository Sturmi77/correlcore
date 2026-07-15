"""Pydantic schemas for user consent audit log (Issue #31)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsentRecordRequest(BaseModel):
    """Record a consent grant or revocation."""

    type: str = Field(min_length=1, max_length=64, description="Consent type, e.g. health_connect")
    version: str = Field(min_length=1, max_length=32)
    granted: bool


class ConsentRevokeRequest(BaseModel):
    """Revoke a previously granted consent."""

    type: str = Field(min_length=1, max_length=64)


class ConsentRecordResponse(BaseModel):
    """Single consent log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    consent_type: str
    consent_version: str
    granted: bool
    created_at: datetime


class ConsentStatusItem(BaseModel):
    """Latest known state for one consent type."""

    consent_type: str
    consent_version: str | None = None
    granted: bool
    updated_at: datetime | None = None


class ConsentListResponse(BaseModel):
    """Current consent states plus full audit history."""

    current: list[ConsentStatusItem]
    history: list[ConsentRecordResponse]

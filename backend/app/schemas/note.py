"""Pydantic schemas for note visibility, signals, and analysis summaries."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class NoteVisibility(StrEnum):
    FULL = "full"
    ANALYSIS_ONLY = "analysis_only"
    HIDDEN = "hidden"


class EntryNoteSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_id: uuid.UUID
    signal: str
    confidence: float = Field(ge=0, le=1)
    source_span: str | None = None
    extractor_v: str
    created_at: datetime


class InsightEvidenceMetadata(BaseModel):
    """Optional evidence block fields for note-derived insights."""

    marker: str | None = None
    signal: str | None = None
    sample_size: int | None = Field(default=None, ge=0)
    time_window: int | None = Field(default=None, ge=1)
    avg_delta: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    example_entry_ids: list[uuid.UUID] = Field(default_factory=list)

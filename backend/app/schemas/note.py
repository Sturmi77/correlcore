"""Pydantic schemas for note markers, visibility, and analysis summaries."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.entry_note import NoteMarkerSource


class NoteVisibility(StrEnum):
    FULL = "full"
    ANALYSIS_ONLY = "analysis_only"
    HIDDEN = "hidden"


PREDEFINED_NOTE_MARKERS: frozenset[str] = frozenset(
    {
        "work",
        "homeoffice",
        "social",
        "movement",
        "sleep_bad",
        "sleep_good",
        "stress",
        "conflict",
        "symptom",
        "travel",
        "achievement",
    }
)

MAX_CUSTOM_MARKER_LENGTH = 32


class EntryNoteMarkerCreate(BaseModel):
    marker: str = Field(min_length=1, max_length=64)
    source: NoteMarkerSource = NoteMarkerSource.USER


class EntryNoteMarkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_id: uuid.UUID
    marker: str
    source: NoteMarkerSource
    created_at: datetime


class EntryNoteSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_id: uuid.UUID
    signal: str
    confidence: float = Field(ge=0, le=1)
    source_span: str | None = None
    extractor_v: str
    created_at: datetime


class MarkerSummaryItem(BaseModel):
    marker: str
    count: int = Field(ge=0)
    avg_mood: float
    entries: list[uuid.UUID] = Field(default_factory=list)


class MarkerSummaryResponse(BaseModel):
    items: list[MarkerSummaryItem] = Field(default_factory=list)
    from_date: date_type = Field(alias="from")
    to_date: date_type = Field(alias="to")

    model_config = ConfigDict(populate_by_name=True)


class InsightEvidenceMetadata(BaseModel):
    """Optional evidence block fields for note-derived insights."""

    marker: str | None = None
    signal: str | None = None
    sample_size: int | None = Field(default=None, ge=0)
    time_window: int | None = Field(default=None, ge=1)
    avg_delta: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    example_entry_ids: list[uuid.UUID] = Field(default_factory=list)

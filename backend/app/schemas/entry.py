"""Pydantic schemas for entry endpoints (M1, Issue #7).

Privacy note
------------
Entry payloads carry the most sensitive data in the system (mood,
energy, stress, freeform note). These schemas are also imported by the
log-scrubber to detect leaked field names — the canonical sensitive-
field list lives in :mod:`app.core.logging`.

Validation
----------
- ``mood_score`` / ``energy`` / ``stress`` are 1..5 ints — same range
  the DB CHECK constraint enforces. Pydantic surfaces a friendly error
  before it ever reaches the DB.
- ``entry_date`` may not be in the future. Older than 7 days is
  rejected at the service layer (read-only window) so the schema can
  stay stateless.
- ``note`` (request-side) maps onto ``note_enc`` (storage). The wire
  field stays human-readable; the column name signals the at-rest
  encryption upgrade path (Issue #26 / ADR-0005).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.entry import BleedingLevel, EntrySlot, EntrySource, WorkContext
from app.schemas.note import EntryNoteMarkerResponse, EntryNoteSignalResponse
from app.schemas.note import NoteVisibility as NoteVisibilitySchema
from app.schemas.tag import TagResponse

# Maximum note length on the wire. Generous, but bounded so a malicious
# client can't dump arbitrary blobs into the DB. Aligns with the
# Markdown-note design guidance in DESIGN_DOCUMENT.md §2.6.
MAX_NOTE_LENGTH = 4000

# Read-only window for backdating an entry (DESIGN_DOCUMENT.md §2.1).
# Enforced in the service layer; documented here for schema readers.
BACKDATE_DAYS_LIMIT = 7

# Manual sleep tracking bounds (M8 Sprint 1, #172). sleep_minutes covers a full
# day (24h = 1440); sleep_quality shares the 1..5 scale family with mood/energy.
MAX_SLEEP_MINUTES = 1440

# Clients key ``entry_date`` by the device-local calendar day (Home
# ``localIsoDate``, entry sheet ``isoDate``, widget ``tz``). The API
# container runs in UTC with no TZ env, so a user east of UTC reaches
# their local "today" while ``datetime.now(UTC).date()`` is still
# yesterday. Without this slack, POST /entries and offline sync reject
# the primary "log today" action for hours each morning (UTC+1 … +14).
# One calendar day covers the maximum civil offset (UTC+14).
CLIENT_TZ_AHEAD_SLACK_DAYS = 1


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class EntryCreate(BaseModel):
    """Payload for ``POST /api/v1/entries``."""

    model_config = ConfigDict(populate_by_name=True)

    entry_date: date_type
    slot: EntrySlot = EntrySlot.DAY
    mood_score: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=5)
    cycle_day: int | None = Field(default=None, ge=1, le=35)
    cycle_bleeding_level: BleedingLevel | None = None
    sleep_minutes: int | None = Field(default=None, ge=0, le=MAX_SLEEP_MINUTES)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    source: EntrySource = EntrySource.DIRECT
    work_context: WorkContext
    note: str | None = Field(
        default=None, validation_alias=AliasChoices("note", "note_raw"), max_length=MAX_NOTE_LENGTH
    )
    note_summary_short: str | None = Field(default=None, max_length=120)
    note_visibility: NoteVisibilitySchema = NoteVisibilitySchema.FULL

    @field_validator("entry_date")
    @classmethod
    def date_not_in_future(cls, v: date_type) -> date_type:
        latest_allowed = datetime.now(UTC).date() + timedelta(days=CLIENT_TZ_AHEAD_SLACK_DAYS)
        if v > latest_allowed:
            raise ValueError("entry_date must not be in the future")
        return v

    @field_validator("note")
    @classmethod
    def note_not_only_whitespace(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            return None
        return v


class EntryUpdate(BaseModel):
    """Payload for ``PATCH /api/v1/entries/{id}``.

    All fields optional — only sent fields are updated.
    """

    model_config = ConfigDict(populate_by_name=True)

    mood_score: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    stress: int | None = Field(default=None, ge=1, le=5)
    slot: EntrySlot | None = None
    cycle_day: int | None = Field(default=None, ge=1, le=35)
    cycle_bleeding_level: BleedingLevel | None = None
    sleep_minutes: int | None = Field(default=None, ge=0, le=MAX_SLEEP_MINUTES)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    work_context: WorkContext | None = None
    note: str | None = Field(
        default=None, validation_alias=AliasChoices("note", "note_raw"), max_length=MAX_NOTE_LENGTH
    )
    note_summary_short: str | None = Field(default=None, max_length=120)
    note_visibility: NoteVisibilitySchema | None = None

    @field_validator("note")
    @classmethod
    def note_not_only_whitespace(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            return None
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class EntryResponse(BaseModel):
    """Single entry — returned by create / get / update / list."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    entry_date: date_type
    slot: EntrySlot
    mood_score: int
    energy: int
    stress: int
    cycle_day: int | None = None
    cycle_bleeding_level: BleedingLevel | None = None
    sleep_minutes: int | None = None
    sleep_quality: int | None = None
    source: EntrySource
    work_context: WorkContext
    note: str | None = Field(default=None, validation_alias="note_enc")
    note_raw: str | None = Field(default=None, validation_alias="note_enc")
    note_summary_short: str | None = None
    note_visibility: NoteVisibilitySchema = NoteVisibilitySchema.FULL
    note_updated_at: datetime | None = None
    note_markers: list[EntryNoteMarkerResponse] = Field(default_factory=list)
    note_signals: list[EntryNoteSignalResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def mirror_note_raw(self) -> EntryResponse:
        if self.note_raw is None:
            self.note_raw = self.note
        return self


class EntryBatchCreate(BaseModel):
    """Payload for onboarding retrospective entry import."""

    entries: list[EntryCreate] = Field(min_length=0, max_length=7)


class EntryMetrics(BaseModel):
    """Small metric-only entry shape for day-over-day comparisons."""

    model_config = ConfigDict(from_attributes=True)

    entry_date: date_type
    slot: EntrySlot
    mood_score: int
    energy: int
    stress: int


class EntryMetricDelta(BaseModel):
    """Difference between two entry metric sets."""

    mood: int | None = None
    energy: int | None = None
    stress: int | None = None


class EntryDeltaResponse(BaseModel):
    """Day-over-day comparison for one entry date and slot."""

    today: EntryMetrics | None = None
    previous: EntryMetrics | None = None
    delta: EntryMetricDelta = Field(default_factory=EntryMetricDelta)
    shared_tags: list[TagResponse] = Field(default_factory=list)

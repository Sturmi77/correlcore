"""Pydantic schemas for offline sync endpoints (M4.1, Issue #10).

Contract
--------
These models mirror :doc:`docs/adr/0036-offline-sync-v1-scope.md` and
``docs/API.md`` §10. Sprint 2 implements push/pull via
``backend/app/services/sync_service.py``.

Privacy
-------
Sync payloads may carry Art.-9 health data. Conflict reports for ``note``
fields use redacted markers only (no plaintext in ``SyncConflictReport``).
The log-scrubber test suite must cover sync field names once endpoints ship.
"""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.entry import BleedingLevel, EntrySlot, WorkContext

# ---------------------------------------------------------------------------
# Enums — wire-stable entity / table identifiers
# ---------------------------------------------------------------------------

SYNC_ENTITY_TYPES = ("entry", "tag", "symptom")
SyncEntityType = Literal["entry", "tag", "symptom"]

SYNC_TABLE_NAMES = ("entries", "tags", "symptoms")
SyncTableName = Literal["entries", "tags", "symptoms"]

SyncChangeOperation = Literal["upsert", "delete"]


class SyncConflictField(StrEnum):
    """Critical fields logged to ``sync_conflicts`` (ADR-0003 / #24)."""

    MOOD_SCORE = "mood_score"
    ENERGY = "energy"
    STRESS = "stress"
    NOTE = "note"
    SYMPTOMS = "symptoms"


# ---------------------------------------------------------------------------
# Push — client → server
# ---------------------------------------------------------------------------


class SyncEntryPayload(BaseModel):
    """Entry body inside a ``SyncChange`` when ``table == "entries"``."""

    entry_date: date_type
    slot: EntrySlot = EntrySlot.DAY
    mood_score: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=5)
    cycle_day: int | None = Field(default=None, ge=1, le=35)
    cycle_bleeding_level: BleedingLevel | None = None
    work_context: WorkContext
    note: str | None = None
    tag_ids: list[uuid.UUID] = Field(default_factory=list)
    symptoms: dict[str, int] = Field(
        default_factory=dict,
        description="Map symptom_id (UUID string) → intensity 0..3",
    )


class SyncTagPayload(BaseModel):
    """Custom tag body inside a ``SyncChange`` when ``table == "tags"``."""

    slug: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    category: str
    icon: str | None = Field(default=None, max_length=32)
    color: str | None = Field(default=None, max_length=7)
    habit_type: Literal["none", "build", "reduce"] = "none"
    target_frequency: int | None = Field(default=None, ge=1, le=7)


class SyncSymptomPayload(BaseModel):
    """Custom symptom body inside a ``SyncChange`` when ``table == "symptoms"``."""

    slug: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    icon: str | None = Field(default=None, max_length=8)


class SyncChange(BaseModel):
    """Single change in a push batch or pull delta."""

    seq: int = Field(ge=1, description="Monotone sequence per client_id")
    id: uuid.UUID = Field(description="Entity primary key (client-assigned for creates)")
    table: SyncTableName
    operation: SyncChangeOperation = "upsert"
    data: dict[str, Any] = Field(
        description="Entity payload; shape depends on ``table`` (see *Payload models)",
    )
    updated_at: datetime = Field(description="Client-side last-write timestamp (UTC)")


class SyncPushRequest(BaseModel):
    """``POST /api/v1/sync/push`` body."""

    client_id: uuid.UUID
    batch_id: uuid.UUID = Field(description="Idempotency key for this HTTP request")
    changes: list[SyncChange] = Field(min_length=1, max_length=500)


class SyncConflictReport(BaseModel):
    """Per-field merge conflict returned in push response (not HTTP 409)."""

    entity_id: uuid.UUID
    entity_type: SyncEntityType
    field_name: SyncConflictField | str
    client_ts: datetime
    server_ts: datetime
    winner: Literal["server"] = "server"
    # Redacted values only — never plaintext health data (ADR-0036 §2.1)
    client_value: dict[str, Any] | None = None
    server_value: dict[str, Any] | None = None


class SyncPushResponse(BaseModel):
    """``POST /api/v1/sync/push`` success body."""

    cursor: str = Field(description="Opaque pull cursor after applying batch")
    applied: int = Field(ge=0, description="Number of changes applied (excl. skipped)")
    skipped: int = Field(ge=0, description="Changes skipped (replay / stale seq)")
    conflicts: list[SyncConflictReport] = Field(default_factory=list)
    idempotent_replay: bool = Field(
        default=False,
        description="True when batch_id was already processed",
    )


# ---------------------------------------------------------------------------
# Pull — server → client
# ---------------------------------------------------------------------------


class SyncPullResponse(BaseModel):
    """``GET /api/v1/sync/pull`` success body."""

    cursor: str = Field(description="Opaque cursor; pass as ``since`` on next pull")
    changes: list[SyncChange]
    has_more: bool = False
    server_time: datetime


# ---------------------------------------------------------------------------
# Conflict history — read-only (Sprint 1)
# ---------------------------------------------------------------------------


class SyncConflictListItem(BaseModel):
    """Row from ``GET /api/v1/user/sync-conflicts`` — no plaintext health values."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_id: uuid.UUID
    entity_type: SyncEntityType
    field_name: str
    client_ts: datetime
    server_ts: datetime
    created_at: datetime
    resolved_at: datetime | None = None
    client_value: dict[str, Any] | None = None
    server_value: dict[str, Any] | None = None


class SyncConflictListResponse(BaseModel):
    """Paginated conflict history."""

    items: list[SyncConflictListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)

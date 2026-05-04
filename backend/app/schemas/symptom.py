"""Pydantic schemas for symptom endpoints (M1, Issue #9).

Symptoms are *health data* under DSGVO Art. 9. The service layer
(``symptom_service.py``) is responsible for keeping these payloads out
of logs; this module merely validates the wire format.

Schema design
-------------
- ``symptom_key`` is constrained to :data:`STANDARD_SYMPTOM_KEYS`. M1
  has no custom-symptom surface.
- ``intensity`` is an integer in 0..3. Validation lives both at the
  schema layer (Pydantic ``Field`` constraint) and at the DB layer
  (CHECK constraint). The frontend renders a 4-step visual scale and
  never sends a raw number outside this range.
- ``EntrySymptomAssignment`` is the request body for the replace-set
  endpoint. ``symptom_key`` is unique per request — the service layer
  also enforces uniqueness in the DB via the ``(entry_id, symptom_key)``
  unique constraint, but rejecting duplicates here gives a 422 instead
  of a 500/integrity error.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.symptom import INTENSITY_MAX, INTENSITY_MIN, STANDARD_SYMPTOM_KEYS

# Maximum number of symptoms a client may attach to a single entry in
# one request. The standard set has only five keys, so the cap is
# generous enough for future extensions while still bounding payloads.
MAX_SYMPTOMS_PER_ENTRY = 32


# ---------------------------------------------------------------------------
# Single-symptom payload
# ---------------------------------------------------------------------------


class SymptomEntry(BaseModel):
    """One ``(symptom_key, intensity)`` pair."""

    symptom_key: str = Field(min_length=1, max_length=64)
    intensity: int = Field(ge=INTENSITY_MIN, le=INTENSITY_MAX)

    @field_validator("symptom_key")
    @classmethod
    def known_key(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in STANDARD_SYMPTOM_KEYS:
            # Don't echo arbitrary input — surface only the allowed
            # set so the error message stays bounded.
            raise ValueError(
                f"symptom_key must be one of: {sorted(STANDARD_SYMPTOM_KEYS)}",
            )
        return v


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class EntrySymptomAssignment(BaseModel):
    """Payload for ``PUT /api/v1/entries/{entry_id}/symptoms``.

    Replace-set semantics: the supplied list overwrites the entry's
    full symptom set. An empty list clears all symptoms on the entry.
    """

    symptoms: list[SymptomEntry] = Field(
        default_factory=list,
        max_length=MAX_SYMPTOMS_PER_ENTRY,
    )

    @field_validator("symptoms")
    @classmethod
    def keys_unique(cls, v: list[SymptomEntry]) -> list[SymptomEntry]:
        keys = [s.symptom_key for s in v]
        if len(set(keys)) != len(keys):
            raise ValueError("symptom_key values must be unique within the request")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class SymptomResponse(BaseModel):
    """Persisted symptom row — returned by symptom endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_id: uuid.UUID
    user_id: uuid.UUID
    symptom_key: str
    intensity: int
    created_at: datetime
    updated_at: datetime


class StandardSymptomKey(BaseModel):
    """Single entry in the standard-symptom-key catalogue."""

    symptom_key: str
    # We deliberately do *not* ship a "default intensity" here. Clients
    # render a neutral state (no value) until the user picks one.


class StandardSymptomKeyList(BaseModel):
    """Response for ``GET /api/v1/symptoms/standard``."""

    keys: list[StandardSymptomKey]

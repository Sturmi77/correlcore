"""Pydantic schemas for symptom endpoints (Issue #57, ADR-0008).

Symptoms are *health data* under DSGVO Art. 9. The service layer
(``symptom_service.py``) is responsible for keeping these payloads out
of logs; this module merely validates the wire format.

Schema design
-------------
- ``Symptom`` is the master row (curated default or user-owned). Schemas
  mirror :mod:`app.schemas.tag` since the surfaces are intentionally
  symmetric (ADR-0008).
- ``slug`` follows the same canonical pattern as tag slugs: lowercase
  letters/digits/dashes/underscores, 2..64 chars, starting and ending
  with an alphanumeric. The validator normalises (strip+lower) so the
  DB only ever sees clean keys.
- The slug is **not** patchable: changing a slug breaks every historical
  ``entry_symptoms`` row that references the master row. Users who need
  a new slug create a new symptom and re-assign entries.
- ``intensity`` is an integer in 0..3. Validation lives both at the
  schema layer (Pydantic ``Field`` constraint) and at the DB layer
  (CHECK constraint). The frontend renders a 4-step visual scale and
  never sends a raw number outside this range.
- ``EntrySymptomAssignment`` carries ``(symptom_id, intensity)`` pairs.
  Clients call ``GET /symptoms`` first, then send the chosen IDs (no
  slugs at the wire layer — same rationale as tags).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.models.symptom import INTENSITY_MAX, INTENSITY_MIN

# Canonical slug pattern (mirrors :mod:`app.schemas.tag`).
_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?$")

# Maximum number of symptoms a client may attach to a single entry in
# one request. The standard set has only five keys, but custom symptoms
# can grow the practical set; the cap protects against runaway payloads.
MAX_SYMPTOMS_PER_ENTRY = 32


# ---------------------------------------------------------------------------
# Request schemas — Symptom CRUD
# ---------------------------------------------------------------------------


class SymptomCreate(BaseModel):
    """Payload for ``POST /api/v1/symptoms`` (custom symptom)."""

    slug: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    icon: str | None = Field(default=None, max_length=32)

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not _SLUG_PATTERN.match(v):
            raise ValueError(
                "slug must be 2..64 chars, lowercase letters/digits/dashes/underscores, "
                "starting and ending with a letter or digit"
            )
        return v

    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v


class SymptomUpdate(BaseModel):
    """Payload for ``PATCH /api/v1/symptoms/{id}`` — custom symptoms only.

    The slug is intentionally not patchable (same rationale as tags).
    """

    name: str | None = Field(default=None, min_length=1, max_length=64)
    icon: str | None = Field(default=None, max_length=32)

    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v


# ---------------------------------------------------------------------------
# Request schemas — Entry-symptom assignment
# ---------------------------------------------------------------------------


class SymptomEntry(BaseModel):
    """One ``(symptom_id, intensity)`` pair on the wire."""

    symptom_id: uuid.UUID
    intensity: int = Field(ge=INTENSITY_MIN, le=INTENSITY_MAX)


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
    def ids_unique(cls, v: list[SymptomEntry]) -> list[SymptomEntry]:
        ids = [s.symptom_id for s in v]
        if len(set(ids)) != len(ids):
            raise ValueError("symptom_id values must be unique within the request")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class SymptomResponse(BaseModel):
    """Single symptom master row — returned by symptom CRUD endpoints.

    For custom symptoms, ``name`` is decrypted on the fly from
    ``Symptom.display_name`` (which uses the request-scoped DEK). Default
    symptoms expose their plaintext ``name`` directly.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    slug: str
    # ``display_name`` resolves to plaintext for both default & custom rows.
    # Wire field stays ``name`` for backwards compatibility with the
    # existing API contract.
    name: str = Field(validation_alias=AliasChoices("display_name", "name"))
    icon: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class EntrySymptomResponse(BaseModel):
    """Persisted entry-symptom row — returned by entry-symptom endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_id: uuid.UUID
    user_id: uuid.UUID
    symptom_id: uuid.UUID
    intensity: int
    created_at: datetime
    updated_at: datetime

"""Pydantic schemas for tag endpoints (M1, Issue #8).

The tag system has two surfaces:

1. *Tag CRUD* — the user manages their own custom tags and reads the
   list of curated defaults.
2. *Entry-tag assignment* — attaching/detaching tags to a specific
   entry.

Schema design
-------------
- ``slug`` is the canonical key. It is normalised on input (lowercased,
  trimmed). The validator rejects empty strings and slugs that don't
  match the allowed character set so the DB only ever sees clean keys.
- ``color`` accepts the 7-char ``#rrggbb`` form. We permit ``None`` so
  the frontend can fall back to the category-default color.
- ``EntryTagAssignment`` carries a list of *tag IDs* — clients call
  ``GET /tags`` first, then send the chosen IDs. We deliberately do not
  let clients send slugs here so a typo can't accidentally create a tag
  on the fly.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.tag import TagCategory

# Canonical slug pattern. Lowercase letters, digits, dashes and
# underscores; 2..64 chars. Dashes/underscores must not start or end
# the slug and must not repeat.
_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?$")
_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

# Maximum number of tags a client may assign to one entry in a single
# request. Keeps payloads small and prevents accidental tag-spam.
MAX_TAGS_PER_ENTRY = 50

HabitType = Literal["none", "build", "reduce"]


# ---------------------------------------------------------------------------
# Request schemas — Tag CRUD
# ---------------------------------------------------------------------------


class TagCreate(BaseModel):
    """Payload for ``POST /api/v1/tags`` (custom tag)."""

    slug: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    category: TagCategory
    icon: str | None = Field(default=None, max_length=32)
    color: str | None = Field(default=None, max_length=7)
    include_in_analytics: bool = True
    habit_type: HabitType = "none"
    target_frequency: int | None = Field(default=None, ge=1, le=7)

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

    @field_validator("color")
    @classmethod
    def color_hex(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _HEX_COLOR_PATTERN.match(v):
            raise ValueError("color must be a 7-char hex string like #aabbcc")
        return v.lower()

    @model_validator(mode="after")
    def habit_fields_consistent(self) -> TagCreate:
        if self.habit_type == "none":
            self.target_frequency = None
        elif self.target_frequency is None:
            raise ValueError("target_frequency is required for habit tags")
        return self


class TagUpdate(BaseModel):
    """Payload for ``PATCH /api/v1/tags/{id}``.

    The slug is intentionally not patchable: changing a slug breaks
    every historical entry that references the tag. Users who want a
    new slug should create a new tag and re-tag their entries. Default
    tag updates create or update a user-owned copy-on-write override.
    """

    name: str | None = Field(default=None, min_length=1, max_length=64)
    category: TagCategory | None = None
    icon: str | None = Field(default=None, max_length=32)
    color: str | None = Field(default=None, max_length=7)
    is_hidden: bool | None = None
    include_in_analytics: bool | None = None
    habit_type: HabitType | None = None
    target_frequency: int | None = Field(default=None, ge=1, le=7)

    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v

    @field_validator("color")
    @classmethod
    def color_hex(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _HEX_COLOR_PATTERN.match(v):
            raise ValueError("color must be a 7-char hex string like #aabbcc")
        return v.lower()

    @model_validator(mode="after")
    def habit_fields_consistent(self) -> TagUpdate:
        fields_set = self.model_fields_set
        if self.habit_type == "none":
            self.target_frequency = None
        elif (
            self.habit_type in {"build", "reduce"}
            and "target_frequency" in fields_set
            and self.target_frequency is None
        ):
            raise ValueError("target_frequency is required for habit tags")
        return self


# ---------------------------------------------------------------------------
# Request schemas — Entry-tag assignment
# ---------------------------------------------------------------------------


class EntryTagAssignment(BaseModel):
    """Payload for ``PUT /api/v1/entries/{entry_id}/tags``.

    The list replaces the entry's current tag set wholesale. Clients
    that want to "add one" must send the full new list; this matches
    REST PUT semantics and keeps the wire format trivially idempotent.
    """

    tag_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_TAGS_PER_ENTRY)

    @field_validator("tag_ids")
    @classmethod
    def tag_ids_unique(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(v)) != len(v):
            raise ValueError("tag_ids must be unique")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TagResponse(BaseModel):
    """Single tag — returned by tag CRUD endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    slug: str
    name: str
    category: TagCategory
    icon: str | None
    color: str | None
    is_default: bool
    is_hidden: bool
    include_in_analytics: bool
    habit_type: HabitType
    target_frequency: int | None
    created_at: datetime
    updated_at: datetime

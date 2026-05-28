"""Schemas for M4 guided onboarding."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from app.models.tag import TagCategory
from app.schemas.tag import TagResponse

_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?$")
_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


class TagSuggestion(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    category: TagCategory
    icon: str | None = Field(default=None, max_length=32)
    color: str | None = Field(default=None, max_length=7)


class TagSuggestionGroup(BaseModel):
    category: TagCategory
    suggestions: list[TagSuggestion]


class TagSuggestionsResponse(BaseModel):
    groups: list[TagSuggestionGroup]


class OnboardingTagInput(BaseModel):
    slug: str | None = Field(default=None, min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    category: TagCategory = TagCategory.OTHER
    icon: str | None = Field(default=None, max_length=32)
    color: str | None = Field(default=None, max_length=7)

    @field_validator("slug")
    @classmethod
    def slug_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if not _SLUG_PATTERN.match(value):
            raise ValueError(
                "slug must be 2..64 chars, lowercase letters/digits/dashes/underscores, "
                "starting and ending with a letter or digit"
            )
        return value

    @field_validator("name")
    @classmethod
    def name_strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("color")
    @classmethod
    def color_hex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _HEX_COLOR_PATTERN.match(value):
            raise ValueError("color must be a 7-char hex string like #aabbcc")
        return value.lower()


class OnboardingCompleteRequest(BaseModel):
    tags: list[OnboardingTagInput] = Field(default_factory=list, max_length=50)


class OnboardingCompleteResponse(BaseModel):
    created_tags: list[TagResponse] = Field(default_factory=list)
    onboarding_retro_completed: bool
    onboarding_profile_completed: bool

"""Schemas for M4 guided onboarding."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.tag import TagCategory
from app.schemas.tag import TagResponse


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

    @field_validator("name")
    @classmethod
    def name_strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class OnboardingCompleteRequest(BaseModel):
    tags: list[OnboardingTagInput] = Field(default_factory=list, max_length=50)


class OnboardingCompleteResponse(BaseModel):
    created_tags: list[TagResponse] = Field(default_factory=list)
    onboarding_retro_completed: bool
    onboarding_profile_completed: bool

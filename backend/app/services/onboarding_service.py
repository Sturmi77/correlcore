"""Guided onboarding helpers for M4."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag, TagCategory
from app.models.user_preference import UserPreference
from app.schemas.onboarding import (
    OnboardingTagInput,
    TagSuggestion,
    TagSuggestionGroup,
    TagSuggestionsResponse,
)
from app.schemas.tag import TagCreate
from app.schemas.user_preferences import UserPreferencesUpdate
from app.services.tag_service import TagConflictError, create_custom_tag
from app.services.user_preferences_service import update_user_preferences


_SUGGESTIONS: tuple[TagSuggestionGroup, ...] = (
    TagSuggestionGroup(
        category=TagCategory.WORK,
        suggestions=[
            TagSuggestion(
                slug="deep-work",
                name="Deep work",
                category=TagCategory.WORK,
                icon="briefcase",
            ),
            TagSuggestion(
                slug="meetings",
                name="Meetings",
                category=TagCategory.WORK,
                icon="users",
            ),
            TagSuggestion(
                slug="deadline",
                name="Deadline",
                category=TagCategory.WORK,
                icon="clock",
            ),
        ],
    ),
    TagSuggestionGroup(
        category=TagCategory.HEALTH,
        suggestions=[
            TagSuggestion(
                slug="walk",
                name="Walk",
                category=TagCategory.HEALTH,
                icon="footprints",
            ),
            TagSuggestion(
                slug="medication",
                name="Medication",
                category=TagCategory.HEALTH,
                icon="pill",
            ),
            TagSuggestion(
                slug="therapy",
                name="Therapy",
                category=TagCategory.HEALTH,
                icon="heart",
            ),
        ],
    ),
    TagSuggestionGroup(
        category=TagCategory.SOCIAL,
        suggestions=[
            TagSuggestion(
                slug="family",
                name="Family",
                category=TagCategory.SOCIAL,
                icon="home",
            ),
            TagSuggestion(
                slug="friends",
                name="Friends",
                category=TagCategory.SOCIAL,
                icon="smile",
            ),
            TagSuggestion(
                slug="alone-time",
                name="Alone time",
                category=TagCategory.SOCIAL,
                icon="moon",
            ),
        ],
    ),
    TagSuggestionGroup(
        category=TagCategory.CYCLE,
        suggestions=[
            TagSuggestion(
                slug="cycle",
                name="Cycle",
                category=TagCategory.CYCLE,
                icon="rotate-cw",
            ),
            TagSuggestion(
                slug="period",
                name="Period",
                category=TagCategory.CYCLE,
                icon="droplet",
            ),
            TagSuggestion(
                slug="pms",
                name="PMS",
                category=TagCategory.CYCLE,
                icon="activity",
            ),
        ],
    ),
)


def tag_suggestions() -> TagSuggestionsResponse:
    return TagSuggestionsResponse(groups=list(_SUGGESTIONS))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:64] or "tag"


async def _find_visible_tag_by_slug(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    slug: str,
) -> Tag | None:
    result = await db.execute(
        select(Tag).where(
            Tag.slug == slug,
            ((Tag.user_id == user_id) & (Tag.is_default.is_(False))) | Tag.is_default.is_(True),
        )
    )
    return result.scalars().first()


async def complete_onboarding(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tags: list[OnboardingTagInput],
) -> tuple[UserPreference, list[Tag]]:
    created_or_existing: list[Tag] = []
    for item in tags:
        slug = item.slug or _slugify(item.name)
        existing = await _find_visible_tag_by_slug(db, user_id=user_id, slug=slug)
        if existing is not None:
            created_or_existing.append(existing)
            continue

        try:
            tag = await create_custom_tag(
                db,
                user_id=user_id,
                payload=TagCreate(
                    slug=slug,
                    name=item.name,
                    category=item.category,
                    icon=item.icon,
                    color=item.color,
                ),
            )
        except TagConflictError:
            existing = await _find_visible_tag_by_slug(db, user_id=user_id, slug=slug)
            if existing is None:
                raise
            tag = existing
        created_or_existing.append(tag)

    preferences = await update_user_preferences(
        db,
        user_id=user_id,
        payload=UserPreferencesUpdate(
            onboarding_retro_completed=True,
            onboarding_profile_completed=True,
        ),
    )
    return preferences, created_or_existing

"""Guided onboarding helpers for M4."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.tag_catalog import canonical_onboarding_slug, onboarding_suggestion_groups
from app.models.tag import Tag
from app.models.user_preference import UserPreference
from app.schemas.onboarding import (
    OnboardingTagInput,
    TagSuggestionsResponse,
)
from app.schemas.tag import TagCreate, TagUpdate
from app.schemas.user_preferences import UserPreferencesUpdate
from app.services.tag_service import TagConflictError, create_custom_tag, update_custom_tag
from app.services.user_preferences_service import update_user_preferences


def tag_suggestions() -> TagSuggestionsResponse:
    return TagSuggestionsResponse(groups=list(onboarding_suggestion_groups()))


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


async def _apply_onboarding_habit(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    existing: Tag,
    item: OnboardingTagInput,
) -> Tag:
    """Set the habit facet on an already-existing tag (copy-on-write for defaults).

    Reuses the same service the PATCH /tags/{id} endpoint uses. A ``none`` habit
    leaves the existing tag untouched.
    """
    if item.habit_type == "none":
        return existing
    return await update_custom_tag(
        db,
        user_id=user_id,
        tag_id=existing.id,
        payload=TagUpdate(
            habit_type=item.habit_type,
            target_frequency=item.target_frequency,
        ),
    )


async def complete_onboarding(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tags: list[OnboardingTagInput],
) -> tuple[UserPreference, list[Tag]]:
    created_or_existing: list[Tag] = []
    for item in tags:
        slug = canonical_onboarding_slug(item.slug or _slugify(item.name))
        existing = await _find_visible_tag_by_slug(db, user_id=user_id, slug=slug)
        if existing is not None:
            created_or_existing.append(
                await _apply_onboarding_habit(db, user_id=user_id, existing=existing, item=item)
            )
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
                    habit_type=item.habit_type,
                    target_frequency=item.target_frequency,
                ),
            )
        except TagConflictError:
            existing = await _find_visible_tag_by_slug(db, user_id=user_id, slug=slug)
            if existing is None:
                raise
            tag = await _apply_onboarding_habit(db, user_id=user_id, existing=existing, item=item)
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

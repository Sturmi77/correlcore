"""User preference helpers for M3 onboarding and insight UI state."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import UserPreference
from app.schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.services.home_sections import merge_home_sections, normalize_home_sections


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


async def get_or_create_user_preferences(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> UserPreference:
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    preferences = result.scalar_one_or_none()
    if preferences is not None:
        return preferences

    preferences = UserPreference(user_id=user_id)
    db.add(preferences)
    await db.flush()
    await db.refresh(preferences)
    return preferences


async def update_user_preferences(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: UserPreferencesUpdate,
) -> UserPreference:
    preferences = await get_or_create_user_preferences(db, user_id=user_id)
    updates = payload.model_dump(exclude_unset=True)

    for key, value in updates.items():
        if value is None:
            continue
        if key in {"dismissed_insight_keys", "reached_milestone_keys"}:
            value = _dedupe_strings(value)
        if key == "home_sections":
            normalized = normalize_home_sections(value)
            if normalized is not None:
                setattr(preferences, key, normalized)
            continue
        setattr(preferences, key, value)

    await db.flush()
    await db.refresh(preferences)
    return preferences


def to_preferences_response(preferences: UserPreference) -> UserPreferencesResponse:
    """Serialize preferences with merged home section defaults."""
    normalized_sections = normalize_home_sections(preferences.home_sections)
    payload = {
        "user_id": preferences.user_id,
        "analytics_enabled": preferences.analytics_enabled,
        "digest_enabled": preferences.digest_enabled,
        "onboarding_retro_completed": preferences.onboarding_retro_completed,
        "onboarding_profile_completed": preferences.onboarding_profile_completed,
        "onboarding_maturity_intro_seen": preferences.onboarding_maturity_intro_seen,
        "cycle_tracking_enabled": preferences.cycle_tracking_enabled,
        "dismissed_insight_keys": preferences.dismissed_insight_keys,
        "reached_milestone_keys": preferences.reached_milestone_keys,
        "last_seen_insight_at": preferences.last_seen_insight_at,
        "home_sections": merge_home_sections(normalized_sections),
        "created_at": preferences.created_at,
        "updated_at": preferences.updated_at,
    }
    return UserPreferencesResponse.model_validate(payload)

"""Service helpers for optional onboarding profile data."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileUpsert


async def upsert_user_profile(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: UserProfileUpsert,
) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    for key, value in payload.model_dump().items():
        setattr(profile, key, value)

    await db.flush()
    await db.refresh(profile)
    return profile

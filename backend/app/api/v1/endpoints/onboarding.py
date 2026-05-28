"""M4 guided onboarding endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.onboarding import (
    OnboardingCompleteRequest,
    OnboardingCompleteResponse,
    TagSuggestionsResponse,
)
from app.schemas.tag import TagResponse
from app.services.onboarding_service import complete_onboarding, tag_suggestions

router = APIRouter()


@router.get(
    "/tag-suggestions",
    response_model=TagSuggestionsResponse,
    summary="Return guided onboarding tag suggestions",
)
@limiter.limit("120/minute")
async def get_tag_suggestions_endpoint(request: Request) -> TagSuggestionsResponse:
    return tag_suggestions()


@router.post(
    "/complete",
    response_model=OnboardingCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete guided onboarding",
)
@limiter.limit("20/minute")
async def complete_onboarding_endpoint(
    request: Request,
    payload: OnboardingCompleteRequest,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> OnboardingCompleteResponse:
    preferences, tags = await complete_onboarding(db, user_id=user.id, tags=payload.tags)
    return OnboardingCompleteResponse(
        created_tags=[TagResponse.model_validate(tag) for tag in tags],
        onboarding_retro_completed=preferences.onboarding_retro_completed,
        onboarding_profile_completed=preferences.onboarding_profile_completed,
    )

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.user import User
from app.models.user_preference import UserPreference


def _make_preferences(user: User) -> UserPreference:
    now = datetime.now(UTC)
    preferences = UserPreference()
    preferences.user_id = user.id
    preferences.analytics_enabled = True
    preferences.onboarding_retro_completed = True
    preferences.onboarding_profile_completed = True
    preferences.dismissed_insight_keys = []
    preferences.reached_milestone_keys = []
    preferences.last_seen_insight_at = None
    preferences.created_at = now
    preferences.updated_at = now
    return preferences


@pytest.mark.asyncio
async def test_get_onboarding_tag_suggestions(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/onboarding/tag-suggestions")

    assert response.status_code == 200
    body = response.json()
    categories = {group["category"] for group in body["groups"]}
    assert {"work", "health", "social", "cycle"}.issubset(categories)


@pytest.mark.asyncio
async def test_complete_onboarding_marks_existing_preferences(
    async_client: AsyncClient, user: User
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.onboarding.complete_onboarding",
            new_callable=AsyncMock,
            return_value=(_make_preferences(user), []),
        ) as mocked:
            response = await async_client.post(
                "/api/v1/onboarding/complete",
                json={"tags": [{"slug": "deep-work", "name": "Deep work", "category": "work"}]},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["onboarding_retro_completed"] is True
    assert body["onboarding_profile_completed"] is True
    mocked.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_onboarding_rejects_invalid_tag_input(
    async_client: AsyncClient, user: User
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        response = await async_client.post(
            "/api/v1/onboarding/complete",
            json={"tags": [{"slug": "bad slug", "name": "Bad", "color": "purple"}]},
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422

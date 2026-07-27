from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.user import User
from app.models.user_preference import UserPreference
from app.schemas.onboarding import OnboardingTagInput
from app.services import onboarding_service


def _make_preferences(user: User) -> UserPreference:
    now = datetime.now(UTC)
    preferences = UserPreference()
    preferences.user_id = user.id
    preferences.analytics_enabled = True
    preferences.onboarding_retro_completed = True
    preferences.onboarding_profile_completed = True
    preferences.onboarding_maturity_intro_seen = False
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
    assert categories == {
        "sport",
        "work",
        "health",
        "social",
        "cycle",
        "leisure",
        "consumption",
        "other",
    }
    sport_group = next(group for group in body["groups"] if group["category"] == "sport")
    assert len(sport_group["suggestions"]) >= 2
    # Social media is seeded as a plain leisure tag (#542).
    leisure_group = next(group for group in body["groups"] if group["category"] == "leisure")
    assert any(s["slug"] == "social-media" for s in leisure_group["suggestions"])


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


@pytest.mark.asyncio
async def test_complete_onboarding_rejects_habit_without_frequency(
    async_client: AsyncClient, user: User
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        response = await async_client.post(
            "/api/v1/onboarding/complete",
            json={
                "tags": [
                    {"slug": "walk", "name": "Walk", "category": "health", "habit_type": "build"}
                ]
            },
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_complete_onboarding_creates_new_habit_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    """A build/reduce pick is created as a habit tag with its target (#564)."""
    created_payloads = []

    async def fake_find(db, *, user_id, slug):  # noqa: ANN001, ANN202
        return None

    async def fake_create(db, *, user_id, payload):  # noqa: ANN001, ANN202
        created_payloads.append(payload)
        tag = MagicMock()
        tag.id = uuid.uuid4()
        return tag

    async def fake_prefs(db, *, user_id, payload):  # noqa: ANN001, ANN202
        return MagicMock()

    monkeypatch.setattr(onboarding_service, "_find_visible_tag_by_slug", fake_find)
    monkeypatch.setattr(onboarding_service, "create_custom_tag", fake_create)
    monkeypatch.setattr(onboarding_service, "update_user_preferences", fake_prefs)

    await onboarding_service.complete_onboarding(
        MagicMock(),
        user_id=uuid.uuid4(),
        tags=[
            OnboardingTagInput(
                slug="meditation",
                name="Meditation",
                category="health",
                habit_type="build",
                target_frequency=3,
            )
        ],
    )

    assert created_payloads[0].habit_type == "build"
    assert created_payloads[0].target_frequency == 3


@pytest.mark.asyncio
async def test_complete_onboarding_sets_habit_on_existing_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A habit on an already-existing/default tag goes through update_custom_tag (#564)."""
    existing = MagicMock()
    existing.id = uuid.uuid4()
    updates = []

    async def fake_find(db, *, user_id, slug):  # noqa: ANN001, ANN202
        return existing

    async def fake_update(db, *, user_id, tag_id, payload):  # noqa: ANN001, ANN202
        updates.append((tag_id, payload))
        return MagicMock()

    async def fake_prefs(db, *, user_id, payload):  # noqa: ANN001, ANN202
        return MagicMock()

    monkeypatch.setattr(onboarding_service, "_find_visible_tag_by_slug", fake_find)
    monkeypatch.setattr(onboarding_service, "update_custom_tag", fake_update)
    monkeypatch.setattr(onboarding_service, "update_user_preferences", fake_prefs)

    await onboarding_service.complete_onboarding(
        MagicMock(),
        user_id=uuid.uuid4(),
        tags=[
            OnboardingTagInput(
                slug="walk",
                name="Walk",
                category="health",
                habit_type="reduce",
                target_frequency=2,
            )
        ],
    )

    assert updates[0][0] == existing.id
    assert updates[0][1].habit_type == "reduce"
    assert updates[0][1].target_frequency == 2

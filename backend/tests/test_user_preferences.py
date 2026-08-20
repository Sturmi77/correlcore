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
from app.models.user_profile import (
    InsightCuriosity,
    SleepHoursTypical,
    UserProfile,
    WorkContextTypical,
)
from app.schemas.user_preferences import UserPreferencesUpdate
from app.schemas.user_profile import UserProfileUpsert
from app.services.user_preferences_service import (
    add_dismissed_insight_keys,
    prune_orphaned_dismissed_insight_keys,
    remove_dismissed_insight_keys,
    update_user_preferences,
)
from app.services.user_profile_service import get_or_create_user_profile, upsert_user_profile
from tests.conftest import make_user


def _scalar_optional_result(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _rows_result(values: list[tuple[object, ...]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values
    return result


def _make_preferences(user: User) -> UserPreference:
    now = datetime.now(UTC)
    preferences = UserPreference()
    preferences.user_id = user.id
    preferences.analytics_enabled = True
    preferences.digest_enabled = True
    preferences.onboarding_retro_completed = False
    preferences.onboarding_profile_completed = False
    preferences.onboarding_maturity_intro_seen = False
    preferences.cycle_tracking_enabled = True
    preferences.health_connect_sync_sleep_enabled = True
    preferences.dismissed_insight_keys = []
    preferences.reached_milestone_keys = []
    preferences.last_seen_insight_at = None
    preferences.last_seen_digest_at = None
    preferences.created_at = now
    preferences.updated_at = now
    return preferences


def _make_profile(user: User) -> UserProfile:
    now = datetime.now(UTC)
    profile = UserProfile()
    profile.user_id = user.id
    profile.sleep_hours_typical = None
    profile.work_context_typical = None
    profile.sport_frequency = None
    profile.insight_curiosity = None
    profile.created_at = now
    profile.updated_at = now
    return profile


@pytest.mark.asyncio
async def test_update_user_preferences_dedupes_dismissed_keys() -> None:
    user = make_user()
    preferences = _make_preferences(user)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_optional_result(preferences))
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    out = await update_user_preferences(
        db,
        user_id=user.id,
        payload=UserPreferencesUpdate(
            dismissed_insight_keys=["first_week_pattern", " first_week_pattern ", ""]
        ),
    )

    assert out.dismissed_insight_keys == ["first_week_pattern"]
    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once_with(preferences)


@pytest.mark.asyncio
async def test_update_user_preferences_sets_last_seen_digest_at() -> None:
    # #739: the one-time modal marks a digest seen by patching this timestamp.
    user = make_user()
    preferences = _make_preferences(user)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_optional_result(preferences))
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    seen_at = datetime(2026, 8, 16, 3, tzinfo=UTC)
    out = await update_user_preferences(
        db,
        user_id=user.id,
        payload=UserPreferencesUpdate(last_seen_digest_at=seen_at),
    )

    assert out.last_seen_digest_at == seen_at


@pytest.mark.asyncio
async def test_update_user_preferences_last_seen_digest_at_is_monotonic() -> None:
    # #739: a stale client must not move the high-water mark backward.
    user = make_user()
    preferences = _make_preferences(user)
    preferences.last_seen_digest_at = datetime(2026, 8, 16, 3, tzinfo=UTC)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_optional_result(preferences))
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    out = await update_user_preferences(
        db,
        user_id=user.id,
        payload=UserPreferencesUpdate(last_seen_digest_at=datetime(2026, 8, 9, 3, tzinfo=UTC)),
    )

    # Older timestamp ignored; newer one accepted.
    assert out.last_seen_digest_at == datetime(2026, 8, 16, 3, tzinfo=UTC)
    out = await update_user_preferences(
        db,
        user_id=user.id,
        payload=UserPreferencesUpdate(last_seen_digest_at=datetime(2026, 8, 23, 3, tzinfo=UTC)),
    )
    assert out.last_seen_digest_at == datetime(2026, 8, 23, 3, tzinfo=UTC)


@pytest.mark.asyncio
async def test_add_and_remove_dismissed_insight_keys() -> None:
    user = make_user()
    preferences = _make_preferences(user)
    preferences.dismissed_insight_keys = ["keep_me"]
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_optional_result(preferences))
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    added = await add_dismissed_insight_keys(db, user_id=user.id, keys=["keep_me", "new_key", ""])
    assert added.dismissed_insight_keys == ["keep_me", "new_key"]

    removed = await remove_dismissed_insight_keys(db, user_id=user.id, keys=["new_key"])
    assert removed.dismissed_insight_keys == ["keep_me"]


@pytest.mark.asyncio
async def test_prune_orphaned_dismissed_insight_keys_keeps_banner_and_live_uuids() -> None:
    user = make_user()
    preferences = _make_preferences(user)
    live_id = uuid.uuid4()
    orphan_id = uuid.uuid4()
    preferences.dismissed_insight_keys = [
        "early_context_pattern",
        str(live_id),
        str(orphan_id),
    ]
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_optional_result(preferences),
            _rows_result([(live_id,)]),
        ]
    )
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    out = await prune_orphaned_dismissed_insight_keys(db, user_id=user.id)

    assert out.dismissed_insight_keys == ["early_context_pattern", str(live_id)]
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_preferences_endpoint_returns_and_updates_state(
    async_client: AsyncClient,
    user: User,
) -> None:
    preferences = _make_preferences(user)
    preferences.dismissed_insight_keys = ["first_week_pattern"]

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.user.prune_orphaned_dismissed_insight_keys",
            new_callable=AsyncMock,
            return_value=preferences,
        ):
            response = await async_client.get(
                "/api/v1/user/preferences",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["dismissed_insight_keys"] == ["first_week_pattern"]


@pytest.mark.asyncio
async def test_preferences_endpoint_updates_analytics_enabled(
    async_client: AsyncClient,
    user: User,
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.user.update_user_preferences",
            new_callable=AsyncMock,
        ) as update_mock:
            updated = _make_preferences(user)
            updated.analytics_enabled = False
            update_mock.return_value = updated

            response = await async_client.patch(
                "/api/v1/user/preferences",
                json={"analytics_enabled": False},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["analytics_enabled"] is False
    update_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_preferences_endpoint_returns_cycle_tracking_default(
    async_client: AsyncClient,
    user: User,
) -> None:
    preferences = _make_preferences(user)

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.user.prune_orphaned_dismissed_insight_keys",
            new_callable=AsyncMock,
            return_value=preferences,
        ):
            response = await async_client.get(
                "/api/v1/user/preferences",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cycle_tracking_enabled"] is True


@pytest.mark.asyncio
async def test_preferences_endpoint_disables_cycle_tracking(
    async_client: AsyncClient,
    user: User,
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.user.update_user_preferences",
            new_callable=AsyncMock,
        ) as update_mock:
            updated = _make_preferences(user)
            updated.cycle_tracking_enabled = False
            update_mock.return_value = updated

            response = await async_client.patch(
                "/api/v1/user/preferences",
                json={"cycle_tracking_enabled": False},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cycle_tracking_enabled"] is False
    update_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_user_profile_updates_optional_answers() -> None:
    user = make_user()
    profile = _make_profile(user)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_optional_result(profile))
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    out = await upsert_user_profile(
        db,
        user_id=user.id,
        payload=UserProfileUpsert(
            sleep_hours_typical=SleepHoursTypical.H7,
            insight_curiosity=InsightCuriosity.ENERGY_SLEEP,
        ),
    )

    assert out.sleep_hours_typical == SleepHoursTypical.H7
    assert out.insight_curiosity == InsightCuriosity.ENERGY_SLEEP
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_user_profile_creates_blank_profile() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_optional_result(None))
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    out = await get_or_create_user_profile(db, user_id=user.id)

    assert out.user_id == user.id
    assert out.work_context_typical is None
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once_with(out)


@pytest.mark.asyncio
async def test_profile_endpoint_returns_profile_state(
    async_client: AsyncClient,
    user: User,
) -> None:
    profile = _make_profile(user)
    profile.work_context_typical = WorkContextTypical.OFFICE

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.user.get_or_create_user_profile",
            new_callable=AsyncMock,
            return_value=profile,
        ):
            response = await async_client.get(
                "/api/v1/user/profile",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["work_context_typical"] == "office"

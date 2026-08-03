"""Tests for Health Connect sleep import (M8 Sprint 4, #172)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.user import User
from app.models.user_preference import UserPreference
from app.schemas.health_connect import HealthConnectImportResponse, HealthConnectSleepImportItem
from app.services.health_connect_import_service import import_health_connect_sleep
from tests.conftest import make_db_session_with_results, make_entry, make_user


def _prefs(user: User, *, sleep_enabled: bool = True) -> UserPreference:
    prefs = UserPreference(user_id=user.id)
    # Transient instances don't get server defaults — set explicitly.
    prefs.health_connect_sync_sleep_enabled = sleep_enabled
    return prefs


def _db_with_entries(prefs: UserPreference, entries: list) -> MagicMock:
    """Mock a preferences lookup (``scalar_one_or_none``) followed by the
    single batched entries lookup (``scalars().all()``) the service now
    issues instead of one SELECT per import item."""
    db = MagicMock()
    db.flush = AsyncMock()
    prefs_result = MagicMock()
    prefs_result.scalar_one_or_none.return_value = prefs
    entries_result = MagicMock()
    entries_result.scalars.return_value.all.return_value = entries
    db.execute = AsyncMock(side_effect=[prefs_result, entries_result])
    return db


# ---------------------------------------------------------------------------
# Service: merge rules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_fills_empty_sleep_on_existing_entry(rest_revision_recorders) -> None:
    user = make_user()
    entry = make_entry(user)  # sleep_minutes defaults to None
    db = _db_with_entries(_prefs(user), [entry])

    result = await import_health_connect_sleep(
        db,
        user_id=user.id,
        items=[HealthConnectSleepImportItem(entry_date=entry.entry_date, sleep_minutes=430)],
    )

    assert entry.sleep_minutes == 430
    assert result.updated == 1
    assert result.skipped_existing_value == 0
    assert result.sleep_sync_enabled is True
    assert result.updated_entry_dates == [entry.entry_date]
    assert result.skipped_existing_entry_dates == []
    rest_revision_recorders["entry"].assert_awaited_once()


@pytest.mark.asyncio
async def test_import_batches_entry_lookup_into_one_query(rest_revision_recorders) -> None:
    """A multi-night import issues one preferences query + one batched entries
    query — never one entry query per item (#634 review)."""
    user = make_user()
    entries = [make_entry(user, entry_date=date(2026, 8, day)) for day in (1, 2, 3)]
    db = _db_with_entries(_prefs(user), entries)

    result = await import_health_connect_sleep(
        db,
        user_id=user.id,
        items=[
            HealthConnectSleepImportItem(entry_date=e.entry_date, sleep_minutes=400)
            for e in entries
        ],
    )

    assert result.updated == 3
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_import_never_overwrites_manual_sleep(rest_revision_recorders) -> None:
    user = make_user()
    entry = make_entry(user)
    entry.sleep_minutes = 400  # a value the user already typed
    db = _db_with_entries(_prefs(user), [entry])

    result = await import_health_connect_sleep(
        db,
        user_id=user.id,
        items=[HealthConnectSleepImportItem(entry_date=entry.entry_date, sleep_minutes=999)],
    )

    assert entry.sleep_minutes == 400  # manual wins
    assert result.updated == 0
    assert result.skipped_existing_value == 1
    assert result.updated_entry_dates == []
    assert result.skipped_existing_entry_dates == [entry.entry_date]
    rest_revision_recorders["entry"].assert_not_awaited()


@pytest.mark.asyncio
async def test_import_does_not_create_entries_for_untracked_days() -> None:
    user = make_user()
    db = _db_with_entries(_prefs(user), [])

    result = await import_health_connect_sleep(
        db,
        user_id=user.id,
        items=[HealthConnectSleepImportItem(entry_date=date.today(), sleep_minutes=420)],
    )

    assert result.updated == 0
    assert result.skipped_no_entry == 1


@pytest.mark.asyncio
async def test_import_skips_everything_when_toggle_disabled() -> None:
    user = make_user()
    db = make_db_session_with_results(_prefs(user, sleep_enabled=False))

    result = await import_health_connect_sleep(
        db,
        user_id=user.id,
        items=[HealthConnectSleepImportItem(entry_date=date.today(), sleep_minutes=420)],
    )

    assert result.sleep_sync_enabled is False
    assert result.updated == 0
    assert result.skipped_no_entry == 1


# ---------------------------------------------------------------------------
# Endpoint: consent gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_endpoint_403_without_consent(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.health_connect.is_consent_granted",
            new_callable=AsyncMock,
            return_value=False,
        ):
            r = await async_client.post(
                "/api/v1/health-connect/import",
                json={"sleep": [{"entry_date": date.today().isoformat(), "sleep_minutes": 430}]},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 403
    assert r.json()["detail"] == "health_connect_consent_required"


@pytest.mark.asyncio
async def test_import_endpoint_200_with_consent(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with (
            patch(
                "app.api.v1.endpoints.health_connect.is_consent_granted",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.health_connect.import_health_connect_sleep",
                new_callable=AsyncMock,
                return_value=HealthConnectImportResponse(
                    updated=2,
                    skipped_existing_value=1,
                    skipped_no_entry=0,
                    sleep_sync_enabled=True,
                ),
            ),
        ):
            r = await async_client.post(
                "/api/v1/health-connect/import",
                json={
                    "sleep": [
                        {"entry_date": date.today().isoformat(), "sleep_minutes": 430},
                    ]
                },
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["updated"] == 2
    assert body["sleep_sync_enabled"] is True

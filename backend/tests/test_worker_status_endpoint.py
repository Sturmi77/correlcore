"""Tests for the worker freshness/monitoring endpoint (#756)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_user_lax
from app.core.config import settings
from app.main import app
from app.models.worker_run import WorkerJobKind, WorkerRun, WorkerRunStatus, WorkerTriggerSource
from tests.conftest import make_user


@pytest.fixture(autouse=True)
def _reset_worker_status_state() -> Generator[None, None, None]:
    original_key = settings.WORKER_STATUS_API_KEY
    original_threshold = settings.WORKER_STALE_AFTER_HOURS
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    settings.WORKER_STATUS_API_KEY = original_key
    settings.WORKER_STALE_AFTER_HOURS = original_threshold


def _fake_run(job_kind: WorkerJobKind, *, finished_at: datetime) -> WorkerRun:
    return WorkerRun(
        id=uuid4(),
        worker_name="analytics",
        job_kind=job_kind,
        trigger_source=WorkerTriggerSource.SCHEDULED,
        status=WorkerRunStatus.SUCCEEDED,
        started_at=finished_at,
        finished_at=finished_at,
        scope_user_id=None,
        result={},
    )


def _no_session_user():
    async def _fake() -> None:
        return None

    return _fake


@pytest.mark.asyncio
async def test_worker_status_401_without_key_or_session(async_client: AsyncClient) -> None:
    settings.WORKER_STATUS_API_KEY = "secret-key"
    app.dependency_overrides[get_current_user_lax] = _no_session_user()

    response = await async_client.get("/api/v1/worker/status")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_worker_status_401_with_wrong_key(async_client: AsyncClient) -> None:
    settings.WORKER_STATUS_API_KEY = "secret-key"
    app.dependency_overrides[get_current_user_lax] = _no_session_user()

    response = await async_client.get(
        "/api/v1/worker/status",
        headers={"X-Worker-Status-Key": "wrong-key"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_worker_status_403_style_for_non_admin_session(async_client: AsyncClient) -> None:
    """Non-admin verified users are treated the same as unauthenticated (opaque 401)."""
    settings.WORKER_STATUS_API_KEY = ""
    user = make_user(verified=True, admin=False)

    async def fake_user():
        return user

    app.dependency_overrides[get_current_user_lax] = fake_user

    response = await async_client.get("/api/v1/worker/status")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_worker_status_ok_with_valid_api_key(async_client: AsyncClient) -> None:
    settings.WORKER_STATUS_API_KEY = "secret-key"
    settings.WORKER_STALE_AFTER_HOURS = 30
    app.dependency_overrides[get_current_user_lax] = _no_session_user()

    now = datetime.now(UTC)
    runs = {
        WorkerJobKind.DAILY_BUNDLE: _fake_run(
            WorkerJobKind.DAILY_BUNDLE, finished_at=now - timedelta(hours=2)
        ),
        WorkerJobKind.INSIGHTS: _fake_run(
            WorkerJobKind.INSIGHTS, finished_at=now - timedelta(hours=2)
        ),
        WorkerJobKind.DIGEST: _fake_run(WorkerJobKind.DIGEST, finished_at=now - timedelta(days=2)),
    }

    with patch(
        "app.api.v1.endpoints.worker_status.latest_successful_system_runs",
        new=AsyncMock(return_value=runs),
    ):
        response = await async_client.get(
            "/api/v1/worker/status",
            headers={"X-Worker-Status-Key": "secret-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    job_by_kind = {job["job_kind"]: job for job in data["jobs"]}
    assert job_by_kind["daily_bundle"]["stale"] is False
    assert job_by_kind["daily_bundle"]["job_status"] == "fresh"
    assert job_by_kind["digest"]["stale"] is False  # 48h age, 7x30=210h threshold


@pytest.mark.asyncio
async def test_worker_status_ok_with_admin_session(async_client: AsyncClient) -> None:
    settings.WORKER_STATUS_API_KEY = ""
    admin = make_user(verified=True, admin=True)

    async def fake_admin():
        return admin

    app.dependency_overrides[get_current_user_lax] = fake_admin

    now = datetime.now(UTC)
    runs = {
        WorkerJobKind.DAILY_BUNDLE: _fake_run(
            WorkerJobKind.DAILY_BUNDLE, finished_at=now - timedelta(hours=1)
        ),
        WorkerJobKind.INSIGHTS: _fake_run(
            WorkerJobKind.INSIGHTS, finished_at=now - timedelta(hours=1)
        ),
        WorkerJobKind.DIGEST: None,
    }

    with patch(
        "app.api.v1.endpoints.worker_status.latest_successful_system_runs",
        new=AsyncMock(return_value=runs),
    ):
        response = await async_client.get("/api/v1/worker/status")

    assert response.status_code == 200
    data = response.json()
    job_by_kind = {job["job_kind"]: job for job in data["jobs"]}
    # DIGEST never ran -> counts as stale/never_run but does not 500.
    assert job_by_kind["digest"]["job_status"] == "never_run"
    assert job_by_kind["digest"]["stale"] is True
    # Overall status reflects the digest gap even though daily jobs are fresh.
    assert data["status"] == "stale"


@pytest.mark.asyncio
async def test_worker_status_flags_stale_daily_bundle(async_client: AsyncClient) -> None:
    settings.WORKER_STATUS_API_KEY = "secret-key"
    settings.WORKER_STALE_AFTER_HOURS = 30
    app.dependency_overrides[get_current_user_lax] = _no_session_user()

    now = datetime.now(UTC)
    runs = {
        WorkerJobKind.DAILY_BUNDLE: _fake_run(
            WorkerJobKind.DAILY_BUNDLE, finished_at=now - timedelta(hours=40)
        ),
        WorkerJobKind.INSIGHTS: _fake_run(
            WorkerJobKind.INSIGHTS, finished_at=now - timedelta(hours=40)
        ),
        WorkerJobKind.DIGEST: _fake_run(WorkerJobKind.DIGEST, finished_at=now - timedelta(days=2)),
    }

    with patch(
        "app.api.v1.endpoints.worker_status.latest_successful_system_runs",
        new=AsyncMock(return_value=runs),
    ):
        response = await async_client.get(
            "/api/v1/worker/status",
            headers={"X-Worker-Status-Key": "secret-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stale"
    job_by_kind = {job["job_kind"]: job for job in data["jobs"]}
    assert job_by_kind["daily_bundle"]["job_status"] == "stale"
    assert job_by_kind["daily_bundle"]["age_hours"] == pytest.approx(40, abs=0.1)


@pytest.mark.asyncio
async def test_worker_status_is_stale_when_all_insight_users_failed(
    async_client: AsyncClient,
) -> None:
    """A SUCCEEDED batch with no successful user work is excluded by the query."""

    settings.WORKER_STATUS_API_KEY = "secret-key"
    settings.WORKER_STALE_AFTER_HOURS = 30
    app.dependency_overrides[get_current_user_lax] = _no_session_user()
    now = datetime.now(UTC)
    runs = {
        WorkerJobKind.DAILY_BUNDLE: _fake_run(
            WorkerJobKind.DAILY_BUNDLE, finished_at=now - timedelta(hours=1)
        ),
        # latest_successful_system_runs() returns None here because the latest
        # SUCCEEDED insight row had failed_users == eligible_users.
        WorkerJobKind.INSIGHTS: None,
        WorkerJobKind.DIGEST: _fake_run(WorkerJobKind.DIGEST, finished_at=now - timedelta(days=2)),
    }

    with patch(
        "app.api.v1.endpoints.worker_status.latest_successful_system_runs",
        new=AsyncMock(return_value=runs),
    ):
        response = await async_client.get(
            "/api/v1/worker/status",
            headers={"X-Worker-Status-Key": "secret-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stale"
    job_by_kind = {job["job_kind"]: job for job in data["jobs"]}
    assert job_by_kind["insights"]["job_status"] == "never_run"
    assert job_by_kind["insights"]["stale"] is True

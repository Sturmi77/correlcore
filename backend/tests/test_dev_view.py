"""Tests for the feature-flagged developer diagnostics endpoint."""

from __future__ import annotations

import socket
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_user
from app.core.config import settings
from app.main import app
from app.models.worker_run import WorkerJobKind, WorkerRun, WorkerRunStatus, WorkerTriggerSource
from app.schemas.dev import DevHealthComponent, DevInfoResponse
from app.services.dev_service import (
    _probe_minio_sync,
    _probe_smtp_sync,
    _probe_web_sync,
    _probe_worker_sync,
    _tcp_probe_sync,
    build_dev_info,
)
from app.services.health_service import ComponentHealth, ComponentStatus, ReadinessReport
from tests.conftest import make_user


def _dev_payload() -> DevInfoResponse:
    return DevInfoResponse(
        image_hash="ghcr.io/sturmi77/correlcore-api@sha256:abc",
        image_digest="ghcr.io/sturmi77/correlcore-api@sha256:abc",
        image_tag="sha-26c4274",
        build_time="2026-05-10T16:00:00Z",
        git_commit="26c4274e0b2688931f7ceab108d72b775233fdf7",
        git_branch="main",
        python_version="3.12.13",
        fastapi_version="0.115.0",
        db_migration_head="009",
        db_pool_size=10,
        db_checked_out=1,
        redis_connected=True,
        minio_connected=False,
        health_ready=True,
        uptime_seconds=42,
        health_components=[
            DevHealthComponent(name="api", status="ok", detail="process"),
            DevHealthComponent(name="postgres", status="ok"),
            DevHealthComponent(name="redis", status="ok"),
            DevHealthComponent(name="encryption", status="ok"),
            DevHealthComponent(name="minio", status="down", detail="unresolved"),
        ],
    )


@pytest.fixture(autouse=True)
def _reset_dev_state() -> Generator[None, None, None]:
    original = {
        "DEV_VIEW_ENABLED": settings.DEV_VIEW_ENABLED,
        "APP_ENV": settings.APP_ENV,
        "DEV_DB_BACKUP_DIR": settings.DEV_DB_BACKUP_DIR,
        "IMAGE_DIGEST": settings.IMAGE_DIGEST,
        "IMAGE_TAG": settings.IMAGE_TAG,
        "GIT_COMMIT": settings.GIT_COMMIT,
        "GIT_BRANCH": settings.GIT_BRANCH,
        "BUILD_TIME": settings.BUILD_TIME,
        "SMTP_HOST": settings.SMTP_HOST,
        "SMTP_PORT": settings.SMTP_PORT,
        "DEV_DOCKER_HOST": settings.DEV_DOCKER_HOST,
        "DATABASE_URL": settings.DATABASE_URL,
    }
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    for key, value in original.items():
        setattr(settings, key, value)


@pytest.mark.asyncio
async def test_dev_info_404_when_feature_flag_off(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = False

    response = await async_client.get("/api/v1/dev/info")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dev_info_401_when_enabled_but_unauthenticated(
    async_client: AsyncClient,
) -> None:
    settings.DEV_VIEW_ENABLED = True

    response = await async_client.get("/api/v1/dev/info")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dev_info_403_for_unverified_user(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = True
    user = make_user(verified=False)

    async def fake_current_user():
        yield user

    app.dependency_overrides[get_current_user] = fake_current_user

    response = await async_client.get("/api/v1/dev/info")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_dev_info_200_for_verified_user(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = True
    settings.IMAGE_DIGEST = "ghcr.io/sturmi77/correlcore-api@sha256:abc"
    settings.IMAGE_TAG = "sha-26c4274"
    settings.GIT_COMMIT = "26c4274e0b2688931f7ceab108d72b775233fdf7"
    settings.GIT_BRANCH = "main"
    settings.BUILD_TIME = "2026-05-10T16:00:00Z"
    user = make_user(verified=True)

    async def fake_current_user():
        yield user

    app.dependency_overrides[get_current_user] = fake_current_user

    with patch(
        "app.api.v1.endpoints.dev.build_dev_info",
        new_callable=AsyncMock,
        return_value=_dev_payload(),
    ):
        response = await async_client.get("/api/v1/dev/info")

    assert response.status_code == 200
    data = response.json()
    assert data["image_digest"] == "ghcr.io/sturmi77/correlcore-api@sha256:abc"
    assert data["image_tag"] == "sha-26c4274"
    assert data["git_commit"] == "26c4274e0b2688931f7ceab108d72b775233fdf7"
    assert data["git_branch"] == "main"
    assert data["build_time"] == "2026-05-10T16:00:00Z"
    assert [item["name"] for item in data["health_components"]] == [
        "api",
        "postgres",
        "redis",
        "encryption",
        "minio",
    ]


@pytest.mark.asyncio
async def test_dev_info_empty_digest_serializes_as_null(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = True
    user = make_user(verified=True)
    payload = _dev_payload()
    payload.image_hash = "sha-26c4274"
    payload.image_digest = None

    async def fake_current_user():
        yield user

    app.dependency_overrides[get_current_user] = fake_current_user

    with patch(
        "app.api.v1.endpoints.dev.build_dev_info",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        response = await async_client.get("/api/v1/dev/info")

    assert response.status_code == 200
    assert response.json()["image_digest"] is None


@pytest.mark.asyncio
async def test_build_dev_info_reads_version_settings() -> None:
    settings.IMAGE_DIGEST = ""
    settings.IMAGE_TAG = "sha-26c4274"
    settings.GIT_COMMIT = "26c4274e0b2688931f7ceab108d72b775233fdf7"
    settings.GIT_BRANCH = "main"
    settings.BUILD_TIME = "2026-05-10T16:00:00Z"

    async def ready() -> ReadinessReport:
        return ReadinessReport(
            ready=True,
            components=[ComponentHealth(name="redis", status=ComponentStatus.OK)],
        )

    def pool_metric(name: str) -> int | None:
        return {"size": 10, "checkedout": 2}.get(name)

    minio = DevHealthComponent(name="minio", status="ok")
    web = DevHealthComponent(name="web", status="ok")
    smtp = DevHealthComponent(name="mailpit", status="ok")
    worker = DevHealthComponent(name="worker", status="ok", detail="resolved")

    with (
        patch("app.services.dev_service.check_readiness", side_effect=ready),
        patch("app.services.dev_service._db_migration_head", AsyncMock(return_value="009")),
        patch(
            "app.services.dev_service._collect_optional_probes",
            AsyncMock(return_value=(minio, web, smtp, worker)),
        ),
        patch("app.services.dev_service.list_stack_containers", return_value=[]),
        patch("app.services.dev_service._pool_metric", side_effect=pool_metric),
    ):
        info = await build_dev_info(AsyncMock(spec=AsyncSession))

    assert info.image_digest is None
    assert info.image_hash == "sha-26c4274"
    assert info.image_tag == "sha-26c4274"
    assert info.git_commit == "26c4274e0b2688931f7ceab108d72b775233fdf7"
    assert info.git_branch == "main"
    assert info.build_time == "2026-05-10T16:00:00Z"
    assert info.redis_connected is True
    assert info.minio_connected is True
    assert info.health_ready is True
    assert info.db_migration_head == "009"
    assert info.db_pool_size == 10
    assert info.db_checked_out == 2
    assert [component.name for component in info.health_components] == [
        "api",
        "redis",
        "web",
        "worker",
        "minio",
        "mailpit",
    ]
    assert all(component.status == "ok" for component in info.health_components)


def test_tcp_probe_sync_ok_down_and_unresolved() -> None:
    with patch("app.services.dev_service.socket.create_connection"):
        status, detail = _tcp_probe_sync("web", 3000)
    assert status is ComponentStatus.OK
    assert detail == ""

    with patch(
        "app.services.dev_service.socket.create_connection",
        side_effect=TimeoutError(),
    ):
        status, detail = _tcp_probe_sync("web", 3000)
    assert status is ComponentStatus.DOWN
    assert detail == "TimeoutError"

    with patch(
        "app.services.dev_service.socket.create_connection",
        side_effect=socket.gaierror(),
    ):
        status, detail = _tcp_probe_sync("missing", 3000)
    assert status is None
    assert detail == "unresolved"


def test_optional_probes_omit_unresolved_web_and_empty_smtp() -> None:
    settings.SMTP_HOST = ""
    with patch(
        "app.services.dev_service._tcp_probe_sync",
        return_value=(None, "unresolved"),
    ):
        assert _probe_web_sync() is None
        minio = _probe_minio_sync()
        assert minio.name == "minio"
        assert minio.status == "down"
        assert minio.detail == "unresolved"
        assert _probe_smtp_sync() is None


def test_web_probe_lists_down_when_port_closed() -> None:
    with patch(
        "app.services.dev_service._tcp_probe_sync",
        return_value=(ComponentStatus.DOWN, "ConnectionRefusedError"),
    ):
        component = _probe_web_sync()
    assert component is not None
    assert component.name == "web"
    assert component.status == "down"
    assert component.detail == "ConnectionRefusedError"


def test_worker_probe_reports_stopped_on_compose_network() -> None:
    settings.DATABASE_URL = "postgresql+asyncpg://u:p@postgres:5432/correlcore"
    with patch(
        "app.services.dev_service.socket.getaddrinfo",
        side_effect=socket.gaierror(),
    ):
        component = _probe_worker_sync()
    assert component is not None
    assert component.name == "worker"
    assert component.status == "down"
    assert component.detail == "stopped"


def test_worker_probe_ok_when_hostname_resolves() -> None:
    settings.DATABASE_URL = "postgresql+asyncpg://u:p@postgres:5432/correlcore"
    with patch("app.services.dev_service.socket.getaddrinfo"):
        component = _probe_worker_sync()
    assert component is not None
    assert component.status == "ok"
    assert component.detail == "resolved"


def test_worker_probe_omitted_outside_compose() -> None:
    settings.DATABASE_URL = "postgresql+asyncpg://u:p@localhost:5432/correlcore"
    assert _probe_worker_sync() is None


def test_smtp_probe_uses_mailpit_name_for_compose_host() -> None:
    settings.SMTP_HOST = "mailpit"
    settings.SMTP_PORT = 1025
    with patch(
        "app.services.dev_service._tcp_probe_sync",
        return_value=(ComponentStatus.OK, ""),
    ) as probe:
        component = _probe_smtp_sync()
    assert component is not None
    assert component.name == "mailpit"
    assert component.status == "ok"
    probe.assert_called_once_with("mailpit", 1025)


def _fake_run(**overrides: object) -> WorkerRun:
    run = WorkerRun(
        id=uuid4(),
        worker_name="analytics",
        job_kind=WorkerJobKind.USER_INSIGHTS,
        trigger_source=WorkerTriggerSource.USER_REGENERATE,
        status=WorkerRunStatus.SUCCEEDED,
        started_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 7, 13, 12, 1, tzinfo=UTC),
        scope_user_id=uuid4(),
        result={"insight_count": 3},
        error_message=None,
    )
    for key, value in overrides.items():
        setattr(run, key, value)
    return run


@pytest.mark.asyncio
async def test_dev_workers_404_when_feature_flag_off(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = False
    response = await async_client.get("/api/v1/dev/workers")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dev_workers_latest_returns_cards(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = True
    user = make_user(verified=True)

    async def fake_current_user():
        yield user

    app.dependency_overrides[get_current_user] = fake_current_user
    user_run = _fake_run(scope_user_id=user.id)

    with patch(
        "app.api.v1.endpoints.dev.worker_run_service.latest_worker_runs",
        new=AsyncMock(
            return_value={
                "daily_bundle": None,
                "fleet_insights": None,
                "user_insights": user_run,
            }
        ),
    ):
        response = await async_client.get("/api/v1/dev/workers/latest")

    assert response.status_code == 200
    data = response.json()
    assert data["ops_ready"] is False
    assert data["user_insights"]["result"]["insight_count"] == 3
    assert data["daily_bundle"] is None


@pytest.mark.asyncio
async def test_dev_db_backups_404_outside_development(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = True
    settings.APP_ENV = "production"
    user = make_user(verified=True)

    async def fake_current_user():
        yield user

    app.dependency_overrides[get_current_user] = fake_current_user

    response = await async_client.get("/api/v1/dev/db/backups")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dev_db_backups_lists_when_development(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = True
    settings.APP_ENV = "development"
    user = make_user(verified=True)

    async def fake_current_user():
        yield user

    app.dependency_overrides[get_current_user] = fake_current_user

    with patch(
        "app.api.v1.endpoints.dev.list_backups",
        return_value=(
            [
                {
                    "name": "correlcore-dev-20260713T120000Z.dump",
                    "size_bytes": 128,
                    "created_at": datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
                    "meta": {"ops_ready": False},
                }
            ],
            "/tmp/correlcore-backups",
        ),
    ):
        response = await async_client.get("/api/v1/dev/db/backups")

    assert response.status_code == 200
    data = response.json()
    assert data["ops_ready"] is False
    assert data["encryption_key_required"] is True
    assert data["items"][0]["name"].endswith(".dump")


@pytest.mark.asyncio
async def test_dev_db_restore_requires_confirm(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = True
    settings.APP_ENV = "development"
    user = make_user(verified=True)

    async def fake_current_user():
        yield user

    app.dependency_overrides[get_current_user] = fake_current_user

    response = await async_client.post(
        "/api/v1/dev/db/restore",
        json={"name": "correlcore-dev-20260713T120000Z.dump", "confirm": False},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_dev_insights_run_once(async_client: AsyncClient) -> None:
    settings.DEV_VIEW_ENABLED = True
    settings.APP_ENV = "development"
    user = make_user(verified=True)

    async def fake_current_user():
        yield user

    app.dependency_overrides[get_current_user] = fake_current_user

    summary = MagicMock(
        eligible_users=2,
        processed_users=2,
        failed_users=0,
        generated_insights=5,
    )
    with patch(
        "app.api.v1.endpoints.dev.run_insights_once",
        new=AsyncMock(return_value=summary),
    ):
        response = await async_client.post("/api/v1/dev/workers/insights/run-once")

    assert response.status_code == 200
    assert response.json()["generated_insights"] == 5

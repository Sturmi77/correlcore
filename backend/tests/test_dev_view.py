"""Tests for the feature-flagged developer diagnostics endpoint."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_user
from app.core.config import settings
from app.main import app
from app.schemas.dev import DevInfoResponse
from app.services.dev_service import build_dev_info
from app.services.health_service import ComponentHealth, ComponentStatus, ReadinessReport
from tests.conftest import make_user


def _dev_payload() -> DevInfoResponse:
    return DevInfoResponse(
        image_hash="ghcr.io/sturmi77/moodsync-api@sha256:abc",
        image_digest="ghcr.io/sturmi77/moodsync-api@sha256:abc",
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
    )


@pytest.fixture(autouse=True)
def _reset_dev_state() -> Generator[None, None, None]:
    original = {
        "DEV_VIEW_ENABLED": settings.DEV_VIEW_ENABLED,
        "IMAGE_DIGEST": settings.IMAGE_DIGEST,
        "IMAGE_TAG": settings.IMAGE_TAG,
        "GIT_COMMIT": settings.GIT_COMMIT,
        "GIT_BRANCH": settings.GIT_BRANCH,
        "BUILD_TIME": settings.BUILD_TIME,
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
    settings.IMAGE_DIGEST = "ghcr.io/sturmi77/moodsync-api@sha256:abc"
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
    assert data["image_digest"] == "ghcr.io/sturmi77/moodsync-api@sha256:abc"
    assert data["image_tag"] == "sha-26c4274"
    assert data["git_commit"] == "26c4274e0b2688931f7ceab108d72b775233fdf7"
    assert data["git_branch"] == "main"
    assert data["build_time"] == "2026-05-10T16:00:00Z"


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

    with (
        patch("app.services.dev_service.check_readiness", side_effect=ready),
        patch("app.services.dev_service._db_migration_head", AsyncMock(return_value="009")),
        patch("app.services.dev_service._probe_minio", AsyncMock(return_value=True)),
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

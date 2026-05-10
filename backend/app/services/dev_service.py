"""Developer diagnostics service for the feature-flagged /dev view."""

from __future__ import annotations

import asyncio
import logging
import socket
import sys
import time
from urllib.parse import urlparse

import fastapi
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import engine
from app.schemas.dev import DevInfoResponse
from app.services.health_service import ComponentStatus, check_readiness

logger = logging.getLogger(__name__)
_STARTED_AT_MONOTONIC = time.monotonic()


def _optional_env(value: str) -> str | None:
    value = value.strip()
    return value or None


def _pool_metric(name: str) -> int | None:
    pool = engine.sync_engine.pool
    attr = getattr(pool, name, None)
    if not callable(attr):
        return None
    try:
        return int(attr())
    except Exception as exc:  # pragma: no cover - defensive across pool impls
        logger.warning("dev info pool metric failed: %s", type(exc).__name__)
        return None


async def _db_migration_head(db: AsyncSession) -> str | None:
    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        value = result.scalar_one_or_none()
        return str(value) if value is not None else None
    except Exception as exc:
        logger.warning("dev info migration head lookup failed: %s", type(exc).__name__)
        return None


def _minio_endpoint_host_port() -> tuple[str, int]:
    raw = settings.MINIO_ENDPOINT.strip()
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = parsed.hostname or "minio"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port


def _probe_minio_sync() -> bool:
    try:
        host, port = _minio_endpoint_host_port()
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception as exc:
        logger.warning("dev info minio probe failed: %s", type(exc).__name__)
        return False


async def _probe_minio() -> bool:
    return await asyncio.to_thread(_probe_minio_sync)


async def build_dev_info(db: AsyncSession) -> DevInfoResponse:
    readiness, migration_head, minio_connected = await asyncio.gather(
        check_readiness(),
        _db_migration_head(db),
        _probe_minio(),
    )
    redis_connected = any(
        component.name == "redis" and component.status == ComponentStatus.OK
        for component in readiness.components
    )
    image_digest = _optional_env(settings.IMAGE_DIGEST)
    image_hash = image_digest or settings.IMAGE_TAG
    return DevInfoResponse(
        image_hash=image_hash,
        image_digest=image_digest,
        image_tag=settings.IMAGE_TAG,
        build_time=_optional_env(settings.BUILD_TIME),
        git_commit=settings.GIT_COMMIT,
        git_branch=settings.GIT_BRANCH,
        python_version=sys.version.split()[0],
        fastapi_version=fastapi.__version__,
        db_migration_head=migration_head,
        db_pool_size=_pool_metric("size"),
        db_checked_out=_pool_metric("checkedout"),
        redis_connected=redis_connected,
        minio_connected=minio_connected,
        health_ready=readiness.ready,
        uptime_seconds=max(0, int(time.monotonic() - _STARTED_AT_MONOTONIC)),
    )

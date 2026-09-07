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
from app.schemas.dev import DevHealthComponent, DevHealthStatus, DevInfoResponse
from app.services.docker_health_service import list_stack_containers
from app.services.health_service import ComponentHealth, ComponentStatus, check_readiness

logger = logging.getLogger(__name__)
_STARTED_AT_MONOTONIC = time.monotonic()
_TCP_TIMEOUT_SECONDS = 2.0
# Compose service name + container port (quickstart, Dockge, Dockhand, prod).
_COMPOSE_WEB_HOST = "web"
_COMPOSE_WEB_PORT = 3000
_COMPOSE_WORKER_HOST = "worker"
_COMPOSE_DB_HOSTS = {"postgres", "correlcore-postgres"}


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


def _tcp_probe_sync(host: str, port: int) -> tuple[ComponentStatus | None, str]:
    """TCP connect with a short timeout.

    Returns ``(None, "unresolved")`` when the hostname is not in DNS — typical
    for local uvicorn without the Compose network. Callers decide whether to
    omit that service or treat it as down.
    """
    try:
        with socket.create_connection((host, port), timeout=_TCP_TIMEOUT_SECONDS):
            return ComponentStatus.OK, ""
    except socket.gaierror:
        return None, "unresolved"
    except Exception as exc:
        logger.warning("dev tcp probe %s:%s failed: %s", host, port, type(exc).__name__)
        return ComponentStatus.DOWN, type(exc).__name__


def _status_value(status: ComponentStatus) -> DevHealthStatus:
    if status == ComponentStatus.OK:
        return "ok"
    if status == ComponentStatus.DEGRADED:
        return "degraded"
    return "down"


def _from_readiness(component: ComponentHealth) -> DevHealthComponent:
    return DevHealthComponent(
        name=component.name,
        status=_status_value(component.status),
        detail=component.detail,
    )


def _probe_minio_sync() -> DevHealthComponent:
    host, port = _minio_endpoint_host_port()
    status, detail = _tcp_probe_sync(host, port)
    if status is None:
        return DevHealthComponent(name="minio", status="down", detail=detail)
    return DevHealthComponent(name="minio", status=_status_value(status), detail=detail)


def _database_hostname() -> str:
    raw = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    return (urlparse(raw).hostname or "").lower()


def _running_on_compose_network() -> bool:
    return _database_hostname() in _COMPOSE_DB_HOSTS


def _probe_web_sync() -> DevHealthComponent | None:
    status, detail = _tcp_probe_sync(_COMPOSE_WEB_HOST, _COMPOSE_WEB_PORT)
    if status is None:
        if _running_on_compose_network():
            return DevHealthComponent(name="web", status="down", detail="stopped")
        return None
    return DevHealthComponent(name="web", status=_status_value(status), detail=detail)


def _probe_worker_sync() -> DevHealthComponent | None:
    """Compose-only: DNS for ``worker``. Unresolved means the container stopped."""
    if not _running_on_compose_network():
        return None
    try:
        socket.getaddrinfo(_COMPOSE_WORKER_HOST, None)
        return DevHealthComponent(name="worker", status="ok", detail="resolved")
    except socket.gaierror:
        return DevHealthComponent(name="worker", status="down", detail="stopped")


def _probe_smtp_sync() -> DevHealthComponent | None:
    host = settings.SMTP_HOST.strip()
    if not host:
        return None
    name = "mailpit" if host in {"mailpit", "correlcore-mailpit"} else "smtp"
    status, detail = _tcp_probe_sync(host, settings.SMTP_PORT)
    if status is None:
        return DevHealthComponent(name=name, status="down", detail=detail)
    return DevHealthComponent(name=name, status=_status_value(status), detail=detail)


async def _collect_optional_probes() -> tuple[
    DevHealthComponent,
    DevHealthComponent | None,
    DevHealthComponent | None,
    DevHealthComponent | None,
]:
    minio, web, smtp, worker = await asyncio.gather(
        asyncio.to_thread(_probe_minio_sync),
        asyncio.to_thread(_probe_web_sync),
        asyncio.to_thread(_probe_smtp_sync),
        asyncio.to_thread(_probe_worker_sync),
    )
    return minio, web, smtp, worker


async def build_dev_info(db: AsyncSession) -> DevInfoResponse:
    readiness, migration_head, optional, containers = await asyncio.gather(
        check_readiness(),
        _db_migration_head(db),
        _collect_optional_probes(),
        asyncio.to_thread(list_stack_containers),
    )
    minio_component, web_component, smtp_component, worker_component = optional
    redis_connected = any(
        component.name == "redis" and component.status == ComponentStatus.OK
        for component in readiness.components
    )
    minio_connected = minio_component.status == "ok"
    health_components: list[DevHealthComponent] = [
        DevHealthComponent(name="api", status="ok", detail="process"),
        *[_from_readiness(component) for component in readiness.components],
    ]
    if web_component is not None:
        health_components.append(web_component)
    if worker_component is not None:
        health_components.append(worker_component)
    health_components.append(minio_component)
    if smtp_component is not None:
        health_components.append(smtp_component)
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
        health_components=health_components,
        containers=containers,
    )

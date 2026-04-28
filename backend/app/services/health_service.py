"""Health check service — probes external dependencies.

Design constraints (DESIGN_DOCUMENT.md §3.6):
- ``check_liveness`` must never fail due to DB/Redis issues.
  It only confirms the API process itself is alive.
- ``check_readiness`` confirms that all required external deps are reachable.
  A 503 from this endpoint tells Traefik/Uptime-Kuma the service is not ready.

Privacy note: no user data of any kind is read here — only
connectivity/ping-level checks are performed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

logger = logging.getLogger(__name__)


class ComponentStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class ComponentHealth:
    name: str
    status: ComponentStatus
    detail: str = ""


@dataclass
class ReadinessReport:
    ready: bool
    components: list[ComponentHealth] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "ready" if self.ready else "not_ready"


# ---------------------------------------------------------------------------
# Liveness — process-only, no I/O
# ---------------------------------------------------------------------------

def check_liveness() -> dict[str, str]:
    """Returns immediately — only confirms the process is alive."""
    return {"status": "ok", "version": settings.APP_VERSION}


# ---------------------------------------------------------------------------
# Readiness — probes DB and Redis
# ---------------------------------------------------------------------------

async def check_readiness() -> ReadinessReport:
    components: list[ComponentHealth] = []

    # --- PostgreSQL ---
    db_health = await _probe_postgres()
    components.append(db_health)

    # --- Redis ---
    redis_health = await _probe_redis()
    components.append(redis_health)

    ready = all(c.status == ComponentStatus.OK for c in components)
    return ReadinessReport(ready=ready, components=components)


async def _probe_postgres() -> ComponentHealth:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return ComponentHealth(name="postgres", status=ComponentStatus.OK)
    except Exception as exc:
        logger.warning("postgres readiness probe failed: %s", type(exc).__name__)
        return ComponentHealth(
            name="postgres",
            status=ComponentStatus.DOWN,
            detail=type(exc).__name__,
        )


async def _probe_redis() -> ComponentHealth:
    try:
        import redis.asyncio as aioredis  # type: ignore[import-untyped]

        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return ComponentHealth(name="redis", status=ComponentStatus.OK)
    except Exception as exc:
        logger.warning("redis readiness probe failed: %s", type(exc).__name__)
        return ComponentHealth(
            name="redis",
            status=ComponentStatus.DOWN,
            detail=type(exc).__name__,
        )

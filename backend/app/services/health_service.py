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
from collections.abc import Awaitable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, cast

from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import settings
from app.core.crypto import generate_dek, unwrap_dek, wrap_dek
from app.db.session import engine

logger = logging.getLogger(__name__)


class ComponentStatus(StrEnum):
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

    # --- Encryption (Master-Fernet roundtrip, ADR-0005 / SA-5) ---
    encryption_health = _probe_encryption()
    components.append(encryption_health)

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
        client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await cast(Awaitable[Any], client.ping())
        await client.aclose()
        return ComponentHealth(name="redis", status=ComponentStatus.OK)
    except Exception as exc:
        logger.warning("redis readiness probe failed: %s", type(exc).__name__)
        return ComponentHealth(
            name="redis",
            status=ComponentStatus.DOWN,
            detail=type(exc).__name__,
        )


def _probe_encryption() -> ComponentHealth:
    """Verify the master encryption key is present and Fernet-conformant.

    Without this probe a misconfigured/rotated master key would let
    ``/health/ready`` return ``200`` while every authenticated request
    silently 401s on DEK unwrap. Mirrors the production code path:
    generate a fresh DEK, wrap it with the master ``MultiFernet``,
    unwrap it again, and assert byte-equality.

    Synchronous because ``cryptography``'s Fernet is CPU-bound and the
    operation finishes in microseconds — no need to schedule it on the
    event loop.

    Logs only the exception class name (ADR-0007) and never the
    plaintext or ciphertext bytes.
    """
    try:
        sample_dek = generate_dek()
        wrapped = wrap_dek(sample_dek)
        unwrapped = unwrap_dek(wrapped)
        if unwrapped != sample_dek:
            logger.warning("encryption readiness probe: roundtrip mismatch")
            return ComponentHealth(
                name="encryption",
                status=ComponentStatus.DOWN,
                detail="roundtrip_mismatch",
            )
        return ComponentHealth(name="encryption", status=ComponentStatus.OK)
    except Exception as exc:
        logger.warning("encryption readiness probe failed: %s", type(exc).__name__)
        return ComponentHealth(
            name="encryption",
            status=ComponentStatus.DOWN,
            detail=type(exc).__name__,
        )

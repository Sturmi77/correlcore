"""Integration smoke for readiness against real CI services.

This is opt-in locally because it needs PostgreSQL and Redis. CI enables it
with CORRELCORE_RUN_INTEGRATION=1 after starting service containers.
"""

from __future__ import annotations

import os

import pytest

from app.services.health_service import ComponentStatus, check_readiness


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readiness_ok_with_real_postgres_redis_and_encryption() -> None:
    if os.getenv("CORRELCORE_RUN_INTEGRATION") != "1":
        pytest.skip("requires real PostgreSQL and Redis services")

    report = await check_readiness()

    assert report.ready is True
    assert report.status == "ready"
    assert {component.name for component in report.components} == {
        "postgres",
        "redis",
        "encryption",
    }
    assert all(component.status == ComponentStatus.OK for component in report.components)

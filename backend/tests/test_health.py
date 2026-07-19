"""Tests for all health check endpoints.

Coverage:
- GET /health/live       → always 200, no external deps
- GET /health/ready      → 200 when deps ok, 503 when deps down
- GET /health            → always 200, aggregated summary
- GET /api/v1/health/live
- GET /api/v1/health/ready
- GET /api/v1/health
- X-Request-ID propagation
- Docs hidden in production
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.health_service import ComponentHealth, ComponentStatus, ReadinessReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_report() -> ReadinessReport:
    return ReadinessReport(
        ready=True,
        components=[
            ComponentHealth(name="postgres", status=ComponentStatus.OK),
            ComponentHealth(name="redis", status=ComponentStatus.OK),
        ],
    )


def _down_report() -> ReadinessReport:
    return ReadinessReport(
        ready=False,
        components=[
            ComponentHealth(
                name="postgres",
                status=ComponentStatus.DOWN,
                detail="OperationalError",
            ),
            ComponentHealth(name="redis", status=ComponentStatus.OK),
        ],
    )


# ---------------------------------------------------------------------------
# Root shortcuts (used by Docker HEALTHCHECK)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_root_health_live_200() -> None:
    """GET /health/live must return 200 regardless of external deps."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_root_health_200() -> None:
    """GET /health (legacy root) must return 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# /api/v1/health/live
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_v1_health_live_200() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    # Effective Secure-Flag as loaded by this process — ops use this to
    # detect "COOKIE_SECURE only in host .env" (never reached the container).
    assert "cookie_secure" in data
    assert isinstance(data["cookie_secure"], bool)
    assert "app_env" in data


@pytest.mark.asyncio
async def test_liveness_does_not_fail_when_db_is_down() -> None:
    """Liveness must return 200 even when the DB probe would fail."""
    # We don't even call check_readiness — liveness is purely in-process
    with patch(
        "app.services.health_service.check_readiness",
        new_callable=AsyncMock,
        return_value=_down_report(),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/live")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/v1/health/ready
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_v1_health_ready_200_when_deps_ok() -> None:
    with patch(
        "app.api.v1.endpoints.health.check_readiness",
        new_callable=AsyncMock,
        return_value=_ok_report(),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert all(c["status"] == "ok" for c in data["components"])


@pytest.mark.asyncio
async def test_api_v1_health_ready_503_when_db_down() -> None:
    """Readiness must return 503 when a dependency is down."""
    with patch(
        "app.api.v1.endpoints.health.check_readiness",
        new_callable=AsyncMock,
        return_value=_down_report(),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    postgres = next(c for c in data["components"] if c["name"] == "postgres")
    assert postgres["status"] == "down"


# ---------------------------------------------------------------------------
# /api/v1/health (summary)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_v1_health_summary_200_always() -> None:
    """Summary endpoint must always return 200."""
    with patch(
        "app.api.v1.endpoints.health.check_readiness",
        new_callable=AsyncMock,
        return_value=_down_report(),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_api_v1_health_summary_ok_when_all_up() -> None:
    with patch(
        "app.api.v1.endpoints.health.check_readiness",
        new_callable=AsyncMock,
        return_value=_ok_report(),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# X-Request-ID propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_id_header_returned() -> None:
    """Every response must carry X-Request-ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_client_request_id_is_echoed() -> None:
    """If client sends X-Request-ID it must be echoed back unchanged."""
    custom_id = "my-trace-abc-123"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live", headers={"X-Request-ID": custom_id})
    assert response.headers.get("x-request-id") == custom_id


# ---------------------------------------------------------------------------
# Docs hidden in production
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_docs_hidden_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAPI docs must be disabled when DEBUG=False."""
    from app.core import config

    monkeypatch.setattr(config.settings, "DEBUG", False)
    from app.main import create_app

    prod_app = create_app()
    async with AsyncClient(transport=ASGITransport(app=prod_app), base_url="http://test") as client:
        resp = await client.get("/api/openapi.json")
    assert resp.status_code == 404

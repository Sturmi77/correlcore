"""Tests for the health check endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_root() -> None:
    """GET /health should return 200 with status=ok."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_api_v1() -> None:
    """GET /api/v1/health should also return 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_docs_hidden_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAPI docs must be disabled when DEBUG=False."""
    from app.core import config
    monkeypatch.setattr(config.settings, "DEBUG", False)
    # Re-create app to pick up setting
    from app.main import create_app
    prod_app = create_app()
    async with AsyncClient(transport=ASGITransport(app=prod_app), base_url="http://test") as client:
        resp = await client.get("/api/openapi.json")
    assert resp.status_code == 404

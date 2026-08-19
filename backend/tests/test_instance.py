"""Tests for the public instance descriptor endpoint (#734/#735).

GET /api/v1/instance → { mode, registration_enabled, version }, public.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_instance_defaults_to_selfhost() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/instance")
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "selfhost"
    assert body["registration_enabled"] is True
    assert isinstance(body["version"], str) and body["version"]


@pytest.mark.asyncio
async def test_instance_reports_hosted_mode() -> None:
    with (
        patch("app.api.v1.endpoints.instance.settings.DEPLOYMENT_MODE", "hosted"),
        patch("app.api.v1.endpoints.instance.settings.REGISTRATION_ENABLED", True),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/instance")
    assert res.status_code == 200
    assert res.json()["mode"] == "hosted"


@pytest.mark.asyncio
async def test_instance_reports_closed_registration() -> None:
    with patch("app.api.v1.endpoints.instance.settings.REGISTRATION_ENABLED", False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/instance")
    assert res.status_code == 200
    assert res.json()["registration_enabled"] is False

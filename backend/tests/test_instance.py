"""Tests for the public instance descriptor endpoint (#734/#735).

GET /api/v1/instance includes mode and immutable release identity, public.
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
    assert body["git_commit"] == "unknown"
    assert body["api_image"] == ""
    assert body["web_image"] == ""


@pytest.mark.asyncio
async def test_instance_reports_immutable_release_identity() -> None:
    with (
        patch("app.api.v1.endpoints.instance.settings.GIT_COMMIT", "a" * 40),
        patch(
            "app.api.v1.endpoints.instance.settings.IMAGE_DIGEST",
            f"ghcr.io/example/api@sha256:{'b' * 64}",
        ),
        patch(
            "app.api.v1.endpoints.instance.settings.WEB_IMAGE_DIGEST",
            f"ghcr.io/example/web@sha256:{'c' * 64}",
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/instance")

    assert res.status_code == 200
    assert res.json()["git_commit"] == "a" * 40
    assert res.json()["api_image"].endswith("b" * 64)
    assert res.json()["web_image"].endswith("c" * 64)


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

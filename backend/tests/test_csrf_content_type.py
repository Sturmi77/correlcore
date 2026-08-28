"""Tests for the Content-Type CSRF gate (audit M12, ADR-0006).

The middleware rejects state-changing requests whose body is not
``application/json`` (with ``multipart/form-data`` as the documented exception
for media uploads). It runs before routing, so a rejected request never reaches
the endpoint — these tests therefore assert the gate's behavior independently of
any endpoint's own validation, using the unauthenticated ``/auth/register`` POST
route as a convenient target.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.csrf import _media_type

_REGISTER = "/api/v1/auth/register"


def test_media_type_strips_parameters_and_casing() -> None:
    assert _media_type("application/json; charset=utf-8") == "application/json"
    assert _media_type("APPLICATION/JSON") == "application/json"
    assert _media_type("  multipart/form-data ; boundary=x") == "multipart/form-data"
    assert _media_type("") == ""


@pytest.mark.asyncio
async def test_rejects_text_plain_body(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        _REGISTER,
        content=b'{"email": "a@b.co"}',
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 415
    assert "Content-Type" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_rejects_form_urlencoded_body(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        _REGISTER,
        data={"email": "a@b.co", "password": "x"},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_allows_multipart_form_data(async_client: AsyncClient) -> None:
    """Documented exception for authenticated media uploads — gate must pass."""
    resp = await async_client.post(
        _REGISTER,
        files={"file": ("x.txt", b"data", "text/plain")},
    )
    # Not blocked by the CSRF gate; the endpoint itself rejects the shape (422).
    assert resp.status_code != 415


@pytest.mark.asyncio
async def test_allows_application_json_body(async_client: AsyncClient) -> None:
    resp = await async_client.post(_REGISTER, json={"unexpected": "shape"})
    assert resp.status_code != 415


@pytest.mark.asyncio
async def test_allows_bodiless_mutation(async_client: AsyncClient) -> None:
    """Bodiless POST (no Content-Type) carries no form payload — allowed."""
    resp = await async_client.post(_REGISTER)
    assert resp.status_code != 415


@pytest.mark.asyncio
async def test_get_requests_are_not_gated(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.status_code == 200

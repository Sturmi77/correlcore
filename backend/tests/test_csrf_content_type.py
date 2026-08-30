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
async def test_rejects_multipart_on_non_upload_route(async_client: AsyncClient) -> None:
    """#791: multipart is only allowed on the media-upload route, not everywhere.

    A cross-site HTML form can post ``multipart/form-data`` without a preflight,
    so allowing it globally would re-open form-CSRF on every mutating route.
    """
    resp = await async_client.post(
        _REGISTER,
        files={"file": ("x.txt", b"data", "text/plain")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_allows_multipart_on_media_upload_route(async_client: AsyncClient) -> None:
    """The scoped exception: multipart passes the gate on POST /media/photos."""
    resp = await async_client.post(
        "/api/v1/media/photos",
        files={"file": ("x.jpg", b"data", "image/jpeg")},
    )
    # Not blocked by the CSRF gate; the route rejects on auth (401/403), not 415.
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
async def test_rejects_body_with_empty_content_type(async_client: AsyncClient) -> None:
    """#791: a body with no declared media type must not bypass the gate.

    A CORS-safelisted ``fetch(url, {method: "POST", credentials: "include"})``
    sends a body and no Content-Type, and reaches here without a preflight.
    """
    resp = await async_client.post(_REGISTER, content=b'{"email": "a@b.co"}')
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_get_requests_are_not_gated(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.status_code == 200


def test_request_has_body_detects_content_length() -> None:
    from starlette.requests import Request

    from app.core.csrf import _request_has_body

    def _req(headers: dict[str, str]) -> Request:
        raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        return Request({"type": "http", "headers": raw})

    assert _request_has_body(_req({"content-length": "5"})) is True
    assert _request_has_body(_req({"content-length": "0"})) is False
    assert _request_has_body(_req({})) is False
    assert _request_has_body(_req({"transfer-encoding": "chunked"})) is True
    # Malformed length → fail closed (treat as body present).
    assert _request_has_body(_req({"content-length": "abc"})) is True

"""Tests for media photo upload endpoint (Issue #28, M13 foundation)."""

from __future__ import annotations

from io import BytesIO

import pytest
from httpx import AsyncClient
from PIL import Image

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.user import User


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (10, 10), color=(10, 20, 30)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_photo_requires_auth(async_client: AsyncClient) -> None:
    files = {"file": ("photo.jpg", _jpeg_bytes(), "image/jpeg")}
    response = await async_client.post("/api/v1/media/photos", files=files)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_photo_strips_and_returns_metadata(
    async_client: AsyncClient,
    user: User,
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        files = {"file": ("photo.jpg", _jpeg_bytes(), "image/jpeg")}
        response = await async_client.post(
            "/api/v1/media/photos",
            files=files,
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["exif_stripped"] is True
    assert body["stored"] is False
    assert body["width"] == 10
    assert body["height"] == 10
    assert len(body["content_hash"]) == 64


@pytest.mark.asyncio
async def test_upload_photo_rejects_unsupported_type(
    async_client: AsyncClient,
    user: User,
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        response = await async_client.post(
            "/api/v1/media/photos",
            files={"file": ("notes.txt", b"hello", "text/plain")},
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415


def _solid_png(width: int, height: int) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color=(1, 2, 3)).save(
        buf, format="PNG", compress_level=9
    )
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_photo_rejects_oversized_dimensions(
    async_client: AsyncClient,
    user: User,
) -> None:
    """Byte-capped decompression bombs must not reach full EXIF decode."""
    bomb = _solid_png(7000, 7000)
    assert len(bomb) < 10 * 1024 * 1024

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        response = await async_client.post(
            "/api/v1/media/photos",
            files={"file": ("bomb.png", bomb, "image/png")},
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413
    assert response.json()["detail"] == "image dimensions too large"

"""Photo media endpoints — M13 foundation stub (Issue #28).

Accepts authenticated uploads, strips EXIF server-side, and returns metadata.
Object storage (MinIO) is intentionally a no-op until M13 wires a real client.
Product status: deferred — see ``docs/M13_NOTES.md``. Do not treat
``stored=false`` responses as a shipped gallery feature.
"""

from __future__ import annotations

import hashlib
import logging
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from PIL import Image

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.media import PhotoUploadResponse
from app.services.exif_strip import ImageTooLargeError, strip_exif

logger = logging.getLogger(__name__)

router = APIRouter()

_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)
_MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MiB guard rail for foundation stub
_READ_CHUNK_BYTES = 64 * 1024


async def _read_upload_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload in chunks and reject early once ``max_bytes`` is exceeded."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="file too large",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "/photos",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo (EXIF stripped; storage noop until M13)",
)
@limiter.limit("30/minute")
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_verified_user),
) -> PhotoUploadResponse:
    """Accept a photo upload, strip metadata, return sanitized metadata.

    MinIO persistence is deferred — this endpoint establishes the security
    contract (server-side EXIF strip before any future storage write).
    """
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="unsupported image content type",
        )

    raw = await _read_upload_capped(file, _MAX_PHOTO_BYTES)
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty upload")

    try:
        stripped = strip_exif(raw)
        with Image.open(BytesIO(stripped)) as img:
            width, height = img.size
    except ImageTooLargeError as exc:
        logger.warning(
            "media.photo.dimensions_too_large",
            extra={"user_id": str(user.id), "error": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="image dimensions too large",
        ) from exc
    except Exception as exc:
        logger.warning(
            "media.photo.invalid_image",
            extra={"user_id": str(user.id), "error": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid image payload",
        ) from exc

    content_hash = hashlib.sha256(stripped).hexdigest()
    logger.info(
        "media.photo.accepted",
        extra={
            "user_id": str(user.id),
            "size_bytes": len(stripped),
            "content_hash": content_hash,
        },
    )

    return PhotoUploadResponse(
        content_hash=content_hash,
        content_type=content_type,
        size_bytes=len(stripped),
        width=width,
        height=height,
        exif_stripped=True,
        stored=False,
    )

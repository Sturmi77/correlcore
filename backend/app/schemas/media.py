"""Response schemas for media upload endpoints (M13 foundation, Issue #28)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PhotoUploadResponse(BaseModel):
    """Metadata returned after a photo upload is accepted and sanitized."""

    content_hash: str = Field(description="SHA-256 hex digest of stripped bytes")
    content_type: str
    size_bytes: int = Field(ge=0)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    exif_stripped: bool = True
    stored: bool = Field(
        default=False,
        description="Whether bytes were persisted to object storage (noop in M13 foundation)",
    )

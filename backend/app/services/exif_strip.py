"""Server-side EXIF/metadata strip for photo uploads (Issue #28, M13 foundation).

Photos may carry GPS coordinates and other Art.-9-relevant metadata in EXIF.
This module re-encodes image bytes without ancillary metadata before any storage
step (MinIO upload is deferred; see ``POST /api/v1/media/photos`` stub).
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image

_SUPPORTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF"})

# Guard decompression bombs: compressed uploads can declare huge dimensions
# while staying under the HTTP byte cap. ``strip_exif`` fully decodes and
# duplicates pixel buffers, so reject oversized frames before ``load()``.
_MAX_IMAGE_DIMENSION = 8192
_MAX_IMAGE_PIXELS = 25_000_000  # ~25 MP — covers high-end phone stills


class ImageTooLargeError(ValueError):
    """Raised when decoded image dimensions exceed safe processing limits."""


def _reject_oversized(size: tuple[int, int]) -> None:
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError("invalid image dimensions")
    if width > _MAX_IMAGE_DIMENSION or height > _MAX_IMAGE_DIMENSION:
        raise ImageTooLargeError(
            f"image dimension exceeds {_MAX_IMAGE_DIMENSION}px limit"
        )
    if width * height > _MAX_IMAGE_PIXELS:
        raise ImageTooLargeError(
            f"image pixel count exceeds {_MAX_IMAGE_PIXELS} limit"
        )


def strip_exif(image_bytes: bytes) -> bytes:
    """Return ``image_bytes`` re-encoded without EXIF/IPTC/XMP metadata."""
    with Image.open(BytesIO(image_bytes)) as src:
        # Header-only size check — must run before load()/putdata().
        _reject_oversized(src.size)
        src.load()
        fmt = (src.format or "JPEG").upper()
        if fmt not in _SUPPORTED_FORMATS:
            fmt = "JPEG"

        clean = Image.new(src.mode, src.size)
        clean.putdata(src.get_flattened_data())
        if src.mode == "P" and src.palette is not None:
            clean.putpalette(src.palette)

        if fmt == "JPEG" and clean.mode in ("RGBA", "P"):
            clean = clean.convert("RGB")

        out = BytesIO()
        save_kwargs: dict[str, object] = {}
        if fmt == "JPEG":
            save_kwargs["quality"] = 95
        clean.save(out, format=fmt, **save_kwargs)
        return out.getvalue()


__all__ = ["ImageTooLargeError", "strip_exif"]

"""Server-side EXIF/metadata strip for photo uploads (Issue #28, M13 foundation).

Photos may carry GPS coordinates and other Art.-9-relevant metadata in EXIF.
This module re-encodes image bytes without ancillary metadata before any storage
step (MinIO upload is deferred; see ``POST /api/v1/media/photos`` stub).
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image

_SUPPORTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF"})


def strip_exif(image_bytes: bytes) -> bytes:
    """Return ``image_bytes`` re-encoded without EXIF/IPTC/XMP metadata."""
    with Image.open(BytesIO(image_bytes)) as src:
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


__all__ = ["strip_exif"]

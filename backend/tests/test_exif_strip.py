"""Tests for server-side EXIF strip (Issue #28, M13 foundation)."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image, UnidentifiedImageError
from PIL.TiffImagePlugin import IFDRational

from app.services.exif_strip import ImageTooLargeError, strip_exif

_GPS_IFD_TAG = 0x8825


def _jpeg_with_gps_exif() -> bytes:
    """Build a tiny JPEG carrying synthetic GPS EXIF via Pillow."""
    img = Image.new("RGB", (12, 12), color=(40, 80, 120))
    exif = Image.Exif()
    exif[0x010E] = "synthetic caption"
    exif[_GPS_IFD_TAG] = {
        1: "N",
        2: (IFDRational(48, 1), IFDRational(8, 1), IFDRational(52, 1)),
        3: "E",
        4: (IFDRational(11, 1), IFDRational(34, 1), IFDRational(56, 1)),
    }
    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def _has_gps_exif(image_bytes: bytes) -> bool:
    with Image.open(BytesIO(image_bytes)) as img:
        exif = img.getexif()
        if not exif:
            return False
        gps_ifd = exif.get_ifd(_GPS_IFD_TAG)
        return bool(gps_ifd)


def test_strip_exif_removes_gps_metadata() -> None:
    original = _jpeg_with_gps_exif()
    assert _has_gps_exif(original)

    stripped = strip_exif(original)
    assert stripped
    assert stripped != original or not _has_gps_exif(stripped)
    assert _has_gps_exif(stripped) is False


def test_strip_exif_clean_image_still_valid() -> None:
    buf = BytesIO()
    Image.new("RGB", (16, 16), color=(200, 100, 50)).save(buf, format="JPEG")
    original = buf.getvalue()
    assert _has_gps_exif(original) is False

    stripped = strip_exif(original)
    with Image.open(BytesIO(stripped)) as img:
        assert img.size == (16, 16)
        assert img.format == "JPEG"


def test_strip_exif_rejects_invalid_bytes() -> None:
    with pytest.raises(UnidentifiedImageError):
        strip_exif(b"not-an-image")


def _solid_png(width: int, height: int) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color=(1, 2, 3)).save(buf, format="PNG", compress_level=9)
    return buf.getvalue()


def test_strip_exif_rejects_oversized_dimensions() -> None:
    """Compressed huge frames must fail before full decode (decompression bomb)."""
    original = _solid_png(9000, 100)
    assert len(original) < 10 * 1024 * 1024

    with pytest.raises(ImageTooLargeError, match="dimension"):
        strip_exif(original)


def test_strip_exif_rejects_oversized_pixel_count() -> None:
    # 6000×6000 = 36 MP > 25 MP pixel cap; each side under the 8192 dim cap.
    original = _solid_png(6000, 6000)
    assert len(original) < 10 * 1024 * 1024

    with pytest.raises(ImageTooLargeError, match="pixel count"):
        strip_exif(original)


def test_strip_exif_accepts_high_end_phone_resolution() -> None:
    # ~12 MP still (4032×3024) must remain processable.
    original = _solid_png(4032, 3024)
    stripped = strip_exif(original)
    with Image.open(BytesIO(stripped)) as img:
        assert img.size == (4032, 3024)

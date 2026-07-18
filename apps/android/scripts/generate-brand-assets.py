#!/usr/bin/env python3
"""Generate launcher icons + splash PNGs from the CorrelCore brand palette.

Uses the same 3×3 grid motif as apps/web/static/icons/icon.svg.
Run from repo: python3 apps/android/scripts/generate-brand-assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

BRAND = (0x7C, 0x6A, 0xF5, 255)
WHITE = (255, 255, 255, 255)
RES = Path(__file__).resolve().parents[1] / "android" / "app" / "src" / "main" / "res"

# Opacity steps matching icon.svg (0.9 … 1.0 on the last cell)
CELL_OPACITY = [
    [0.9, 0.7, 0.5],
    [0.7, 0.5, 0.3],
    [0.5, 0.3, 1.0],
]

MIPMAP_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

FOREGROUND_SIZES = {
    "mipmap-mdpi": 108,
    "mipmap-hdpi": 162,
    "mipmap-xhdpi": 216,
    "mipmap-xxhdpi": 324,
    "mipmap-xxxhdpi": 432,
}

SPLASH_SIZES = {
    "drawable": (480, 800),
    "drawable-port-mdpi": (320, 480),
    "drawable-port-hdpi": (480, 800),
    "drawable-port-xhdpi": (720, 1280),
    "drawable-port-xxhdpi": (1080, 1920),
    "drawable-port-xxxhdpi": (1440, 2560),
    "drawable-land-mdpi": (480, 320),
    "drawable-land-hdpi": (800, 480),
    "drawable-land-xhdpi": (1280, 720),
    "drawable-land-xxhdpi": (1920, 1080),
    "drawable-land-xxxhdpi": (2560, 1440),
}


def draw_grid_icon(size: int, *, rounded: bool) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Background rounded square
    radius = int(size * 112 / 512)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=BRAND)

    cell = size * 96 / 512
    gap_origin = size * 96 / 512
    step = size * 112 / 512
    corner = max(1, int(size * 20 / 512))

    for row in range(3):
        for col in range(3):
            x0 = gap_origin + col * step
            y0 = gap_origin + row * step
            alpha = int(255 * CELL_OPACITY[row][col])
            fill = (255, 255, 255, alpha)
            draw.rounded_rectangle(
                (x0, y0, x0 + cell, y0 + cell),
                radius=corner,
                fill=fill,
            )

    if rounded:
        # Soft circular mask for round launcher
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(img, mask=mask)
        return out
    return img


def draw_adaptive_foreground(size: int) -> Image.Image:
    """Foreground layer for adaptive icons (safe zone ~66% center)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Place grid in the safe zone
    inset = int(size * 0.18)
    inner = size - 2 * inset
    grid = draw_grid_icon(inner, rounded=False)
    # Strip background — keep only white cells on transparent
    pixels = grid.load()
    for y in range(inner):
        for x in range(inner):
            r, g, b, a = pixels[x, y]
            if (r, g, b) == BRAND[:3]:
                pixels[x, y] = (0, 0, 0, 0)
    img.paste(grid, (inset, inset), grid)
    return img


def main() -> None:
    for folder, size in MIPMAP_SIZES.items():
        out_dir = RES / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        draw_grid_icon(size, rounded=False).save(out_dir / "ic_launcher.png")
        draw_grid_icon(size, rounded=True).save(out_dir / "ic_launcher_round.png")

    for folder, size in FOREGROUND_SIZES.items():
        out_dir = RES / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        draw_adaptive_foreground(size).save(out_dir / "ic_launcher_foreground.png")

    for folder, (w, h) in SPLASH_SIZES.items():
        out_dir = RES / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (w, h), BRAND).save(out_dir / "splash.png")

    print(f"Wrote brand assets under {RES}")


if __name__ == "__main__":
    main()

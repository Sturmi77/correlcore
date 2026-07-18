#!/usr/bin/env python3
"""Generate launcher icons + splash PNGs from Claude Design brand assets.

Sources (web static, after Logo PR):
  - apps/web/static/icons/correlcore-app-icon.png        (rounded 144²)
  - apps/web/static/icons/correlcore-icon-dark-bg.png    (512² plate)
  - apps/web/static/icons/correlcore-logo-mark-dark.svg  (mark colors)

Run: pnpm --filter @correlcore/android assets:brand
  or: python3 apps/android/scripts/generate-brand-assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[3]
WEB_ICONS = REPO / "apps" / "web" / "static" / "icons"
RES = Path(__file__).resolve().parents[1] / "android" / "app" / "src" / "main" / "res"

# Dark app chrome — matches default theme --color-bg and Capacitor SplashScreen.
SPLASH_BG = (0x17, 0x16, 0x14, 255)
# Dark-theme logo-mark fills (correlcore-logo-mark-dark.svg + primary accent).
MARK_FILLS = [
    [(0x1F, 0x2A, 0x44, 255), (0x2E, 0x3F, 0x6F, 255), (0x41, 0x5A, 0xA3, 255)],
    [(0x2E, 0x3F, 0x6F, 255), (0x41, 0x5A, 0xA3, 255), (0x62, 0x79, 0xD6, 255)],
    [(0x41, 0x5A, 0xA3, 255), (0x62, 0x79, 0xD6, 255), (0x95, 0x87, 0xFF, 255)],
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


def load_rgba(path: Path) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(f"Brand source missing: {path}")
    return Image.open(path).convert("RGBA")


def resize_cover(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.Resampling.LANCZOS)


def circular_mask(img: Image.Image) -> Image.Image:
    size = img.size[0]
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return out


def draw_mark(size: int) -> Image.Image:
    """Transparent 3×3 brand mark at the given pixel size (viewBox 36)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    scale = size / 36
    cell = 10 * scale
    step = 13 * scale
    radius = max(1, int(2 * scale))
    for row in range(3):
        for col in range(3):
            x0 = col * step
            y0 = row * step
            draw.rounded_rectangle(
                (x0, y0, x0 + cell - 1, y0 + cell - 1),
                radius=radius,
                fill=MARK_FILLS[row][col],
            )
    return img


# Adaptive-icon safe zone is the center ~66%. OEM masks (Samsung One UI,
# circles) crop harder than the material minimum — keep the mark smaller so
# it does not look oversized / clipped on devices like Galaxy S25.
ADAPTIVE_MARK_INSET = 0.32  # mark ≈ 36% of the 108dp canvas (Samsung-safe)
LEGACY_MARK_RATIO = 0.48  # mark size vs plate for legacy mipmap icons


def draw_adaptive_foreground(size: int) -> Image.Image:
    """Foreground layer for adaptive icons (mark inside OEM-safe center)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inset = int(size * ADAPTIVE_MARK_INSET)
    inner = max(1, size - 2 * inset)
    mark = draw_mark(inner)
    img.paste(mark, (inset, inset), mark)
    return img


def draw_legacy_launcher(size: int, *, rounded: bool) -> Image.Image:
    """Legacy mipmap icon: dark plate + padded mark (not full-bleed export)."""
    img = Image.new("RGBA", (size, size), SPLASH_BG)
    draw = ImageDraw.Draw(img)
    radius = int(size * 112 / 512)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=SPLASH_BG)

    mark_size = max(8, int(size * LEGACY_MARK_RATIO))
    mark = draw_mark(mark_size)
    origin = (size - mark_size) // 2
    img.paste(mark, (origin, origin), mark)

    if rounded:
        return circular_mask(img)
    return img


def draw_splash(width: int, height: int, mark_source: Image.Image) -> Image.Image:
    img = Image.new("RGBA", (width, height), SPLASH_BG)
    mark_size = max(64, int(min(width, height) * 0.22))
    mark = resize_cover(mark_source, mark_size)
    x = (width - mark_size) // 2
    y = (height - mark_size) // 2
    img.paste(mark, (x, y), mark)
    return img


def main() -> None:
    # Keep source check so CI/docs still point at the Claude Design exports.
    _ = load_rgba(WEB_ICONS / "correlcore-app-icon.png")
    _ = load_rgba(WEB_ICONS / "correlcore-icon-dark-bg.png")
    splash_mark = draw_mark(256)

    for folder, size in MIPMAP_SIZES.items():
        out_dir = RES / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        draw_legacy_launcher(size, rounded=False).save(out_dir / "ic_launcher.png")
        draw_legacy_launcher(size, rounded=True).save(out_dir / "ic_launcher_round.png")

    for folder, size in FOREGROUND_SIZES.items():
        out_dir = RES / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        draw_adaptive_foreground(size).save(out_dir / "ic_launcher_foreground.png")

    for folder, (w, h) in SPLASH_SIZES.items():
        out_dir = RES / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        draw_splash(w, h, splash_mark).save(out_dir / "splash.png")

    print(f"Wrote brand assets under {RES}")
    print(
        f"Adaptive mark inset={ADAPTIVE_MARK_INSET:.0%}, "
        f"legacy mark ratio={LEGACY_MARK_RATIO:.0%}"
    )
    print(f"Sources: {WEB_ICONS}")


if __name__ == "__main__":
    main()

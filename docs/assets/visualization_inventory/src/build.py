import importlib
import os
import subprocess
import sys

from PIL import Image

from lib import render_page

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "out")
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
BG = (26, 24, 21)
MAX_H = 880
SCALE = 2

MODULES = sys.argv[2:] or ["mocks_a", "mocks_b", "mocks_c", "mocks_d"]

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(HERE, "shared.css")) as fh:
    css = fh.read()
with open(os.path.join(OUT, "shared.css"), "w") as fh:
    fh.write(css)


def autocrop_bottom(path: str) -> tuple[int, int]:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()
    last = 0
    for y in range(h - 1, -1, -1):
        row_has_content = False
        for x in range(0, w, 4):
            r, g, b = px[x, y]
            if abs(r - BG[0]) > 4 or abs(g - BG[1]) > 4 or abs(b - BG[2]) > 4:
                row_has_content = True
                break
        if row_has_content:
            last = y
            break
    bottom = min(h, last + 16 * SCALE)
    img.crop((0, 0, w, bottom)).save(path)
    return w, bottom


for modname in MODULES:
    try:
        mod = importlib.import_module(modname)
    except ModuleNotFoundError:
        print(f"skip {modname}")
        continue
    for name, fn in mod.MOCKS.items():
        width, body = fn()
        html_path = os.path.join(OUT, name + ".html")
        with open(html_path, "w") as fh:
            fh.write(render_page(width, body))
        png = os.path.join(OUT, name + ".png")
        subprocess.run(
            [CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--force-device-scale-factor={SCALE}", "--virtual-time-budget=1500",
             f"--window-size={width},{MAX_H}",
             f"--screenshot={png}", f"file://{html_path}"],
            capture_output=True, text=True,
        )
        w, h = autocrop_bottom(png)
        warn = "  <-- CLIPPED?" if h >= MAX_H * SCALE - 8 else ""
        print(f"{name}: {w}x{h} ({os.path.getsize(png) // 1024} KiB){warn}")

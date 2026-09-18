"""Shared helpers for the CorrelCore visualization mockups."""

import math
import random

RNG = random.Random(20260917)

HM = ["#1f2a44", "#2e3f6f", "#415aa3", "#6279d6"]
DIVERGENT_NEG = "#3a5a8a"
DIVERGENT_MID = "#2a2825"
DIVERGENT_POS = "#9587ff"


def lerp_hex(a: str, b: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    return "#%02x%02x%02x" % (
        round(ar + (br - ar) * t),
        round(ag + (bg - ag) * t),
        round(ab + (bb - ab) * t),
    )


def divergent(value: float, midpoint: float = 0.0, rng: float = 2.0) -> str:
    """Mirror of StripCellMapper: value -> token colour."""
    t = (value - midpoint) / (rng / 2.0)  # -1 .. 1
    t = max(-1.0, min(1.0, t))
    if t >= 0:
        return lerp_hex(DIVERGENT_MID, DIVERGENT_POS, t)
    return lerp_hex(DIVERGENT_MID, DIVERGENT_NEG, -t)


def heat(level: int) -> str:
    """0 = empty cell, 1..4 = heatmap intensity tokens."""
    if level <= 0:
        return "#232120"
    return HM[min(3, level - 1)]


def series(n: int, base: float, amp: float, period: float, phase: float = 0.0, noise: float = 0.25):
    out = []
    for i in range(n):
        v = base + amp * math.sin((i / period) * 2 * math.pi + phase) + RNG.uniform(-noise, noise)
        out.append(max(1.0, min(5.0, v)))
    return out


def polyline(values, x0, y0, w, h, vmin=1.0, vmax=5.0):
    n = len(values)
    step = w / max(1, n - 1)
    pts = []
    for i, v in enumerate(values):
        x = x0 + i * step
        y = y0 + h - ((v - vmin) / (vmax - vmin)) * h
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def cells_row(values, x0, y0, cell, gap, colour_fn, stroke=None):
    out = []
    for i, v in enumerate(values):
        x = x0 + i * (cell + gap)
        extra = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
        out.append(
            f'<rect x="{x:.1f}" y="{y0:.1f}" width="{cell}" height="{cell}" rx="2.5" '
            f'fill="{colour_fn(v)}"{extra}/>'
        )
    return "".join(out)


import os as _os

with open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "shared.css")) as _fh:
    SHARED_CSS = _fh.read()

def render_page(width: int, body: str) -> str:
    return (
        '<!doctype html><html lang="de"><head><meta charset="utf-8"><style>'
        + SHARED_CSS
        + '</style></head><body><div class="frame" style="width:'
        + str(width)
        + 'px">'
        + body
        + '</div></body></html>'
    )

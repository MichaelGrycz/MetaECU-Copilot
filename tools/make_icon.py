#!/usr/bin/env python3
"""Generate the MetaECU motorsport icon (ICO + PNG set) with Pillow.

Draws a neon-orange turbo/compressor wheel on carbon black: radial turbine
blades, hub, and an orange boost arc. Output:
    assets/metaecu.ico          (16..256 px, Windows)
    backend/static/icon-192.png (PWA)
    backend/static/icon-512.png (PWA)

Usage:
    python tools/make_icon.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]

ORANGE = (255, 122, 24, 255)
ORANGE_DIM = (214, 90, 10, 255)
CYAN = (34, 211, 238, 255)
CARBON = (5, 7, 10, 255)
STEEL = (148, 184, 220, 255)


def render(size: int) -> Image.Image:
    ss = 4  # supersample
    S = size * ss
    img = Image.new("RGBA", (S, S), CARBON)
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    r_out = S * 0.46

    # carbon disc + rim
    d.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=(10, 15, 22, 255))
    d.ellipse(
        [cx - r_out, cy - r_out, cx + r_out, cy + r_out],
        outline=ORANGE,
        width=max(2, S // 42),
    )

    # turbine blades (alternating sweep direction for a machined look)
    blades = 11
    for i in range(blades):
        a0 = (2 * math.pi * i / blades) - 0.42
        r1, r2, w = S * 0.16, S * 0.40, max(2, S // 30)
        x1, y1 = cx + r1 * math.cos(a0), cy + r1 * math.sin(a0)
        x2, y2 = cx + r2 * math.cos(a0), cy + r2 * math.sin(a0)
        x3, y3 = cx + r2 * math.cos(a0 + 0.30), cy + r2 * math.sin(a0 + 0.30)
        d.polygon(
            [(x1, y1), (x2, y2), (x3, y3)],
            fill=STEEL if i % 2 else (104, 140, 180, 255),
        )
        d.line([x1, y1, x2, y2], fill=(200, 225, 250, 255), width=w // 2)

    # hub
    rh = S * 0.15
    d.ellipse(
        [cx - rh, cy - rh, cx + rh, cy + rh],
        fill=(16, 24, 36, 255),
        outline=ORANGE,
        width=max(2, S // 40),
    )
    rb = S * 0.055
    d.ellipse([cx - rb, cy - rb, cx + rb, cy + rb], fill=ORANGE)

    # boost arc (cyan, sweeping past 270deg)
    r_arc = S * 0.435
    d.arc(
        [cx - r_arc, cy - r_arc, cx + r_arc, cy + r_arc],
        start=130,
        end=370,
        fill=CYAN,
        width=max(2, S // 26),
    )
    # needle tip dot at end of boost arc
    a = math.radians(10)
    d.ellipse(
        [
            cx + r_arc * math.cos(a) - S * 0.03,
            cy + r_arc * math.sin(a) - S * 0.03,
            cx + r_arc * math.cos(a) + S * 0.03,
            cy + r_arc * math.sin(a) + S * 0.03,
        ],
        fill=CYAN,
    )
    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    assets = REPO / "assets"
    static = REPO / "backend" / "static"
    assets.mkdir(exist_ok=True)
    ico_path = assets / "metaecu.ico"
    render(256).save(
        ico_path,
        format="ICO",
        sizes=[
            (16, 16),
            (24, 24),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ],
    )
    render(192).save(static / "icon-192.png")
    render(512).save(static / "icon-512.png")
    render(180).save(static / "apple-touch-icon.png")
    print(f"icon -> {ico_path} ({ico_path.stat().st_size} B)")
    print(f"PWA icons -> {static}/icon-192.png, icon-512.png, apple-touch-icon.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

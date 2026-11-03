#!/usr/bin/env python3
"""Build the MetaECU Copilot cinema-grade motion graphics demo video.

Renders high-budget vectorized HTML5/CSS3/Canvas motion graphics (trailer.html)
in Full HD 1080p, multiplexed with warm ambient cinematic music (Dm9 Hans Zimmer style).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.render_motion_graphics_video import render_cinema_video


if __name__ == "__main__":
    success = render_cinema_video()
    sys.exit(0 if success else 1)

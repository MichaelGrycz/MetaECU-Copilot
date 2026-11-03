#!/usr/bin/env python3
"""Build the MetaECU Copilot cinema-grade hackathon demo video.

Delegates directly to tools.build_cinematic_video for full 110-second
Full HD video generation with motorsport sound design, synchronized captions,
and fast-paced cinematic cuts.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_cinematic_video import compile_video


if __name__ == "__main__":
    success = compile_video()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""Build the MetaECU Copilot live-action dynamic hackathon demo video.

Captures real interactive browser actions (Playwright Chromium 1080p),
synchronized with 120-BPM motorsport synthwave soundtrack and unobtrusive
bottom-line captions.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_live_recorded_video import assemble_complete_video


if __name__ == "__main__":
    success = assemble_complete_video()
    sys.exit(0 if success else 1)

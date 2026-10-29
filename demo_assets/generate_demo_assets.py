"""Generate every demo artifact (charts, tuned binary, audit report) for recording.

Usage: python demo_assets/generate_demo_assets.py
Runs the exact pipeline shown on camera, with the 450 Nm rejection moment.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo_assets" / "output"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(ROOT / "main.py"),
        "--intent",
        "Give me 450 Nm, maximum power",
        "--out",
        str(OUT / "metaecu_demo_tuned.bin"),
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())

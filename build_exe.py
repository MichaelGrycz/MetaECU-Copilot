#!/usr/bin/env python3
"""Build the standalone Windows executable: MetaECU_Copilot.exe.

    python build_exe.py            # full build into dist/MetaECU_Copilot.exe
    python build_exe.py --check    # validate inputs, skip the PyInstaller run

The bundle is self-contained (one file, no console window):
  - run_desktop.py as the entry point (pywebview native window)
  - backend/ python package + static cockpit (HTML/PWA/audio FX)
  - staged slim assets (stock .bin, catalogue, telemetry) as metaecu_assets/
  - tools-generated motorsport icon (assets/metaecu.ico)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent


def sep() -> str:
    return ";" if sys.platform.startswith("win") else ":"


def build_command() -> list[str]:
    s = sep()
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noconsole",
        "--onefile",
        "--windowed",
        "--name",
        "MetaECU_Copilot",
        f"--icon={REPO / 'assets' / 'metaecu.ico'}",
        f"--add-data={REPO / 'backend'}{s}backend",
        f"--add-data={REPO / 'build_assets' / 'metaecu_assets'}{s}metaecu_assets",
        "--hidden-import=backend.web_app",
        "--hidden-import=backend.telemetry_cockpit",
        "--hidden-import=backend.voice_ingest",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--collect-submodules=webview",
        str(REPO / "run_desktop.py"),
    ]


INPUTS = [
    REPO / "run_desktop.py",
    REPO / "backend" / "web_app.py",
    REPO / "backend" / "static" / "index.html",
    REPO / "assets" / "metaecu.ico",
    REPO / "build_assets" / "metaecu_assets" / "ASSETS_MANIFEST.txt",
]


def main() -> int:
    missing = [str(p) for p in INPUTS if not p.exists()]
    if missing:
        print("Missing build inputs (run tools/stage_assets.py + tools/make_icon.py):")
        for m in missing:
            print(f"  - {m}")
        return 2
    try:
        import PyInstaller  # noqa: F401
        import webview  # noqa: F401
    except ImportError as exc:
        print(
            f"Missing build dependency: {exc}. Run: pip install pyinstaller pywebview"
        )
        return 2

    cmd = build_command()
    print("Build command:")
    print("  " + " ".join(cmd))
    if "--check" in sys.argv:
        print("CHECK PASS — inputs present, PyInstaller + pywebview importable.")
        return 0

    result = subprocess.run(cmd, cwd=REPO)
    if result.returncode != 0:
        print(f"PyInstaller failed with exit code {result.returncode}.")
        return result.returncode
    exe = REPO / "dist" / "MetaECU_Copilot.exe"
    size_mb = exe.stat().st_size / 1e6 if exe.exists() else 0
    print(f"BUILT: {exe} ({size_mb:.1f} MB)")
    print("Double-click it — the Motorsport Studio opens with no console window.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

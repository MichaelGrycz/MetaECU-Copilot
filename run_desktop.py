#!/usr/bin/env python3
"""MetaECU Copilot — native desktop launcher (no console window).

Starts the FastAPI cockpit on an ephemeral localhost port in a background
thread and opens it in a native pywebview window titled
"MetaECU Copilot — Motorsport Studio". No browser chrome, no CMD window
(when built with build_exe.py --windowed).

Modes:
    python run_desktop.py              # native window (pywebview)
    python run_desktop.py --browser    # system browser fallback
    python run_desktop.py --smoke      # verify the embedded server boots, exit

PyInstaller: when frozen, runtime assets are read from the bundled staging
tree (sys._MEIPASS) and output files go to %TEMP%/metaecu_web.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

WINDOW_TITLE = "MetaECU Copilot — Motorsport Studio"


def _repo_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def configure_environment() -> Path:
    """Point the web app at bundled assets when running frozen / staged."""
    root = _repo_root()
    staged = root / "metaecu_assets"
    if staged.is_dir() and not os.environ.get("METAECU_ASSET_ROOT"):
        os.environ["METAECU_ASSET_ROOT"] = str(staged)
    sys.path.insert(0, str(root))
    return root


def wait_ready(port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/meta", timeout=2
            ) as resp:
                return resp.status == 200
        except Exception:
            time.sleep(0.25)
    return False


def serve(port: int) -> None:
    import uvicorn

    from backend.web_app import app

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    configure_environment()
    port = _free_port()
    thread = threading.Thread(target=serve, args=(port,), daemon=True)
    thread.start()
    if not wait_ready(port):
        print("MetaECU server failed to start.", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{port}/"
    print(f"{WINDOW_TITLE} -> {url}")

    if "--smoke" in argv:
        print("SMOKE PASS: embedded cockpit server is live.")
        if "--hold" in argv:
            # Keep serving until killed (used to HTTP-verify the frozen EXE).
            try:
                while thread.is_alive():
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass
        return 0

    if "--browser" in argv:
        import webbrowser

        webbrowser.open(url)
        try:
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        return 0

    try:
        import webview
    except ImportError:
        print(
            "pywebview is not installed (pip install pywebview). "
            "Falling back to the system browser.",
            file=sys.stderr,
        )
        import webbrowser

        webbrowser.open(url)
        try:
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        return 0

    webview.create_window(
        WINDOW_TITLE,
        url,
        width=1600,
        height=1000,
        min_size=(1100, 700),
        background_color="#05070a",
        text_select=True,
    )
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

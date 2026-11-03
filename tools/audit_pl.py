#!/usr/bin/env python3
"""Audit Polish language rendering on all 5 stages of MetaECU Copilot."""

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "output" / "visual_audit_pl"
BASE = "http://127.0.0.1:8000"


def wait_server(proc: subprocess.Popen, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(BASE + "/api/meta", timeout=2) as r:
                return r.status == 200
        except Exception:
            time.sleep(0.3)
    return False


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [sys.executable, str(REPO / "web_app.py")],
        cwd=REPO,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_server(proc):
            print("server failed to start")
            return 1

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1050})
            errors: list[str] = []
            page.on(
                "console",
                lambda m: errors.append(m.text) if m.type == "error" else None,
            )
            page.on("pageerror", lambda e: errors.append(str(e)))

            page.goto(BASE, wait_until="networkidle")
            page.wait_for_timeout(1000)

            # Switch to Polish
            page.click("#langPL")
            page.wait_for_timeout(1000)

            # View 1: Map Studio PL
            page.screenshot(path=str(OUT / "pl_01_maps_matrix.png"))
            print("saved pl_01_maps_matrix.png")

            # View 2: Intercept PL
            page.click("#btnTune")
            page.wait_for_function(
                "() => document.querySelector('#gateBadge').textContent.includes('PASS') || document.querySelector('#gateBadge').textContent.includes('ZATWIERDZONA')",
                timeout=120000,
            )
            page.wait_for_timeout(2000)
            page.screenshot(path=str(OUT / "pl_02_intercept.png"))
            print("saved pl_02_intercept.png")

            # View 3: Dyno PL
            page.click('[data-tab="dyno"]')
            page.wait_for_timeout(2000)
            page.screenshot(path=str(OUT / "pl_03_dyno.png"))
            print("saved pl_03_dyno.png")

            # View 4: Vision PL
            page.click('[data-tab="vision"]')
            page.wait_for_timeout(1000)
            page.click("#btnLoadSampleDyno")
            page.wait_for_timeout(3000)
            page.screenshot(path=str(OUT / "pl_04_vision.png"))
            print("saved pl_04_vision.png")

            # View 5: Export PL
            page.click('[data-tab="export"]')
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / "pl_05_export.png"))
            print("saved pl_05_export.png")

            browser.close()
            real_errors = [e for e in errors if "favicon" not in e.lower()]
            print(f"PL audit console errors: {len(real_errors)}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())

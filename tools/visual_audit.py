#!/usr/bin/env python3
"""Visual audit of the MetaECU flow-based cockpit (headless Chromium screenshots).

Starts backend/web_app.py and steps through the 5-stage workflow:
  01_stage1_ingest.png     — Stage 1: Vehicle & ECU Ingest
  02_stage2_intent.png     — Stage 2: Calibration Intent & Tuning Presets
  03_stage3_intercept.png  — Stage 3: Deterministic Safety Gate Intercept & Self-Correction
  04_stage4_3d_audit.png   — Stage 4: 3D Map Surface Studio & Road Telemetry
  05_stage5_export.png     — Stage 5: Verified Calibration & Digital Certificate
  06_mobile.png            — Mobile Viewport (430x932)

Usage: python tools/visual_audit.py
"""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "output" / "visual_audit"
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
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "playwright missing: pip install playwright && playwright install chromium"
        )
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    log = open(REPO / "output" / "visual_audit" / "server.log", "w")
    proc = subprocess.Popen(
        [sys.executable, str(REPO / "web_app.py")],
        cwd=REPO,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        if not wait_server(proc):
            print("server failed to start — see output/visual_audit/server.log")
            return 1
        print("server up:", BASE)

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1050})
            errors: list[str] = []
            page.on(
                "console",
                lambda m: errors.append(m.text) if m.type == "error" else None,
            )
            page.on("pageerror", lambda e: errors.append(str(e)))

            # View 1: Map Studio & 2D Matrix Table
            page.goto(BASE, wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / "01_map_studio_matrix.png"))
            print("saved 01_map_studio_matrix.png")

            # View 2: Safety Gate Intercept (450 Nm test)
            page.click("button:has-text('450 Nm INTERCEPT')")
            page.wait_for_function(
                "() => document.querySelector('#gateBadge').textContent.includes('PASS')",
                timeout=120000,
            )
            page.wait_for_timeout(2000)
            page.screenshot(path=str(OUT / "02_safety_intercept_pass.png"))
            print("saved 02_safety_intercept_pass.png")

            # View 3: Dyno Bench & Road Telemetry
            page.click('[data-tab="dyno"]')
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / "03_dyno_telemetry.png"))
            print("saved 03_dyno_telemetry.png")

            # View 4: SAM 3.1 Vision Radar
            page.click('[data-tab="vision"]')
            page.wait_for_timeout(1000)
            page.click("#btnLoadSampleDyno")
            page.wait_for_timeout(3500)
            page.screenshot(path=str(OUT / "04_sam_vision_radar.png"))
            print("saved 04_sam_vision_radar.png")

            # View 5: HIL Flasher & Export
            page.click('[data-tab="export"]')
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / "05_hil_flasher_export.png"))
            print("saved 05_hil_flasher_export.png")

            # Mobile view
            mobile = browser.new_page(viewport={"width": 430, "height": 932})
            mobile.goto(BASE, wait_until="networkidle")
            mobile.wait_for_timeout(2500)
            mobile.screenshot(path=str(OUT / "06_mobile.png"))
            print("saved 06_mobile.png")

            browser.close()
            real_errors = [e for e in errors if "favicon" not in e.lower()]
            print(f"console/page errors: {len(real_errors)}")
            for e in real_errors[:5]:
                print("  -", e[:200])
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())

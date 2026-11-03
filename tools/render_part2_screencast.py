import subprocess
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT / "demo_assets" / "_screencast_tmp"
FRAMES_DIR = TMP_DIR / "frames"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

TOTAL_SEC = 19.5
FPS = 30
TOTAL_FRAMES = round(TOTAL_SEC * FPS) # 585 frames

print("Starting local server for live screencast capture...")
server_proc = subprocess.Popen([sys.executable, str(ROOT / "web_app.py")], cwd=str(ROOT))
time.sleep(3.5)

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.goto("http://127.0.0.1:8000")
        page.wait_for_timeout(1500)

        # Trigger 450 Nm INTERCEPT to have fresh data in the DOM
        print("Triggering 450 Nm INTERCEPT on live UI...")
        page.click("button:has-text('450 Nm INTERCEPT')")
        page.wait_for_timeout(8000)

        print(f"Rendering {TOTAL_FRAMES} frames for Part 2 (19.5s)...")
        # Tabs schedule:
        # 0.0s - 6.5s: Maps Studio & Matrix (active)
        # 6.5s - 13.0s: Dyno Bench & Telemetry
        # 13.0s - 19.5s: HIL Flasher & Export
        
        current_tab = "maps"
        page.click('[data-tab="maps"]')
        page.wait_for_timeout(500)

        t0 = time.time()
        for idx in range(TOTAL_FRAMES):
            t = idx / FPS
            
            # Switch tabs on milestones
            if t >= 6.5 and current_tab == "maps":
                current_tab = "dyno"
                page.click('[data-tab="dyno"]')
                page.wait_for_timeout(200)
            elif t >= 13.0 and current_tab == "dyno":
                current_tab = "export"
                page.click('[data-tab="export"]')
                page.wait_for_timeout(200)

            out_img = FRAMES_DIR / f"p2_frame_{idx:05d}.jpg"
            page.screenshot(path=str(out_img), type="jpeg", quality=92)
            if idx % 60 == 0:
                print(f"  [Part 2 Progress] {t:.1f}s / {TOTAL_SEC:.1f}s ({idx}/{TOTAL_FRAMES})")

        dur_render = time.time() - t0
        print(f"Rendered {TOTAL_FRAMES} screencast frames in {dur_render:.2f}s ({TOTAL_FRAMES/dur_render:.1f} FPS)!")
        context.close()
        browser.close()
finally:
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except Exception:
        server_proc.kill()

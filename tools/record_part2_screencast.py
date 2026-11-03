import subprocess
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT / "demo_assets" / "_screencast_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR = TMP_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 1. Start local server
print("Starting local server...")
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
        context = browser.new_context(
            record_video_dir=str(RAW_DIR),
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:8000")
        page.wait_for_timeout(2000)

        # Click 450 Nm INTERCEPT
        print("Clicking 450 Nm INTERCEPT on live UI...")
        page.click("button:has-text('450 Nm INTERCEPT')")
        
        # Observe live Thought Stream and Safety Gate
        page.wait_for_timeout(9500)
        
        # Switch to Dyno Bench & Telemetry
        print("Switching to Dyno Bench tab...")
        page.click('[data-tab="dyno"]')
        page.wait_for_timeout(4500)
        
        # Switch to HIL Flasher & Export
        print("Switching to HIL Flasher & Export tab...")
        page.click('[data-tab="export"]')
        page.wait_for_timeout(4000)

        context.close()
        browser.close()
finally:
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except Exception:
        server_proc.kill()

recs = list(RAW_DIR.glob("*.webm"))
print(f"Recorded screencast: {recs[0]}")

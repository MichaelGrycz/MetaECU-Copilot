#!/usr/bin/env python3
"""
MetaECU Copilot — Cinema Motion Graphics Video Renderer (Kokoro-82M 56.5s).

Drives the high-budget HTML5/CSS3/Canvas motion graphics engine (demo_assets/trailer.html)
in Playwright Chromium 1080p, records the dynamic motion graphics (56.5s), and multiplexes
it with Kokoro-82M studio voiceover + tactile sound effects soundtrack.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ASSETS = ROOT / "demo_assets"
HTML_PATH = ASSETS / "trailer.html"
OUT_VIDEO = ASSETS / "MetaECU_Copilot_Demo.mp4"
TMP_DIR = ASSETS / "_mg_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

TOTAL_DURATION = 56.5  # Exactly 56.5 seconds of high-impact presentation
W, H = 1920, 1080
FPS = 30


def record_motion_graphics() -> Path:
    raw_dir = TMP_DIR / "raw_video"
    if raw_dir.exists():
        shutil.rmtree(raw_dir, ignore_errors=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"Launching Playwright Chromium for Cinema Motion Graphics ({TOTAL_DURATION}s)...")
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
            record_video_dir=str(raw_dir),
            record_video_size={"width": W, "height": H},
            viewport={"width": W, "height": H}
        )
        page = context.new_page()
        
        file_url = HTML_PATH.resolve().as_uri()
        print(f"Navigating to {file_url}...")
        page.goto(file_url)
        
        print("Triggering synchronized real-time 60fps animation...")
        page.evaluate("window.startAnimation()")
        
        start_t = time.time()
        while time.time() - start_t < TOTAL_DURATION + 0.8:
            time.sleep(0.5)
            elapsed = time.time() - start_t
            print(f"  [Progress] {elapsed:.1f}s / {TOTAL_DURATION:.1f}s", end="\r", flush=True)

        print(f"\nMotion graphics capture complete ({TOTAL_DURATION}s)! Finalizing video stream...")
        context.close()
        browser.close()

    recordings = list(raw_dir.glob("*.webm"))
    if not recordings:
        raise RuntimeError("No recorded motion graphics video found!")
    raw_file = recordings[0]
    print(f"Raw motion graphics recording: {raw_file} ({raw_file.stat().st_size / (1024*1024):.2f} MB)")
    return raw_file


def render_cinema_video():
    # 1. Generate Kokoro-82M Voiceover & Master Audio
    from tools.generate_kokoro_vo import generate_voiceover_files
    from tools.build_kokoro_master_audio import build_kokoro_master_audio
    generate_voiceover_files()
    
    soundtrack_wav = TMP_DIR / "master_audio.wav"
    build_kokoro_master_audio(soundtrack_wav)
    
    # 2. Capture dynamic motion graphics
    raw_webm = record_motion_graphics()
    
    # 3. Multiplex into Full HD 1080p MP4 with FFmpeg
    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_webm),
        "-i", str(soundtrack_wav),
        "-t", str(TOTAL_DURATION),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(OUT_VIDEO)
    ]
    
    print("\nEncoding Final Cinema Motion Graphics Video with FFmpeg...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr[-1200:])
        return False
        
    print(f"\n=======================================================")
    print(f"CINEMA MOTION GRAPHICS SUCCESS: {OUT_VIDEO}")
    print(f"Duration: {TOTAL_DURATION}s | Size: {OUT_VIDEO.stat().st_size / (1024*1024):.2f} MB")
    print(f"=======================================================")
    return True


if __name__ == "__main__":
    if not render_cinema_video():
        sys.exit(1)

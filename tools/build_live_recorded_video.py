#!/usr/bin/env python3
"""
MetaECU Copilot — Fully Dynamic Live Screen Recording & Cinema Video Builder.

Records REAL interactive browser actions (Playwright Chromium 1080p):
  - Real clicks on buttons, presets, and model selectors.
  - Live typing and real-time SSE Thought Stream event streaming.
  - Live virtual dyno gauge sweeps (tachometer & boost).
  - Live flashing crimson 450 Nm safety intercept alert & self-correction loop.
  - Live 3D WebGL difference matrix & hex inspector.
  - Live SAM 3.1 vision analysis with curve segmentation.
  - Live KWP2000 / UDS flasher terminal streaming CAN packets.
  - Compact, unobtrusive subtitles positioned at the bottom margin.
  - High-energy motorsport synthwave soundtrack + authentic acoustic SFX.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ASSETS = ROOT / "demo_assets"
OUT_VIDEO = ASSETS / "MetaECU_Copilot_Demo.mp4"
TMP_DIR = ASSETS / "_live_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080
FPS = 30
PORT = 8000
BASE_URL = f"http://127.0.0.1:{PORT}"

# Motorsport Luxury Palette
BG_DARK = (10, 16, 26)
BG_PANEL = (17, 26, 40)
CYAN = (0, 229, 255)
WHITE = (248, 250, 252)
GRAY = (148, 163, 184)
GRAY_DARK = (51, 65, 85)


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf" if not bold else "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/Calibri.ttf" if not bold else "C:/Windows/Fonts/Calibrib.ttf",
        "C:/Windows/Fonts/Arial.ttf" if not bold else "C:/Windows/Fonts/Arialbd.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_intro_card(out_path: Path):
    img = Image.new("RGB", (W, H), BG_DARK)
    d = ImageDraw.Draw(img)
    # Subtle gradient
    for y in range(0, H, 4):
        alpha = 0.5 + 0.5 * (1.0 - abs(y - H / 2) / (H / 2))
        col = (int(BG_DARK[0] + 8 * alpha), int(BG_DARK[1] + 12 * alpha), int(BG_DARK[2] + 20 * alpha))
        d.line([(0, y), (W, y)], fill=col, width=4)
        
    d.rectangle([0, 0, W, 6], fill=CYAN)
    d.rectangle([0, H - 6, W, H], fill=CYAN)
    
    # Badge
    d.rounded_rectangle([120, 220, 780, 275], radius=8, fill=(0, 45, 60), outline=CYAN, width=2)
    d.text((140, 236), "META GLOBAL AI DEVELOPER HACKATHON 2026", font=get_font(22, bold=True), fill=CYAN)
    
    # Title
    d.text((120, 310), "MetaECU Copilot", font=get_font(76, bold=True), fill=WHITE)
    d.text((122, 410), "Autonomous & Verifiable Calibration Engine with Deterministic Safety Gates", font=get_font(28, bold=False), fill=GRAY)
    
    # Feature Cards
    y_cur = 500
    features = [
        ("⚡", "AI PROPOSES: Meta Muse Spark 1.3 & SAM 3.1 Multimodal Grounding"),
        ("🛡️", "PHYSICS DISPOSES: Deterministic Domain Gate Protects GM F40 Clutch @ 377 Nm"),
        ("🔒", "VERIFIABLE PRODUCTION: 32-bit Bosch Checksum 0xD01FE500 Sealed & Flash-Ready")
    ]
    for icon, txt in features:
        d.rounded_rectangle([120, y_cur, W - 120, y_cur + 80], radius=8, fill=BG_PANEL, outline=GRAY_DARK, width=1)
        d.rectangle([120, y_cur, 128, y_cur + 80], fill=CYAN)
        d.text((155, y_cur + 20), icon, font=get_font(30, bold=True), fill=CYAN)
        d.text((220, y_cur + 24), txt, font=get_font(24, bold=True), fill=WHITE)
        y_cur += 105
        
    d.text((122, H - 90), "SOLO BUILDER: MICHAŁ GRYCZ // INDIE DEVELOPER TRACK", font=get_font(20, bold=True), fill=CYAN)
    img.save(out_path)


def render_outro_card(out_path: Path):
    img = Image.new("RGB", (W, H), BG_DARK)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 4):
        alpha = 0.5 + 0.5 * (1.0 - abs(y - H / 2) / (H / 2))
        col = (int(BG_DARK[0] + 8 * alpha), int(BG_DARK[1] + 12 * alpha), int(BG_DARK[2] + 20 * alpha))
        d.line([(0, y), (W, y)], fill=col, width=4)
        
    d.rectangle([0, 0, W, 6], fill=CYAN)
    d.rectangle([0, H - 6, W, H], fill=CYAN)
    
    d.text((120, 220), "AI PROPOSES · PHYSICS DISPOSES", font=get_font(28, bold=True), fill=CYAN)
    d.text((120, 280), "MetaECU Copilot", font=get_font(72, bold=True), fill=WHITE)
    d.text((122, 380), "The future of autonomous, grounded automotive engineering.", font=get_font(28, bold=False), fill=GRAY)
    
    y_cur = 470
    links = [
        ("🌐 LIVE DEMO (MODAL)", "https://michaelgrycz--metaecu-copilot-web.us-east.modal.run"),
        ("💻 OPEN SOURCE GITHUB", "https://github.com/MichaelGrycz/MetaECU-Copilot"),
        ("🏆 BEST AGENTIC & OPEN-WEIGHT", "Eligible for $10k Meta Open Weight (Baseten) & $5k Agentic awards")
    ]
    for title, val in links:
        d.rounded_rectangle([120, y_cur, W - 120, y_cur + 80], radius=8, fill=BG_PANEL, outline=GRAY_DARK, width=1)
        d.rectangle([120, y_cur, 128, y_cur + 80], fill=CYAN)
        d.text((155, y_cur + 16), title, font=get_font(18, bold=True), fill=CYAN)
        d.text((155, y_cur + 42), val, font=get_font(22, bold=False), fill=WHITE)
        y_cur += 105
        
    d.text((122, H - 90), "THANK YOU FOR WATCHING · META GLOBAL AI DEVELOPER HACKATHON 2026", font=get_font(20, bold=True), fill=CYAN)
    img.save(out_path)


def record_live_browser_actions() -> Path:
    """Execute live screen choreography via Playwright and record raw WebM."""
    raw_dir = TMP_DIR / "raw_rec"
    if raw_dir.exists():
        shutil.rmtree(raw_dir, ignore_errors=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    print("\nStarting backend server on port 8000...")
    server_proc = subprocess.Popen([sys.executable, str(ROOT / "web_app.py")], cwd=str(ROOT))
    time.sleep(3.5)
    
    try:
        print("Launching Playwright Chromium (1920x1080 Full HD)...")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                record_video_dir=str(raw_dir),
                record_video_size={"width": 1920, "height": 1080},
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            print("Action 1: Loading Cockpit & Ingesting Flash Binary...")
            page.goto(BASE_URL)
            page.wait_for_timeout(2000)
            
            # Hover over Hardware fingerprint
            page.hover("#ecuMeta")
            page.wait_for_timeout(2000)
            
            print("Action 2: Selecting 450 Nm Boundary Test...")
            page.click("button:has-text('450 Nm Boundary Test')")
            page.wait_for_timeout(2500)
            
            print("Action 3: Triggering 450 Nm INTERCEPT...")
            page.click("button:has-text('450 Nm INTERCEPT')")
            
            # Wait for Thought Stream to show intercept and self-correction
            print("  -> Observing real-time Thought Stream & Safety Gate intercept...")
            page.wait_for_timeout(6000)
            
            # Wait for second pull to finish and lock in PASS
            print("  -> Observing self-correction and PASS badge...")
            page.wait_for_timeout(6500)
            
            print("Action 4: Switching to Map Studio & Inspecting Delta Heatmap...")
            page.click('[data-tab="maps"]')
            page.wait_for_timeout(1500)
            page.click("button:has-text('Δ Delta')")
            page.wait_for_timeout(4500)
            
            # Expand Hex Diff Inspector
            page.click("#lblHexInspector")
            page.wait_for_timeout(3500)
            
            print("Action 5: Switching to Virtual Dyno & Executing WOT Pull...")
            page.click('[data-tab="dyno"]')
            page.wait_for_timeout(2000)
            page.click("#btnDynoSim")
            page.wait_for_timeout(5500)
            
            # Scroll down slightly to show highway telemetry
            page.evaluate("window.scrollBy(0, 320)")
            page.wait_for_timeout(3500)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1000)
            
            print("Action 6: Switching to SAM 3.1 Vision Radar...")
            page.click('[data-tab="vision"]')
            page.wait_for_timeout(1500)
            page.click("#btnLoadSampleDyno")
            page.wait_for_timeout(6000)
            
            print("Action 7: Switching to HIL Flasher & Executing CAN Sequence...")
            page.click('[data-tab="export"]')
            page.wait_for_timeout(1500)
            page.click("#btnRunHilFlash")
            page.wait_for_timeout(7000)
            
            print("Action 8: Final Verified State & Certificate...")
            page.wait_for_timeout(3500)
            
            context.close()
            browser.close()
            print("Playwright live recording complete!")
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except Exception:
            server_proc.kill()
            
    # Locate recorded video
    recordings = list(raw_dir.glob("*.webm"))
    if not recordings:
        raise RuntimeError("No Playwright video recording found!")
    raw_video = recordings[0]
    print(f"Captured live screen recording: {raw_video} ({raw_video.stat().st_size / (1024*1024):.2f} MB)")
    return raw_video


def build_compact_subtitles(out_srt: Path):
    """
    Subtitles timed to the live actions, formatted as concise 1-line text
    placed at the very bottom margin so they never obscure the UI.
    """
    srt_content = """1
00:00:00,000 --> 00:00:03,500
MetaECU Copilot: The first autonomous calibration engine with deterministic physics gates.

2
00:00:03,500 --> 00:00:09,000
Pre-existing: raw binary dump & catalog. Built this week: autonomous reasoning & safety gate.

3
00:00:09,000 --> 00:00:15,000
We ingest the stock 2 MiB flash of a Bosch EDC16C39 with 774 defined Bosch maps.

4
00:00:15,000 --> 00:00:20,500
The tuner specifies their goal: "Give me 450 Nm, maximum power" — an aggressive boundary test.

5
00:00:20,500 --> 00:00:26,500
Meta Muse Spark plans the calibration vector across 774 symbols in real-time.

6
00:00:26,500 --> 00:00:33,000
CRITICAL SAFETY INTERCEPT! The deterministic gate detects clutch shear breakaway on the GM F40!

7
00:00:33,000 --> 00:00:39,000
Indicated torque of 450 Nm minus friction @ 90°C exceeds the 377 Nm physical clutch clamping limit.

8
00:00:39,000 --> 00:00:46,000
Violation report feeds back into Muse Spark. The AI autonomously replans, clamping torque to 369 Nm.

9
00:00:46,000 --> 00:00:52,500
Attempt two passes! 185.4 horsepower, 369 Nm effective torque, and zero clutch slip.

10
00:00:52,500 --> 00:00:59,500
In the 3D Map Studio, we inspect the exact surgical delta applied to the calibration tables.

11
00:00:59,500 --> 00:01:05,000
The Hex Diff Inspector confirms binary alignment and modified Motorola MPC562 memory bytes.

12
00:01:05,000 --> 00:01:13,000
Maha LPS 3000 Dyno Cell: Replaying real OBD-II logs — spool lag drops from 4.90s to 1.34s!

13
00:01:13,000 --> 00:01:21,500
SAM 3.1 Vision Studio analyzes dyno graphs, segments torque valleys, and optimizes VNT geometry.

14
00:01:21,500 --> 00:01:30,000
To flash hardware, our HIL flasher executes genuine KWP2000 diagnostic protocols over CAN 500 kbps.

15
00:01:30,000 --> 00:01:36,500
The binary is sealed with a verified 32-bit Bosch checksum — 0xD01FE500 — ready for physical flashing.

16
00:01:36,500 --> 00:01:42,000
Every tune ships with an Official Certificate of Safe Calibration and motorsport spec card.

17
00:01:42,000 --> 00:01:49,000
AI that proposes. Physics that disposes. Try the live product at our Modal cloud link!
"""
    out_srt.write_text(srt_content.strip() + "\n", encoding="utf-8")
    print(f"Generated clean bottom-line subtitles: {out_srt}")


def assemble_complete_video():
    intro_img = TMP_DIR / "intro_card.png"
    outro_img = TMP_DIR / "outro_card.png"
    render_intro_card(intro_img)
    render_outro_card(outro_img)
    
    # 1. Capture real live screen recording
    raw_video = record_live_browser_actions()
    
    # Probe duration of raw video
    res = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(raw_video)
    ], capture_output=True, text=True)
    raw_dur = float(res.stdout.strip())
    print(f"Raw recorded video duration: {raw_dur:.2f}s")
    
    INTRO_DUR = 3.5
    OUTRO_DUR = 6.5
    total_dur = INTRO_DUR + raw_dur + OUTRO_DUR
    print(f"Total compiled video duration: {total_dur:.2f}s (~{int(total_dur)//60}m {int(total_dur)%60}s)")
    
    # 2. Build customized soundtrack matching the exact recorded duration
    from tools.build_cinematic_audio import generate_music_track, overlay_sfx
    from scipy.io import wavfile
    
    soundtrack_wav = TMP_DIR / "soundtrack.wav"
    music = generate_music_track(total_dur)
    master_stereo = overlay_sfx(music)
    pcm16 = (master_stereo.T * 32767.0).astype("int16")
    wavfile.write(str(soundtrack_wav), 48000, pcm16)
    print(f"Generated matching soundtrack: {soundtrack_wav}")
    
    # 3. Generate clean bottom-line subtitles
    srt_path = ASSETS / "subtitles.srt"
    build_compact_subtitles(srt_path)
    
    # 4. Compose full video with FFmpeg
    # Subtle, clean subtitle styling: MarginV=14 (pinned to the bottom), 1-line, thin outline, NO opaque box!
    srt_rel = srt_path.relative_to(ROOT).as_posix().replace("\\", "/")
    sub_style = (
        "FontName=Segoe UI,FontSize=20,Bold=1,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H90000000,BackColour=&H00000000,BorderStyle=1,Outline=1.2,"
        "Shadow=1,Alignment=2,MarginV=14"
    )
    
    filter_complex = (
        f"[0:v]format=yuv420p,scale={W}:{H},fps={FPS}[v_intro];"
        f"[1:v]format=yuv420p,scale={W}:{H},fps={FPS}[v_live];"
        f"[2:v]format=yuv420p,scale={W}:{H},fps={FPS}[v_outro];"
        f"[v_intro][v_live][v_outro]concat=n=3:v=1:a=0[v_concat];"
        f"[v_concat]subtitles='{srt_rel}':force_style='\"{sub_style}\"'[v_final]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(INTRO_DUR), "-i", str(intro_img),
        "-i", str(raw_video),
        "-loop", "1", "-t", str(OUTRO_DUR), "-i", str(outro_img),
        "-i", str(soundtrack_wav),
        "-filter_complex", filter_complex,
        "-map", "[v_final]",
        "-map", "3:a",
        "-t", str(round(total_dur, 2)),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(OUT_VIDEO)
    ]
    
    print("\nEncoding cinema-grade presentation video with FFmpeg...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr[-1200:])
        return False
        
    print(f"\n=======================================================")
    print(f"DYNAMIC LIVE DEMO VIDEO SUCCESS: {OUT_VIDEO}")
    print(f"Duration: {total_dur:.1f}s | Size: {OUT_VIDEO.stat().st_size / (1024*1024):.2f} MB")
    print(f"=======================================================")
    return True


if __name__ == "__main__":
    if not assemble_complete_video():
        sys.exit(1)

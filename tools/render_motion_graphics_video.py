#!/usr/bin/env python3
"""Render exact-timestamp frames; never use wall-clock browser video recording."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ASSETS = ROOT / "demo_assets"
HTML_PATH = ASSETS / "trailer.html"
CAPTIONS = ASSETS / "captions.ass"
OUT_VIDEO = ASSETS / "MetaECU_Copilot_Demo.mp4"
TOTAL_DURATION = 56.5
W, H = 1920, 1080
FPS = 30
CHECK_TIMES = (6, 24, 28, 31, 34, 38, 42, 44, 47, 50, 52, 55, 56.4)


def verify_streams(path: Path) -> dict:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)
    ], check=True, capture_output=True, text=True)
    streams = json.loads(result.stdout)["streams"]
    video = next(s for s in streams if s["codec_type"] == "video")
    audio = next(s for s in streams if s["codec_type"] == "audio")
    for stream in (video, audio):
        if abs(float(stream["duration"]) - TOTAL_DURATION) > 1 / FPS:
            raise ValueError(f"Wrong {stream['codec_type']} duration: {stream['duration']}")
    if int(video["nb_frames"]) != round(TOTAL_DURATION * FPS):
        raise ValueError("Missing video frames")
    return {"video_seconds": float(video["duration"]),
            "audio_seconds": float(audio["duration"]),
            "frames": int(video["nb_frames"]), "fps": video["r_frame_rate"]}


def record_motion_graphics(soundtrack: Path, output: Path, job_dir: Path) -> list[dict]:
    """One screenshot per frame, piped with a fixed input framerate to FFmpeg."""
    captions_rel = CAPTIONS.relative_to(ROOT).as_posix()
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
        "-f", "image2pipe", "-framerate", str(FPS), "-vcodec", "png", "-i", "pipe:0",
        "-i", str(soundtrack), "-map", "0:v:0", "-map", "1:a:0",
        "-vf", f"ass={captions_rel}",
        "-t", str(TOTAL_DURATION), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", "-movflags", "+faststart", str(output)
    ]
    checkpoints = []
    check_frames = {round(t * FPS) for t in CHECK_TIMES}
    with (job_dir / "ffmpeg.log").open("wb") as log, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": W, "height": H})
        page = context.new_page()
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(HTML_PATH.resolve().as_uri())
        page.evaluate("document.fonts.ready")
        page.evaluate("Promise.all(Array.from(document.images, img => img.decode()))")
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log, cwd=str(ROOT))
        try:
            for frame in range(round(TOTAL_DURATION * FPS)):
                seconds = frame / FPS
                state = page.evaluate("t => window.setTime(t)", seconds)
                image = page.screenshot(type="png", animations="allow")
                process.stdin.write(image)
                if frame in check_frames:
                    reference = job_dir / f"reference_{frame:04d}.png"
                    reference.write_bytes(image)
                    checkpoints.append({**state, "frame": frame, "reference": str(reference)})
                if frame % (FPS * 5) == 0:
                    print(f"Rendered {seconds:.1f}/{TOTAL_DURATION:.1f}s", flush=True)
            if page_errors:
                raise RuntimeError(f"Page errors: {page_errors}")
        except BaseException:
            process.kill()
            raise
        finally:
            process.stdin.close()
            process.wait()
            context.close()
            browser.close()
        if process.returncode:
            raise RuntimeError((job_dir / "ffmpeg.log").read_text())
    return checkpoints


def verify_encoded_frames(output: Path, checkpoints: list[dict], job_dir: Path) -> None:
    """Compare decoded MP4 frames with the exact screenshots sent to the encoder."""
    import numpy as np
    from PIL import Image, ImageDraw

    sheet = Image.new("RGB", (960, 210 * ((len(checkpoints) + 1) // 2)), "#060a12")
    draw = ImageDraw.Draw(sheet)
    for index, checkpoint in enumerate(checkpoints):
        decoded = job_dir / f"decoded_{checkpoint['frame']:04d}.png"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i", str(output),
            "-vf", f"select=eq(n\\,{checkpoint['frame']})", "-frames:v", "1", str(decoded)
        ], check=True)
        with Image.open(decoded) as image, Image.open(checkpoint["reference"]) as reference:
            error = float(np.abs(np.asarray(image, dtype=float) - np.asarray(reference, dtype=float)).mean())
            if error > 8:
                raise ValueError(f"Frame timing mismatch at {checkpoint['time']}: MAE {error:.2f}")
            checkpoint["decoded_pixel_mae"] = round(error, 3)
            tile = image.resize((480, 185))
            x, y = (index % 2) * 480, (index // 2) * 210
            sheet.paste(tile, (x, y))
            draw.text((x + 8, y + 188), f"{checkpoint['time']:.2f}s | {checkpoint['stage']} | MAE {error:.2f}", fill="white")
    sheet.save(job_dir / "sync_contact_sheet.jpg")


def render_cinema_video(regenerate_voiceover: bool = False) -> Path:
    from tools.build_kokoro_master_audio import VO_DIR, build_kokoro_master_audio
    from tools.build_captions import build_captions

    # Preserve the exact approved voice unless regeneration is explicitly requested.
    required = ("sc1_hook", "sc2_ingest", "sc3_intent", "sc4_intercept", "sc5_pass", "sc6_map3d", "sc7_outro")
    if regenerate_voiceover or not all((VO_DIR / f"{name}.wav").exists() for name in required):
        from tools.generate_kokoro_vo import generate_voiceover_files
        generate_voiceover_files()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    job_dir = ASSETS / "_mg_tmp" / stamp
    job_dir.mkdir(parents=True)
    soundtrack = build_kokoro_master_audio(job_dir / "master_audio.wav")
    build_captions()
    output = job_dir / OUT_VIDEO.name
    checkpoints = record_motion_graphics(soundtrack, output, job_dir)
    report = verify_streams(output)
    verify_encoded_frames(output, checkpoints, job_dir)
    (job_dir / "sync_report.json").write_text(
        json.dumps({**report, "checkpoints": checkpoints}, indent=2), encoding="utf-8")
    if OUT_VIDEO.exists():
        shutil.copy2(OUT_VIDEO, job_dir / "previous_demo.mp4")
    shutil.copy2(output, OUT_VIDEO)
    print(f"Verified: {report}\nVideo: {OUT_VIDEO}\nEvidence: {job_dir}", flush=True)
    return job_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate-voiceover", action="store_true")
    args = parser.parse_args()
    render_cinema_video(args.regenerate_voiceover)

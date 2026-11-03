#!/usr/bin/env python3
"""Build burned-in captions (ASS) from the exact narration cue timings."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
VO_DIR = ROOT / "demo_assets" / "_kokoro_vo"
OUT = ROOT / "demo_assets" / "captions.ass"

# (voice file, start seconds, caption text)
LINES = [
    ("sc1_hook.wav", 0.15, "What happens when AI blindly tunes an engine? It shatters the clutch."),
    ("sc1_hook.wav", 2.55, "Unless it has deterministic safety gates."),
    ("sc2_ingest.wav", 7.25, "Meet MetaECU Copilot."),
    ("sc2_ingest.wav", 9.00, "We ingest the stock 2 MiB Bosch EDC16C39 flash,"),
    ("sc2_ingest.wav", 12.20, "mapping all 774 calibration tables."),
    ("sc3_intent.wav", 17.80, "The tuner asks for 450 Nm."),
    ("sc3_intent.wav", 20.10, "Meta Muse Spark plans the torque limiter curve."),
    ("sc4_intercept.wav", 24.00, "At 2200 RPM, the safety gate detects"),
    ("sc4_intercept.wav", 26.50, "clutch shear breakaway on the GM F40 —"),
    ("sc4_intercept.wav", 29.60, "and halts execution instantly."),
    ("sc5_pass.wav", 32.80, "Muse Spark clamps the plan to 376.5 Nm at the clutch."),
    ("sc5_pass.wav", 36.40, "Attempt two passes with zero slip."),
    ("sc6_map3d.wav", 40.80, "Visual grounding inspects the effective clutch torque surface."),
    ("sc7_outro.wav", 45.80, "Replaying 33 real road logs: instant spool wins by 3.5 seconds."),
    ("sc7_outro.wav", 50.20, "202.5 PS, zero slip — within the F40 limit."),
]

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Segoe UI,40,&H00FFFFFF,&H00FFFFFF,&H00100A05,&H7A000000,-1,0,0,0,100,100,0,0,1,3,2,2,80,80,58,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def build_captions() -> Path:
    durations = {}
    for name, _start, _text in LINES:
        if name in durations:
            continue
        rate, data = wavfile.read(VO_DIR / name)
        durations[name] = len(data) / rate

    events = []
    for index, (name, start, text) in enumerate(LINES):
        nxt = LINES[index + 1][1] if index + 1 < len(LINES) and LINES[index + 1][0] == name else None
        cue_end = start + durations[name]
        end = min(cue_end, nxt - 0.05) if nxt else cue_end
        events.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{text}")

    OUT.write_text(HEADER + "\n".join(events) + "\n", encoding="utf-8")
    print(f"Captions: {OUT} ({len(events)} cues)")
    return OUT


if __name__ == "__main__":
    build_captions()
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(OUT), "-f", "null", "-"], check=False)

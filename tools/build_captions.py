#!/usr/bin/env python3
"""Build burned-in captions (ASS) from the exact verified narration cue timings."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo_assets" / "captions.ass"

# Exact non-overlapping cue timings
LINES = [
    ("0:00:00.15", "0:00:03.65", "What happens when AI blindly tunes an engine? It shatters the clutch."),
    ("0:00:03.75", "0:00:06.80", "Unless it has deterministic safety gates."),
    ("0:00:07.25", "0:00:09.10", "Meet MetaECU Copilot."),
    ("0:00:09.55", "0:00:13.20", "We ingest the stock 2 MiB Bosch EDC16C39 flash,"),
    ("0:00:13.25", "0:00:16.80", "mapping all 774 calibration tables."),
    ("0:00:17.80", "0:00:20.05", "The tuner asks for 450 Nm."),
    ("0:00:20.10", "0:00:23.10", "Meta Muse Spark plans the torque limiter curve."),
    ("0:00:24.00", "0:00:26.45", "At 2200 RPM, the safety gate detects"),
    ("0:00:26.50", "0:00:29.55", "clutch shear breakaway on the GM F40 gearbox —"),
    ("0:00:29.60", "0:00:32.20", "and halts execution instantly."),
    ("0:00:32.80", "0:00:36.85", "Muse Spark clamps the plan to 376.5 Nm at the clutch."),
    ("0:00:36.90", "0:00:39.80", "Attempt two passes with zero slip."),
    ("0:00:40.80", "0:00:44.60", "Visual grounding inspects the effective clutch torque surface."),
    ("0:00:45.80", "0:00:50.60", "Replaying 33 real road logs: instant spool wins by 3.5 seconds."),
    ("0:00:51.15", "0:00:55.60", "202.5 PS, zero slip — within the F40 limit."),
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


def build_captions() -> Path:
    events = [
        f"Dialogue: 0,{start},{end},Caption,,0,0,0,,{text}"
        for start, end, text in LINES
    ]
    OUT.write_text(HEADER + "\n".join(events) + "\n", encoding="utf-8")
    print(f"Captions: {OUT} ({len(events)} cues)")
    return OUT


if __name__ == "__main__":
    build_captions()

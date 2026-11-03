#!/usr/bin/env python3
"""
MetaECU Copilot — 47-Second Fast-Paced Voiceover Generator (SAPI5 Zira).
"""

from __future__ import annotations

from pathlib import Path
import win32com.client

ROOT = Path(__file__).resolve().parents[1]
VO_DIR = ROOT / "demo_assets" / "_vo_tmp"
VO_DIR.mkdir(parents=True, exist_ok=True)

VO_SEGMENTS = [
    ("vo_01_hook.wav", "What happens when AI blindly tunes an engine? It shatters the clutch."),
    ("vo_02_intro.wav", "Unless it has deterministic safety gates. Meet MetaECU Copilot."),
    ("vo_03_ingest.wav", "We ingest 2 MiB of Bosch EDC16C39 flash with 774 defined maps."),
    ("vo_04_intent.wav", "The tuner asks for 450 Nm. Meta Muse Spark plans the fuel curve."),
    ("vo_05_intercept.wav", "At 2200 RPM, the gate detects clutch shear breakaway on the GM F40 and halts execution!"),
    ("vo_06_pass.wav", "Muse Spark autonomously clamps torque to 369 Nm. Attempt two passes with zero slip!"),
    ("vo_07_map3d.wav", "Visual grounding inspects the surgical 3D Common Rail pressure matrix."),
    ("vo_08_drag.wav", "Replaying 33 road logs: instant spool wins by three and a half seconds!"),
    ("vo_09_outro.wav", "185 horsepower. Zero slip. 100% safe. Try MetaECU Copilot live today."),
]


def generate_voiceover_files():
    print("Generating punchy 47-second voiceover narration (Rate = +3)...")
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    for v in voice.GetVoices():
        if "Zira" in v.GetDescription():
            voice.Voice = v
            break
            
    voice.Rate = 3
    voice.Volume = 100

    results = []
    for filename, text in VO_SEGMENTS:
        out_path = VO_DIR / filename
        fs = win32com.client.Dispatch("SAPI.SpFileStream")
        fs.Open(str(out_path), 3, False)
        voice.AudioOutputStream = fs
        voice.Speak(text)
        fs.Close()
        print(f"  + Generated {filename}")
        results.append(out_path)

    print("Voiceover generation complete!")
    return results


if __name__ == "__main__":
    generate_voiceover_files()

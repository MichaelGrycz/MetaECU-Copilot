from pathlib import Path
import soundfile as sf
import subprocess
from kokoro import KPipeline
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "demo_assets" / "_kokoro_vo"
OUT_DIR.mkdir(parents=True, exist_ok=True)

scenes = [
    ("sc1_hook.wav", "What happens when AI blindly tunes an engine? It shatters the clutch. Unless... it has deterministic safety gates.", 1.15),
    ("sc2_ingest.wav", "Meet Meta E-C-U Copilot. We ingest the stock two-megabyte Bosch E-D-C-16-C-39 flash, mapping all seven hundred seventy-four calibration tables.", 1.15),
    ("sc3_intent.wav", "The tuner asks for four hundred fifty Newton meters. Meta Muse Spark plans the fuel curve.", 1.15),
    ("sc4_intercept.wav", "At twenty-two hundred R-P-M, the safety gate detects clutch shear breakaway on the G-M F-40 gearbox—and halts execution instantly.", 1.15),
    ("sc5_pass.wav", "Muse Spark autonomously clamps torque to a safe three hundred sixty-nine Newton meters. Attempt two passes with zero clutch slip.", 1.15),
    ("sc6_map3d.wav", "Visual grounding inspects the surgical 3D common-rail pressure matrix.", 1.15),
    ("sc7_outro.wav", "Replaying thirty-three real road logs: instant spool wins by three and a half seconds. One hundred eighty-five horsepower, zero slip, one hundred percent safe.", 1.15),
]


def generate_voiceover_files():
    print("Generating Kokoro-82M Neural Audio on RTX 5090 GPU...")
    pipe = KPipeline(lang_code='a')
    results = []
    for fname, text, spd in scenes:
        out_p = OUT_DIR / fname
        gen = pipe(text, voice='am_adam', speed=spd, split_pattern=r'\n+')
        audio_chunks = [chunk[2] for chunk in gen]
        full_audio = np.concatenate(audio_chunks)
        sf.write(str(out_p), full_audio, 24000)
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(out_p)], capture_output=True, text=True).stdout.strip())
        print(f"  + {fname:16s} ({dur:.2f}s) | {text[:45]}...")
        results.append(out_p)
    return results


if __name__ == "__main__":
    generate_voiceover_files()

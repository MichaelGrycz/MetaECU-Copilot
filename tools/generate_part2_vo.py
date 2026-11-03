import subprocess
import time
from pathlib import Path
from kokoro import KPipeline
import soundfile as sf
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
VO_DIR = ROOT / "demo_assets" / "_kokoro_vo"

pipe = KPipeline(lang_code='a')
text = "Now, watch the live production cockpit on Modal cloud. When testing four hundred fifty Newton meters, Meta Muse Spark plans the calibration. The deterministic safety gate intercepts clutch breakaway, and autonomously replans to three hundred seventy-six point five Newton meters. Approved and sealed."

gen = pipe(text, voice='am_adam', speed=1.15, split_pattern=r'\n+')
chunks = [c[2] for c in gen]
full_audio = np.concatenate(chunks)
sf.write(str(VO_DIR / "part2_screencast.wav"), full_audio, 24000)

dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(VO_DIR / "part2_screencast.wav")], capture_output=True, text=True).stdout.strip())
print(f"Generated part2_screencast.wav ({dur:.2f}s)")

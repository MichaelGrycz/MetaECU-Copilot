import subprocess
import json
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample

ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT / "demo_assets" / "_screencast_tmp"
OUT_VIDEO = ROOT / "demo_assets" / "MetaECU_Copilot_Demo.mp4"
PART1_VIDEO = ROOT / "demo_assets" / "MetaECU_Copilot_Demo.mp4" # currently 56.5s motion graphics
W, H = 1920, 1080
FPS = 30

# 1. Generate Intermission Card (2.5s)
card_path = TMP_DIR / "part2_card.png"
img = Image.new("RGB", (W, H), (6, 10, 18))
d = ImageDraw.Draw(img)

# Gradient background
for y in range(0, H, 4):
    alpha = 0.5 + 0.5 * (1.0 - abs(y - H / 2) / (H / 2))
    col = (int(6 + 8 * alpha), int(10 + 12 * alpha), int(18 + 20 * alpha))
    d.line([(0, y), (W, y)], fill=col, width=4)

d.rectangle([0, 0, W, 6], fill=(0, 229, 255))
d.rectangle([0, H - 6, W, H], fill=(0, 229, 255))

font_kicker = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
font_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 68)
font_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 28)

# Center texts
d.text((W/2, 380), "PART 2: LIVE PRODUCTION COCKPIT", font=font_kicker, fill=(0, 229, 255), anchor="mm")
d.text((W/2, 470), "Real-Time Cyber-Physical Actuation", font=font_title, fill=(248, 250, 252), anchor="mm")
d.text((W/2, 570), "Hosted on Modal Cloud · Fast-API · Real 2 MiB Bosch EDC16C39 Binary", font=font_sub, fill=(148, 163, 184), anchor="mm")
img.save(card_path)
print("Generated Part 2 intermission card.")

# 2. Build Audio for Part 2
sr = 48000
p2_dur = 25.0
p2_samples = int(p2_dur * sr)
p2_audio = np.zeros(p2_samples, dtype=np.float32)

# Load Kokoro VO
vo_path = ROOT / "demo_assets" / "_kokoro_vo" / "part2_screencast.wav"
vo_sr, vo_data = wavfile.read(str(vo_path))
if vo_data.ndim > 1:
    vo_data = vo_data[:, 0]
vo_data = vo_data.astype(np.float32)
if np.max(np.abs(vo_data)) > 1.0:
    vo_data /= 32767.0
if vo_sr != sr:
    vo_data = resample(vo_data, int(len(vo_data) * sr / vo_sr))

# Place VO at t = 3.0s (after intermission card)
idx_vo = int(3.2 * sr)
p2_audio[idx_vo:idx_vo + len(vo_data)] += vo_data * 0.95

# Add subtle dark-synth pulse in background
t_track = np.linspace(0, p2_dur, p2_samples, endpoint=False)
pulse = np.sin(2 * np.pi * 55.0 * t_track) * 0.04
p2_audio += pulse

# Save Part 2 Audio
p2_audio_wav = TMP_DIR / "part2_audio.wav"
p2_stereo = np.vstack([p2_audio, p2_audio])
wavfile.write(str(p2_audio_wav), sr, (p2_stereo.T * 32767.0).astype(np.int16))
print("Generated Part 2 audio track.")

# 3. Locate recorded screencast
raw_recs = list((TMP_DIR / "raw").glob("*.webm"))
raw_screencast = raw_recs[0]

# 4. Compose Part 2 Video Clip
part2_clip_mp4 = TMP_DIR / "part2_clip.mp4"
ass_captions = ROOT / "demo_assets" / "captions_part2.ass"
ass_captions.write_text("""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Segoe UI,38,&H00FFFFFF,&H00FFFFFF,&H00100A05,&H7A000000,-1,0,0,0,100,100,0,0,1,3,2,2,80,80,48,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:03.20,0:00:07.50,Caption,,0,0,0,,Now, watch the live production cockpit on Modal cloud.
Dialogue: 0,0:00:07.60,0:00:11.80,Caption,,0,0,0,,When testing 450 Nm, Meta Muse Spark plans the calibration.
Dialogue: 0,0:00:11.90,0:00:16.80,Caption,,0,0,0,,The deterministic safety gate intercepts clutch breakaway,
Dialogue: 0,0:00:16.90,0:00:21.50,Caption,,0,0,0,,and autonomously replans to 376.5 Nm. Approved and sealed.
""", encoding="utf-8")

# Encode Part 2 clip
cmd_p2 = [
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-loop", "1", "-t", "2.8", "-i", str(card_path),
    "-i", str(raw_screencast),
    "-i", str(p2_audio_wav),
    "-filter_complex",
    f"[0:v]format=yuv420p,scale={W}:{H}[v_card];"
    f"[1:v]format=yuv420p,scale={W}:{H}[v_screen];"
    f"[v_card][v_screen]concat=n=2:v=1:a=0[v_joined];"
    f"[v_joined]ass=demo_assets/captions_part2.ass[v_out]",
    "-map", "[v_out]",
    "-map", "2:a",
    "-t", "24.5",
    "-c:v", "h264_nvenc", "-preset", "p7", "-cq", "19",
    "-c:a", "aac", "-b:a", "192k",
    str(part2_clip_mp4)
]
subprocess.run(cmd_p2, check=True, cwd=str(ROOT))
print("Encoded Part 2 clip.")

# 5. Concatenate Part 1 (56.5s) and Part 2 (24.5s) into final demo video
final_mp4 = ROOT / "demo_assets" / "MetaECU_Copilot_Demo_Complete.mp4"
concat_txt = TMP_DIR / "concat.txt"
concat_txt.write_text(f"""file '{ROOT.as_posix()}/demo_assets/MetaECU_Copilot_Demo.mp4'
file '{part2_clip_mp4.as_posix()}'
""", encoding="utf-8")

cmd_concat = [
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-f", "concat", "-safe", "0",
    "-i", str(concat_txt),
    "-c", "copy",
    str(final_mp4)
]
subprocess.run(cmd_concat, check=True)
print(f"Final concatenated video ready: {final_mp4}")

# Replace main demo video with complete version
shutil.copy2(final_mp4, ROOT / "demo_assets" / "MetaECU_Copilot_Demo.mp4")
print("Replaced demo_assets/MetaECU_Copilot_Demo.mp4 with Complete (Trailer + Live Demo) Edition!")

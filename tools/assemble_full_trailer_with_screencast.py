import subprocess
import json
import shutil
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample

ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT / "demo_assets" / "_screencast_tmp"
FRAMES_DIR = TMP_DIR / "frames"
OUT_VIDEO = ROOT / "demo_assets" / "MetaECU_Copilot_Demo.mp4"
PART1_VIDEO = ROOT / "demo_assets" / "_mg_tmp" / "20261103-135758-305781" / "MetaECU_Copilot_Demo.mp4"
W, H = 1920, 1080
FPS = 30
TOTAL_P2_SEC = 19.5
SR = 48000

print(f"\n[1/3] Preparing Part 2 Audio (19.5s) with zero initial dead air...")
# 1. Audio track
p2_samples = int(TOTAL_P2_SEC * SR)
p2_audio = np.zeros(p2_samples, dtype=np.float32)

vo_path = ROOT / "demo_assets" / "_kokoro_vo" / "part2_screencast.wav"
vo_sr, vo_data = wavfile.read(str(vo_path))
if vo_data.ndim > 1:
    vo_data = vo_data[:, 0]
vo_data = vo_data.astype(np.float32)
if np.max(np.abs(vo_data)) > 1.0:
    vo_data /= 32767.0
if vo_sr != SR:
    vo_data = resample(vo_data, int(len(vo_data) * SR / vo_sr))

# Place VO at t = 0.20s
idx_vo = int(0.20 * SR)
p2_audio[idx_vo:idx_vo + len(vo_data)] += vo_data * 0.98

# Soft ambient bass pulse
t_track = np.linspace(0, TOTAL_P2_SEC, p2_samples, endpoint=False)
pulse = np.sin(2 * np.pi * 55.0 * t_track) * 0.03
p2_audio += pulse

p2_audio_wav = TMP_DIR / "part2_audio.wav"
p2_stereo = np.vstack([p2_audio, p2_audio])
wavfile.write(str(p2_audio_wav), SR, (p2_stereo.T * 32767.0).astype(np.int16))

# 2. Captions
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
Dialogue: 0,0:00:00.20,0:00:04.50,Caption,,0,0,0,,Now, watch the live production cockpit on Modal cloud.
Dialogue: 0,0:00:04.60,0:00:08.80,Caption,,0,0,0,,When testing 450 Nm, Meta Muse Spark plans the calibration.
Dialogue: 0,0:00:08.90,0:00:13.80,Caption,,0,0,0,,The deterministic safety gate intercepts clutch breakaway,
Dialogue: 0,0:00:13.90,0:00:18.50,Caption,,0,0,0,,and autonomously replans to 376.5 Nm. Approved and sealed.
""", encoding="utf-8")

# 3. Encode Part 2 clip from exactly 585 JPEG frames
print(f"\n[2/3] Encoding Part 2 clip (585 frames @ 30 FPS) with NVENC...")
part2_clip_mp4 = TMP_DIR / "part2_clip.mp4"
frames_pattern = (FRAMES_DIR / "p2_frame_%05d.jpg").as_posix()
captions_rel = ass_captions.relative_to(ROOT).as_posix()

cmd_p2 = [
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-framerate", str(FPS),
    "-i", frames_pattern,
    "-i", str(p2_audio_wav),
    "-vf", f"ass={captions_rel}",
    "-t", str(TOTAL_P2_SEC),
    "-c:v", "h264_nvenc", "-preset", "p7", "-cq", "19", "-b:v", "0",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
    "-movflags", "+faststart",
    str(part2_clip_mp4)
]
subprocess.run(cmd_p2, check=True, cwd=str(ROOT))

# Verify Part 2 stream lengths
res = subprocess.run([
    "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(part2_clip_mp4)
], check=True, capture_output=True, text=True)
p2_meta = json.loads(res.stdout)["streams"]
print(f"Part 2 encoded successfully: Video {p2_meta[0]['duration']}s, Audio {p2_meta[1]['duration']}s")

# 4. Concatenate Part 1 (56.5s) and Part 2 (19.5s) using full re-encoding for rock-solid sync
print(f"\n[3/3] Seamlessly assembling Complete 76.0s Edition (Part 1 + Part 2)...")
final_complete_mp4 = ROOT / "demo_assets" / "MetaECU_Copilot_Demo_Complete.mp4"

# We use filter_complex concat to re-encode at standard 30fps without timebase mismatch
cmd_full = [
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-i", str(PART1_VIDEO),
    "-i", str(part2_clip_mp4),
    "-filter_complex",
    "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[v_out][a_out]",
    "-map", "[v_out]",
    "-map", "[a_out]",
    "-c:v", "h264_nvenc", "-preset", "p7", "-cq", "19", "-b:v", "0",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
    "-movflags", "+faststart",
    str(final_complete_mp4)
]
subprocess.run(cmd_full, check=True, cwd=str(ROOT))

# Verify Final Video
res_final = subprocess.run([
    "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(final_complete_mp4)
], check=True, capture_output=True, text=True)
streams = json.loads(res_final.stdout)["streams"]
v_dur = float(streams[0]["duration"])
a_dur = float(streams[1]["duration"])

print(f"\n=======================================================")
print(f"COMPLETE CINEMA + LIVE COCKPIT VIDEO SUCCESS!")
print(f"Video Stream Duration: {v_dur:.3f}s")
print(f"Audio Stream Duration: {a_dur:.3f}s")
print(f"Frame Count:           {streams[0]['nb_frames']} frames @ 30 FPS")
print(f"File Size:             {final_complete_mp4.stat().st_size / (1024*1024):.2f} MB")
print(f"=======================================================")

# Replace main demo video
shutil.copy2(final_complete_mp4, OUT_VIDEO)
print(f"Updated: {OUT_VIDEO}")

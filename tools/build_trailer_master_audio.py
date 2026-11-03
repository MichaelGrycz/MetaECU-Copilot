#!/usr/bin/env python3
"""
MetaECU Copilot — 47-Second Master Audio Track Generator (Voiceover + Tactile SFX).
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

ROOT = Path(__file__).resolve().parents[1]
VO_DIR = ROOT / "demo_assets" / "_vo_tmp"
SAMPLE_RATE = 48000
TOTAL_DURATION = 47.0


def butter_lowpass_filter(data: np.ndarray, cutoff: float, fs: int = SAMPLE_RATE, order: int = 4) -> np.ndarray:
    nyq = 0.5 * fs
    normal_cutoff = min(cutoff / nyq, 0.95)
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, data)


def generate_pink_noise(n_samples: int) -> np.ndarray:
    uneven = n_samples % 2
    X = np.random.randn(n_samples // 2 + 1 + uneven) + 1j * np.random.randn(n_samples // 2 + 1 + uneven)
    S = np.sqrt(np.arange(len(X)) + 1.0)
    y = (np.fft.irfft(X / S)).real
    if uneven:
        y = y[:-1]
    y = y / (np.max(np.abs(y)) + 1e-6)
    return y.astype(np.float32)


def make_sub_impact(duration_s: float = 1.2, peak: float = 0.7) -> np.ndarray:
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    freq = 32.0 + 50.0 * np.exp(-t * 4.0)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    sub = np.sin(phase) * np.exp(-t * 3.2)
    sub = np.tanh(sub * 1.5) * 0.7
    return (butter_lowpass_filter(sub, 110.0) * peak).astype(np.float32)


def make_ui_whoosh(duration_s: float = 0.7, peak: float = 0.35) -> np.ndarray:
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    noise = generate_pink_noise(n)
    bell = np.exp(-((t - duration_s * 0.45) ** 2) / (2 * (0.15 ** 2)))
    filtered = butter_lowpass_filter(noise * bell, 1100.0)
    return (filtered * peak).astype(np.float32)


def make_tech_click(peak: float = 0.28) -> np.ndarray:
    dur = 0.04
    n = int(dur * SAMPLE_RATE)
    t = np.linspace(0, dur, n, endpoint=False)
    click = np.sin(2 * np.pi * 1800.0 * t) * np.exp(-t * 80.0)
    return (click * peak).astype(np.float32)


def make_intercept_alarm(duration_s: float = 3.2, peak: float = 0.45) -> np.ndarray:
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    audio = np.zeros(n, dtype=np.float32)
    burst_dur = 0.18
    n_b = int(burst_dur * SAMPLE_RATE)
    cur = 0
    high = True
    while cur + n_b <= n:
        f = 520.0 if high else 390.0
        t_b = np.linspace(0, burst_dur, n_b, endpoint=False)
        tone = np.sin(2 * np.pi * f * t_b) + 0.2 * np.sin(2 * np.pi * f * 2 * t_b)
        env = np.sin(np.pi * t_b / burst_dur) ** 2
        audio[cur:cur + n_b] += tone * env * peak
        cur += int(0.24 * SAMPLE_RATE)
        high = not high
    return butter_lowpass_filter(audio, 1200.0).astype(np.float32)


def make_crystal_chime(peak: float = 0.55) -> np.ndarray:
    dur = 1.6
    n = int(dur * SAMPLE_RATE)
    t = np.linspace(0, dur, n, endpoint=False)
    c1 = np.sin(2 * np.pi * 880.0 * t) * np.exp(-t * 2.8) * 0.5
    c2 = np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t * 3.5) * 0.35
    chime = butter_lowpass_filter(c1 + c2, 2800.0)
    return (chime * peak).astype(np.float32)


def load_and_resample_wav(path: Path) -> np.ndarray:
    sr, data = wavfile.read(str(path))
    if data.ndim > 1:
        data = data[:, 0]
    data = data.astype(np.float32) / 32767.0
    if sr != SAMPLE_RATE:
        from scipy.signal import resample
        num_samples = int(len(data) * SAMPLE_RATE / sr)
        data = resample(data, num_samples)
    return data


def build_master_audio(out_wav: Path) -> Path:
    print(f"Building 47-second Master Audio Track (Voiceover + SFX)...")
    n_total = int(TOTAL_DURATION * SAMPLE_RATE)
    track_l = np.zeros(n_total, dtype=np.float32)
    track_r = np.zeros(n_total, dtype=np.float32)

    def inject(mono: np.ndarray, t_start_s: float, gain_l: float = 1.0, gain_r: float = 1.0):
        idx = int(t_start_s * SAMPLE_RATE)
        count = len(mono)
        if idx + count <= n_total:
            track_l[idx:idx + count] += mono * gain_l
            track_r[idx:idx + count] += mono * gain_r
        elif idx < n_total:
            rem = n_total - idx
            track_l[idx:] += mono[:rem] * gain_l
            track_r[idx:] += mono[:rem] * gain_r

    # Voiceover Placements timed to 47.0s
    vo_cues = [
        ("vo_01_hook.wav", 0.05, 1.0),
        ("vo_02_intro.wav", 4.1, 1.0),
        ("vo_03_ingest.wav", 6.6, 1.0),
        ("vo_04_intent.wav", 11.6, 1.0),
        ("vo_05_intercept.wav", 16.6, 1.0),
        ("vo_06_pass.wav", 23.6, 1.0),
        ("vo_07_map3d.wav", 29.6, 1.0),
        ("vo_08_drag.wav", 35.1, 1.0),
        ("vo_09_outro.wav", 41.1, 1.0),
    ]

    for vo_file, t_start, vol in vo_cues:
        p = VO_DIR / vo_file
        if p.exists():
            vo_data = load_and_resample_wav(p)
            inject(vo_data * vol, t_start, 0.95, 0.95)

    # Tactile Sound Effects (SFX)
    # 0.0s: Disaster Alarm & Impact
    inject(make_sub_impact(1.8, 0.75), 0.0)
    inject(make_intercept_alarm(3.2, 0.35), 0.1)

    # 4.0s: Title Reveal Impact
    inject(make_sub_impact(1.4, 0.65), 4.0)
    inject(make_ui_whoosh(0.8, 0.28), 4.1)

    # 6.5s: Binary Ingest & Counters
    inject(make_ui_whoosh(0.7, 0.25), 6.5)
    inject(make_tech_click(0.2), 7.2)
    inject(make_tech_click(0.2), 7.6)

    # 11.5s: Intent Zoom-in
    inject(make_ui_whoosh(0.6, 0.25), 11.5)

    # 16.5s: Dyno Sweep
    t_sweep = np.linspace(0, 3.2, int(3.2 * SAMPLE_RATE), endpoint=False)
    rumble = np.sin(2 * np.pi * (45.0 + 25.0 * t_sweep) * t_sweep) * np.linspace(0.05, 0.35, len(t_sweep))
    inject(butter_lowpass_filter(rumble, 90.0), 16.5)

    # 20.0s: Intercept Clutch Klang & Warning Horn
    inject(make_sub_impact(2.0, 0.8), 20.0)
    inject(make_intercept_alarm(3.0, 0.4), 20.1)

    # 23.5s: PASS Confirmation Chime
    inject(make_crystal_chime(0.65), 23.6)

    # 29.5s: 3D Map Holographic Sweep
    inject(make_ui_whoosh(0.9, 0.3), 29.5)

    # 35.0s: Ghost Car Launch & Pass Whoosh
    inject(make_ui_whoosh(1.1, 0.4), 35.0)
    inject(make_ui_whoosh(1.0, 0.35), 37.0)

    # 41.0s: Final Grand Payoff & Sub Boom
    inject(make_sub_impact(2.5, 0.85), 41.0)
    inject(make_crystal_chime(0.4), 41.5)

    stereo = np.vstack([track_l, track_r])
    max_val = np.max(np.abs(stereo))
    if max_val > 0.95:
        stereo = stereo * (0.92 / max_val)

    pcm16 = (stereo.T * 32767.0).astype(np.int16)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(out_wav), SAMPLE_RATE, pcm16)
    print(f"Master Audio Track Generated: {out_wav}")
    return out_wav


if __name__ == "__main__":
    out = ROOT / "demo_assets" / "_vo_tmp" / "master_audio.wav"
    build_master_audio(out)

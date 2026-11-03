#!/usr/bin/env python3
"""
MetaECU Copilot — Transition & Motion Sound Effects ONLY (No Constant Drone).

Generates pure, tactile sound design synchronized strictly to visual events:
  - 0.0s:  Intro Title Impact & Smooth Whoosh
  - 4.0s:  Compliance Kicker Slide
  - 7.5s:  Silicon Chip & 4 Metric Cards Spring-In
  - 14.5s: User Intent Capsule Drop
  - 24.0s: Tachometer Dial Sweep
  - 28.5s: ⚡ CLUTCH INTERCEPT ALARM (Warning horn + Sub Impact on screen shake)
  - 36.5s: Self-Correction Loop Transition
  - 41.5s: Gate PASS Emerald Badge (Mechanical Latch + Crystal Chime)
  - 45.0s: 3D Map Studio Holographic Entrance
  - 53.0s: Ghost Car Drag Race Highway Launch Whoosh
  - 62.0s: HIL Flasher Terminal & CAN-Bus Packet Chirps
  - 67.0s: Checksum Seal Latch
  - 70.0s: Keynote Outro Ambient Chime
Between events: Total silence. Zero annoying background buzzing or music.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SAMPLE_RATE = 48000
TOTAL_DURATION = 75.0


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


def make_sub_impact(duration_s: float = 1.4, peak: float = 0.65) -> np.ndarray:
    """Soft warm 808 sub-impact on major card entrance."""
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    freq = 32.0 + 50.0 * np.exp(-t * 4.0)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    sub = np.sin(phase) * np.exp(-t * 3.0)
    sub = np.tanh(sub * 1.5) * 0.7
    return (butter_lowpass_filter(sub, 110.0) * peak).astype(np.float32)


def make_ui_whoosh(duration_s: float = 0.8, peak: float = 0.35) -> np.ndarray:
    """Tactile UI slide whoosh (soft pink noise bell curve)."""
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    noise = generate_pink_noise(n)
    bell = np.exp(-((t - duration_s * 0.45) ** 2) / (2 * (0.16 ** 2)))
    filtered = butter_lowpass_filter(noise * bell, 1100.0)
    return (filtered * peak).astype(np.float32)


def make_tech_click(peak: float = 0.3) -> np.ndarray:
    """Crisp tactile mechanical click."""
    dur = 0.05
    n = int(dur * SAMPLE_RATE)
    t = np.linspace(0, dur, n, endpoint=False)
    click = np.sin(2 * np.pi * 1800.0 * t) * np.exp(-t * 80.0)
    return (click * peak).astype(np.float32)


def make_intercept_alarm(duration_s: float = 4.2, peak: float = 0.5) -> np.ndarray:
    """Warm dual-tone warning horn on 450 Nm intercept."""
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    audio = np.zeros(n, dtype=np.float32)
    burst_dur = 0.20
    n_b = int(burst_dur * SAMPLE_RATE)
    cur = 0
    high = True
    while cur + n_b <= n:
        f = 520.0 if high else 390.0
        t_b = np.linspace(0, burst_dur, n_b, endpoint=False)
        tone = np.sin(2 * np.pi * f * t_b) + 0.2 * np.sin(2 * np.pi * f * 2 * t_b)
        env = np.sin(np.pi * t_b / burst_dur) ** 2
        audio[cur:cur + n_b] += tone * env * peak
        cur += int(0.26 * SAMPLE_RATE)
        high = not high
    return butter_lowpass_filter(audio, 1200.0).astype(np.float32)


def make_crystal_chime(peak: float = 0.5) -> np.ndarray:
    """Gentle confirmation chime (A5 880 Hz / E6 1318.5 Hz)."""
    dur = 1.8
    n = int(dur * SAMPLE_RATE)
    t = np.linspace(0, dur, n, endpoint=False)
    c1 = np.sin(2 * np.pi * 880.0 * t) * np.exp(-t * 2.8) * 0.5
    c2 = np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t * 3.5) * 0.35
    chime = butter_lowpass_filter(c1 + c2, 2800.0)
    return (chime * peak).astype(np.float32)


def make_digital_chirp(peak: float = 0.25) -> np.ndarray:
    """High-speed CAN bus packet chirp."""
    dur = 0.3
    n = int(dur * SAMPLE_RATE)
    audio = np.zeros(n, dtype=np.float32)
    for i in range(6):
        f = 2400 + (i % 3) * 400
        chip_dur = 0.025
        t = np.linspace(0, chip_dur, int(chip_dur * SAMPLE_RATE), endpoint=False)
        chirp = np.sin(2 * np.pi * f * t) * np.sin(np.pi * t / chip_dur) ** 2 * 0.18
        idx = int(i * 0.04 * SAMPLE_RATE)
        if idx + len(chirp) <= n:
            audio[idx:idx + len(chirp)] += chirp
    return (audio * peak).astype(np.float32)


def build_transition_sfx_track(total_s: float = TOTAL_DURATION) -> np.ndarray:
    n = int(total_s * SAMPLE_RATE)
    # Start with pure silent stereo buffer
    track_l = np.zeros(n, dtype=np.float32)
    track_r = np.zeros(n, dtype=np.float32)

    def place_sfx(mono: np.ndarray, t_start_s: float, pan: float = 0.5, gain: float = 1.0):
        idx = int(t_start_s * SAMPLE_RATE)
        count = len(mono)
        g_l = gain * (1.0 - pan * 0.4)
        g_r = gain * (0.6 + pan * 0.4)
        if idx + count <= n:
            track_l[idx:idx + count] += mono * g_l
            track_r[idx:idx + count] += mono * g_r
        elif idx < n:
            rem = n - idx
            track_l[idx:] += mono[:rem] * g_l
            track_r[idx:] += mono[:rem] * g_r

    # 1. t = 0.0s: Title & Intro Card Appearance
    place_sfx(make_sub_impact(1.6, 0.7), 0.0, pan=0.5)
    place_sfx(make_ui_whoosh(1.2, 0.35), 0.1, pan=0.5)

    # 2. t = 4.0s: Compliance Kicker Drop
    place_sfx(make_ui_whoosh(0.7, 0.25), 4.0, pan=0.4)

    # 3. t = 7.5s: Chip & 4 Metric Cards Pop In
    place_sfx(make_sub_impact(1.2, 0.5), 7.5, pan=0.5)
    place_sfx(make_ui_whoosh(0.9, 0.3), 7.6, pan=0.6)
    place_sfx(make_tech_click(0.25), 8.2, pan=0.3)
    place_sfx(make_tech_click(0.25), 8.6, pan=0.7)

    # 4. t = 14.5s: User Intent Capsule Drops
    place_sfx(make_ui_whoosh(0.8, 0.3), 14.5, pan=0.5)
    place_sfx(make_tech_click(0.35), 14.8, pan=0.5)

    # 5. t = 24.0s: Virtual Dyno Sweep Starts
    # Soft low-pass rumble ramping up
    t_sweep = np.linspace(0, 4.0, int(4.0 * SAMPLE_RATE), endpoint=False)
    dyno_rumble = np.sin(2 * np.pi * (45.0 + 20.0 * t_sweep) * t_sweep) * np.linspace(0.05, 0.35, len(t_sweep))
    dyno_rumble = butter_lowpass_filter(dyno_rumble, 90.0)
    place_sfx(dyno_rumble, 24.0, pan=0.5)

    # 6. t = 28.5s: ⚡ CLUTCH INTERCEPT CLIMAX (Sub Impact + Warning Alarm)
    place_sfx(make_sub_impact(2.2, 0.85), 28.5, pan=0.5)
    place_sfx(make_intercept_alarm(4.5, 0.45), 28.7, pan=0.5)

    # 7. t = 36.5s: Self-Correction Transition
    place_sfx(make_ui_whoosh(1.0, 0.35), 36.5, pan=0.6)
    place_sfx(make_digital_chirp(0.3), 37.0, pan=0.5)

    # 8. t = 41.5s: Gate PASS Emerald Badge Slam (Sub Impact + Confirmation Chime)
    place_sfx(make_sub_impact(1.2, 0.55), 41.5, pan=0.5)
    place_sfx(make_crystal_chime(0.6), 41.6, pan=0.5)

    # 9. t = 45.0s: 3D Map Studio & Real Rail Map Entrance
    place_sfx(make_ui_whoosh(1.1, 0.35), 45.0, pan=0.4)

    # 10. t = 53.0s: Ghost Car Drag Race Launch
    place_sfx(make_ui_whoosh(1.4, 0.45), 53.0, pan=0.3)
    # Boost whoosh as MetaECU surges ahead at 55s
    place_sfx(make_ui_whoosh(1.2, 0.4), 55.2, pan=0.8)

    # 11. t = 62.0s: HIL Flasher Terminal Pop-in & CAN Packet Burst
    place_sfx(make_ui_whoosh(0.8, 0.3), 62.0, pan=0.5)
    place_sfx(make_digital_chirp(0.35), 62.5, pan=0.6)
    place_sfx(make_digital_chirp(0.35), 64.0, pan=0.4)

    # 12. t = 67.0s: Checksum Sealed 0xD01FE500
    place_sfx(make_tech_click(0.4), 67.0, pan=0.5)
    place_sfx(make_crystal_chime(0.45), 67.1, pan=0.5)

    # 13. t = 70.0s: Outro Keynote Slide
    place_sfx(make_sub_impact(1.8, 0.65), 70.0, pan=0.5)
    place_sfx(make_ui_whoosh(1.2, 0.3), 70.1, pan=0.5)

    stereo = np.vstack([track_l, track_r])
    # Peak normalization
    max_val = np.max(np.abs(stereo))
    if max_val > 0.95:
        stereo = stereo * (0.92 / max_val)
    return stereo


def build_sfx_audio(out_wav: Path, total_dur: float = TOTAL_DURATION) -> Path:
    print(f"Generating clean transition-only sound effects ({total_dur:.1f}s)...")
    stereo = build_transition_sfx_track(total_dur)
    pcm16 = (stereo.T * 32767.0).astype(np.int16)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(out_wav), SAMPLE_RATE, pcm16)
    print(f"Clean Transition SFX Audio Generated: {out_wav}")
    return out_wav


if __name__ == "__main__":
    out = Path("demo_assets/_sfx_tmp/transition_sfx.wav")
    build_sfx_audio(out)

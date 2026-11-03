#!/usr/bin/env python3
"""
MetaECU Copilot — Master audio: Kokoro narration + dark synth bed + tactile SFX.

A continuous 100 BPM dark-synth pulse runs under the whole trailer and is
side-chain ducked by the narration envelope, so speech never fights the music.
The dyno section is a real diesel ramp (firing frequency = RPM / 30) with a
turbo spool whistle, not retro blips.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter, resample

ROOT = Path(__file__).resolve().parents[1]
VO_DIR = ROOT / "demo_assets" / "_kokoro_vo"
SAMPLE_RATE = 48000
TOTAL_DURATION = 56.5

CUES = [
    ("sc1_hook.wav", 0.15),
    ("sc2_ingest.wav", 7.25),
    ("sc3_intent.wav", 17.80),
    ("sc4_intercept.wav", 24.00),
    ("sc5_pass.wav", 32.80),
    ("sc6_map3d.wav", 40.80),
    ("sc7_outro.wav", 45.80),
]


def lowpass(data: np.ndarray, cutoff: float, order: int = 4) -> np.ndarray:
    nyq = 0.5 * SAMPLE_RATE
    b, a = butter(order, min(cutoff / nyq, 0.95), btype="low", analog=False)
    return lfilter(b, a, data)


def pink_noise(n: int) -> np.ndarray:
    uneven = n % 2
    x = np.random.randn(n // 2 + 1 + uneven) + 1j * np.random.randn(n // 2 + 1 + uneven)
    y = np.fft.irfft(x / np.sqrt(np.arange(len(x)) + 1.0)).real
    y = y[:-1] if uneven else y
    return (y / (np.max(np.abs(y)) + 1e-6)).astype(np.float32)


def sub_impact(duration: float = 1.3, peak: float = 0.7) -> np.ndarray:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False)
    freq = 32.0 + 50.0 * np.exp(-t * 4.0)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * np.exp(-t * 3.2)
    return (lowpass(np.tanh(body * 1.5) * 0.7, 110.0) * peak).astype(np.float32)


def whoosh(duration: float = 0.7, peak: float = 0.35) -> np.ndarray:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False)
    bell = np.exp(-((t - duration * 0.45) ** 2) / (2 * 0.15 ** 2))
    return (lowpass(pink_noise(n) * bell, 1100.0) * peak).astype(np.float32)


def tech_click(peak: float = 0.28) -> np.ndarray:
    n = int(0.04 * SAMPLE_RATE)
    t = np.linspace(0, 0.04, n, endpoint=False)
    return (np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 80) * peak).astype(np.float32)


def alarm(duration: float, peak: float = 0.45) -> np.ndarray:
    n = int(duration * SAMPLE_RATE)
    out = np.zeros(n, dtype=np.float32)
    burst = int(0.18 * SAMPLE_RATE)
    i, high = 0, True
    while i + burst <= n:
        f = 520.0 if high else 390.0
        tb = np.linspace(0, 0.18, burst, endpoint=False)
        out[i:i + burst] += (np.sin(2 * np.pi * f * tb) + 0.2 * np.sin(4 * np.pi * f * tb)) \
            * np.sin(np.pi * tb / 0.18) ** 2 * peak
        i += int(0.24 * SAMPLE_RATE)
        high = not high
    return lowpass(out, 1200.0)


def chime(peak: float = 0.55) -> np.ndarray:
    n = int(1.6 * SAMPLE_RATE)
    t = np.linspace(0, 1.6, n, endpoint=False)
    tone = (np.sin(2 * np.pi * 880 * t) * np.exp(-t * 2.8) * 0.5
            + np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t * 3.5) * 0.35)
    return (lowpass(tone, 2800.0) * peak).astype(np.float32)


def diesel_pull(start_rpm: float, end_rpm: float, duration: float, peak: float = 0.42) -> np.ndarray:
    """Four-cylinder diesel under load: firing frequency = RPM / 30."""
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False)
    rpm = start_rpm * (end_rpm / start_rpm) ** (t / duration)
    firing = rpm / 30.0

    def tones(mult: float, amp: float) -> np.ndarray:
        phase = 2 * np.pi * np.cumsum(firing * mult) / SAMPLE_RATE
        saw = 2.0 * (phase / (2 * np.pi) - np.floor(phase / (2 * np.pi) + 0.5))
        return saw * amp

    block = tones(1.0, 0.55) + tones(0.5, 0.40) + tones(2.0, 0.18) + tones(3.0, 0.09)
    block += pink_noise(n) * 0.10
    # Turbo spool whistle rides the same RPM ramp.
    phase = 2 * np.pi * np.cumsum(1400.0 + (rpm / end_rpm) ** 1.4 * 4200.0) / SAMPLE_RATE
    block += np.sin(phase) * (0.10 + 0.16 * (t / duration))
    env = np.minimum(1.0, t / 0.35) * np.minimum(1.0, (duration - t) / 0.45)
    return (lowpass(block * env, 2400.0) * peak).astype(np.float32)


def music_bed(total: float) -> np.ndarray:
    """Sparse dark-synth pulse: sub line, soft kick and a distant pad."""
    n = int(total * SAMPLE_RATE)
    bed = np.zeros(n, dtype=np.float32)
    beat = 60.0 / 100.0
    sixteenth = beat / 4.0

    # D minor pulse
    bass = {0: 36.71, 3: 43.65, 6: 49.00, 9: 55.00, 12: 65.41, 14: 73.42}
    n16 = int(sixteenth * SAMPLE_RATE)
    t16 = np.linspace(0, sixteenth, n16, endpoint=False)
    for i in range(int(total / sixteenth)):
        start = int(i * sixteenth * SAMPLE_RATE)
        semis = i % 16
        freq = bass.get(semis, 36.71)
        phase = 2 * np.pi * freq * t16
        note = (np.sin(phase) * 0.7 + np.sin(2 * phase) * 0.2) * np.exp(-t16 * 11.0)
        if start + n16 <= n:
            bed[start:start + n16] += (note * 0.5).astype(np.float32)

    # Soft kick on every beat
    nk = int(0.22 * SAMPLE_RATE)
    tk = np.linspace(0, 0.22, nk, endpoint=False)
    fk = 120.0 * np.exp(-tk * 18.0) + 42.0
    kick = np.sin(2 * np.pi * np.cumsum(fk) / SAMPLE_RATE) * np.exp(-tk * 9.0) * 0.5
    for b in range(int(total / beat)):
        s = int(b * beat * SAMPLE_RATE)
        if s + nk <= n:
            bed[s:s + nk] += kick.astype(np.float32)

    # Distant sustained pad (D minor add9), very quiet
    t = np.linspace(0, total, n, endpoint=False)
    pad = np.zeros(n, dtype=np.float32)
    for f, a in ((146.83, 0.30), (174.61, 0.22), (220.00, 0.18), (329.63, 0.10)):
        pad += np.sin(2 * np.pi * f * t) * a
    pad *= (0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * t)).astype(np.float32)
    bed += lowpass(pad, 900.0) * 0.16

    return lowpass(bed, 3200.0) * 0.42


def load_cue(path: Path) -> np.ndarray:
    rate, data = wavfile.read(str(path))
    if data.ndim > 1:
        data = data[:, 0]
    data = data.astype(np.float32)
    if np.max(np.abs(data)) > 1.0:
        data /= 32767.0
    if rate != SAMPLE_RATE:
        data = resample(data, int(len(data) * SAMPLE_RATE / rate)).astype(np.float32)
    return data


def build_kokoro_master_audio(out_wav: Path) -> Path:
    n_total = int(TOTAL_DURATION * SAMPLE_RATE)
    narration = np.zeros(n_total, dtype=np.float32)

    previous_end = 0.0
    for name, start_s in CUES:
        voice = load_cue(VO_DIR / name)
        end = start_s + len(voice) / SAMPLE_RATE
        if start_s < previous_end or end > TOTAL_DURATION:
            raise ValueError(f"Narration overlaps or exceeds video: {name} ({start_s:.2f}-{end:.2f}s)")
        print(f"  {name}: {start_s:.2f}-{end:.2f}s")
        i = int(start_s * SAMPLE_RATE)
        narration[i:i + len(voice)] += voice * 0.98
        previous_end = end

    # Side-chain: duck the bed while the narrator speaks.
    window = int(0.20 * SAMPLE_RATE)
    envelope = np.convolve(np.abs(narration), np.ones(window, dtype=np.float32) / window, mode="same")
    envelope /= max(float(envelope.max()), 1e-6)
    duck = 1.0 - 0.78 * np.clip(envelope * 6.0, 0.0, 1.0)

    bed = music_bed(TOTAL_DURATION) * duck * 0.15  # audible pulse, still ~-18 dB under speech

    mix = narration + bed

    def add(sound: np.ndarray, start_s: float, gain: float = 1.0) -> None:
        i = int(start_s * SAMPLE_RATE)
        if i >= n_total:
            return
        chunk = sound[: n_total - i]
        mix[i:i + len(chunk)] += chunk * gain

    def add_ducked(sound: np.ndarray, start_s: float, gain: float = 1.0) -> None:
        """Engine/SFX must not mask the narrator: follow the same side-chain."""
        i = int(start_s * SAMPLE_RATE)
        if i >= n_total:
            return
        chunk = sound[: n_total - i]
        mix[i:i + len(chunk)] += chunk * gain * duck[i:i + len(chunk)]

    add(sub_impact(1.8, 0.75), 0.0)
    add(alarm(3.2, 0.30), 0.10)
    add(sub_impact(1.4, 0.65), 7.2)
    add(whoosh(0.8, 0.26), 7.3)
    add(whoosh(0.7, 0.22), 9.5)
    add(tech_click(0.18), 10.2)
    add(tech_click(0.18), 10.7)
    add(whoosh(0.6, 0.22), 17.6)

    # Real dyno pull instead of retro blips, ducked so it never masks the voice.
    add_ducked(diesel_pull(1290, 2190, 5.8, 0.55), 23.5)
    add(sub_impact(2.0, 0.80), 29.6)
    add_ducked(alarm(3.0, 0.42), 29.6)
    add(chime(0.62), 32.8)
    add(whoosh(0.9, 0.26), 40.8)
    add(whoosh(1.1, 0.34), 45.8)
    add(whoosh(1.0, 0.30), 48.0)
    add(sub_impact(2.5, 0.85), 51.0)
    add(chime(0.40), 51.5)

    stereo = np.vstack([mix, mix])
    peak = float(np.max(np.abs(stereo)))
    if peak > 0.95:
        stereo *= 0.92 / peak

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(out_wav), SAMPLE_RATE, (stereo.T * 32767.0).astype(np.int16))
    print(f"Master audio: {out_wav}")
    return out_wav


if __name__ == "__main__":
    build_kokoro_master_audio(ROOT / "demo_assets" / "_kokoro_vo" / "kokoro_master.wav")

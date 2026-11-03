#!/usr/bin/env python3
"""
MetaECU Copilot — Warm Cinematic Trailer Soundtrack Generator.

No piercing square waves or harsh noise. Pure warm analog pads (Blade Runner /
Hans Zimmer style Dm9 chords), deep filtered sub-bass, smooth pink-noise whooshes,
and rich low-passed acoustic sound effects.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SAMPLE_RATE = 48000
TOTAL_DURATION = 75.0  # 1 minute 15 seconds


def butter_lowpass_filter(data: np.ndarray, cutoff: float, fs: int = SAMPLE_RATE, order: int = 4) -> np.ndarray:
    nyq = 0.5 * fs
    normal_cutoff = min(cutoff / nyq, 0.95)
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, data)


def generate_pink_noise(n_samples: int) -> np.ndarray:
    """Generate 1/f pink noise (warm, natural, no harsh treble)."""
    uneven = n_samples % 2
    X = np.random.randn(n_samples // 2 + 1 + uneven) + 1j * np.random.randn(n_samples // 2 + 1 + uneven)
    S = np.sqrt(np.arange(len(X)) + 1.0)
    y = (np.fft.irfft(X / S)).real
    if uneven:
        y = y[:-1]
    y = y / (np.max(np.abs(y)) + 1e-6)
    return y.astype(np.float32)


def make_cinematic_sub_impact(duration_s: float = 2.2, peak: float = 0.7) -> np.ndarray:
    """Deep warm 808 sub-boom impact (Hans Zimmer style braam/sub hit)."""
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    # Pitch drop 85 Hz -> 32 Hz
    freq = 32.0 + 53.0 * np.exp(-t * 3.5)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    sub = np.sin(phase) * np.exp(-t * 2.2)
    # Warm saturation
    sub = np.tanh(sub * 1.5) * 0.75
    # Low-pass filter at 120 Hz to ensure zero harshness
    sub = butter_lowpass_filter(sub, 120.0)
    return (sub * peak).astype(np.float32)


def make_smooth_whoosh(duration_s: float = 1.8, peak: float = 0.35) -> np.ndarray:
    """Smooth cinematic transition whoosh (pink noise bell sweep)."""
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    noise = generate_pink_noise(n)
    # Gaussian bell envelope
    bell = np.exp(-((t - duration_s * 0.45) ** 2) / (2 * (0.35 ** 2)))
    # Moving frequency modulation
    filtered = butter_lowpass_filter(noise * bell, 1200.0)
    return (filtered * peak).astype(np.float32)


def make_warm_alarm(duration_s: float = 6.0, peak: float = 0.45) -> np.ndarray:
    """Warm, filtered cinematic warning horn (NOT piercing)."""
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    audio = np.zeros(n, dtype=np.float32)
    # Gentle alternating 520 Hz / 390 Hz sine tones with soft attack/decay
    burst_dur = 0.22
    n_b = int(burst_dur * SAMPLE_RATE)
    cur = 0
    high = True
    while cur + n_b <= n:
        f = 520.0 if high else 390.0
        t_b = np.linspace(0, burst_dur, n_b, endpoint=False)
        tone = np.sin(2 * np.pi * f * t_b) + 0.3 * np.sin(2 * np.pi * f * 2 * t_b)
        env = np.sin(np.pi * t_b / burst_dur) ** 2
        audio[cur:cur + n_b] += tone * env * peak
        cur += int(0.28 * SAMPLE_RATE)
        high = not high
    # Warm lowpass filter at 1500 Hz
    audio = butter_lowpass_filter(audio, 1500.0)
    return audio


def make_warm_chime(peak: float = 0.4) -> np.ndarray:
    """Soft warm ambient glass confirmation chime (A5/E6)."""
    dur = 2.0
    n = int(dur * SAMPLE_RATE)
    t = np.linspace(0, dur, n, endpoint=False)
    c1 = np.sin(2 * np.pi * 880.0 * t) * np.exp(-t * 3.0) * 0.5
    c2 = np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t * 4.0) * 0.35
    c3 = np.sin(2 * np.pi * 1760.0 * t) * np.exp(-t * 5.5) * 0.15
    chime = (c1 + c2 + c3)
    return (butter_lowpass_filter(chime, 3000.0) * peak).astype(np.float32)


def make_warm_ambient_soundtrack(total_s: float = TOTAL_DURATION) -> np.ndarray:
    """
    Blade Runner 2049 / Interstellar style ambient tech chord progression.
    Deep, wide, atmospheric, zero ear fatigue.
    """
    n = int(total_s * SAMPLE_RATE)
    track_l = np.zeros(n, dtype=np.float32)
    track_r = np.zeros(n, dtype=np.float32)
    t = np.linspace(0, total_s, n, endpoint=False)
    
    # Chord progression: Dm9 (0-18s) -> Bbmaj7 (18-36s) -> Gm9 (36-54s) -> Dm (54-75s)
    chords = [
        # (start_s, end_s, [freqs in Hz])
        (0.0, 18.0, [73.42, 146.83, 220.00, 261.63, 329.63, 440.00]),   # Dm9: D2, D3, A3, C4, E4, A4
        (18.0, 34.0, [58.27, 116.54, 174.61, 233.08, 293.66, 349.23]), # Bbmaj7: Bb1, Bb2, F3, Bb3, D4, F4
        (34.0, 52.0, [49.00, 98.00, 146.83, 196.00, 261.63, 293.66]),   # Gm7: G1, G2, D3, G3, C4, D4
        (52.0, 75.0, [73.42, 146.83, 220.00, 293.66, 349.23, 440.00]),  # Dm: D2, D3, A3, D4, F4, A4
    ]
    
    for start_s, end_s, freqs in chords:
        idx_start = int(start_s * SAMPLE_RATE)
        idx_end = min(n, int(end_s * SAMPLE_RATE))
        dur_chord = (idx_end - idx_start) / SAMPLE_RATE
        t_chord = np.linspace(0, dur_chord, idx_end - idx_start, endpoint=False)
        
        # Soft crossfade envelope
        att = min(2.5, dur_chord * 0.25)
        dec = min(2.5, dur_chord * 0.25)
        env = np.ones(len(t_chord), dtype=np.float32)
        n_att = int(att * SAMPLE_RATE)
        n_dec = int(dec * SAMPLE_RATE)
        if n_att > 0:
            env[:n_att] = np.sin(np.linspace(0, np.pi / 2, n_att)) ** 2
        if n_dec > 0:
            env[-n_dec:] = np.cos(np.linspace(0, np.pi / 2, n_dec)) ** 2
            
        pad_mono = np.zeros(len(t_chord), dtype=np.float32)
        for i, f in enumerate(freqs):
            # Soft sine with subtle detuning for stereo chorus width
            detune = 1.0 + 0.0015 * (i % 2 * 2 - 1)
            weight = 0.28 / (1.0 + i * 0.25)
            pad_mono += np.sin(2 * np.pi * f * detune * t_chord) * weight
            
        # Lowpass filter the pad to keep it warm and non-intrusive
        pad_warm = butter_lowpass_filter(pad_mono * env, 950.0)
        
        # Stereo panning
        track_l[idx_start:idx_end] += pad_warm * 0.65
        track_r[idx_start:idx_end] += pad_warm * 0.65

    # Minimalist warm heartbeat pulse (soft 45 Hz sub pulse on beats 1 and 3)
    pulse_bpm = 100.0
    pulse_interval = 60.0 / pulse_bpm
    n_pulse = int(0.22 * SAMPLE_RATE)
    t_p = np.linspace(0, 0.22, n_pulse, endpoint=False)
    heartbeat = np.sin(2 * np.pi * 50.0 * t_p) * np.sin(np.pi * t_p / 0.22) ** 2 * 0.35
    heartbeat = butter_lowpass_filter(heartbeat, 85.0)
    
    total_pulses = int(total_s / pulse_interval)
    for p_idx in range(total_pulses):
        t_pos = p_idx * pulse_interval
        # Skip during the intercept crisis (28s to 36s)
        if 28.0 <= t_pos <= 35.0:
            continue
        idx_p = int(t_pos * SAMPLE_RATE)
        if idx_p + n_pulse <= n:
            track_l[idx_p:idx_p + n_pulse] += heartbeat
            track_r[idx_p:idx_p + n_pulse] += heartbeat

    return np.vstack([track_l, track_r])


def overlay_warm_sfx(soundtrack: np.ndarray) -> np.ndarray:
    stereo = np.copy(soundtrack)
    n_total = stereo.shape[1]
    
    def inject(mono: np.ndarray, t_s: float, gain: float = 1.0):
        idx = int(t_s * SAMPLE_RATE)
        n = len(mono)
        if idx + n <= n_total:
            stereo[0, idx:idx + n] += mono * gain
            stereo[1, idx:idx + n] += mono * gain
        elif idx < n_total:
            rem = n_total - idx
            stereo[0, idx:] += mono[:rem] * gain
            stereo[1, idx:] += mono[:rem] * gain

    # T = 0.0s: Opening Sub-Impact & Smooth Whoosh
    inject(make_cinematic_sub_impact(2.5, 0.8), 0.0)
    inject(make_smooth_whoosh(2.0, 0.3), 0.2)
    
    # T = 7.0s: Binary Chip reveal whoosh
    inject(make_smooth_whoosh(1.6, 0.3), 7.0)
    
    # T = 14.0s: User Intent card entrance
    inject(make_smooth_whoosh(1.4, 0.28), 14.0)
    
    # T = 23.0s: Dyno Cell rev up whoosh
    inject(make_smooth_whoosh(1.8, 0.35), 23.0)
    
    # T = 28.5s: ⚡ CLUTCH INTERCEPT CLIMAX (Warm Warning Horn + Sub Impact)
    inject(make_cinematic_sub_impact(2.8, 0.9), 28.5)
    inject(make_warm_alarm(5.5, 0.5), 28.7)
    
    # T = 35.0s: Self-Correction chime & recovery
    inject(make_smooth_whoosh(1.8, 0.35), 35.0)
    
    # T = 41.5s: PASS Confirmation (Warm Chime)
    inject(make_warm_chime(0.55), 41.5)
    
    # T = 43.0s: 3D Surface entrance whoosh
    inject(make_smooth_whoosh(1.6, 0.3), 43.0)
    
    # T = 52.0s: Ghost Car Highway pass whoosh
    inject(make_smooth_whoosh(2.2, 0.4), 52.0)
    
    # T = 61.0s: SAM 3.1 & HIL Flasher whoosh
    inject(make_smooth_whoosh(1.8, 0.35), 61.0)
    
    # T = 68.0s: Final Certificate & Outro Sub-Impact
    inject(make_cinematic_sub_impact(3.0, 0.85), 68.0)
    inject(make_warm_chime(0.4), 68.5)

    # Master Limiter
    max_val = np.max(np.abs(stereo))
    if max_val > 0.95:
        stereo = stereo * (0.92 / max_val)
    return stereo


def build_warm_audio(out_wav: Path, total_dur: float = TOTAL_DURATION) -> Path:
    print(f"Synthesizing warm ambient cinematic soundtrack ({total_dur:.1f}s)...")
    music = make_warm_ambient_soundtrack(total_dur)
    master = overlay_warm_sfx(music)
    pcm16 = (master.T * 32767.0).astype(np.int16)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(out_wav), SAMPLE_RATE, pcm16)
    print(f"Warm Audio Ready: {out_wav}")
    return out_wav


if __name__ == "__main__":
    out = Path("demo_assets/_warm_tmp/warm_soundtrack.wav")
    build_warm_audio(out)

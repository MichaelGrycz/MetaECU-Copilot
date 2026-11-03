#!/usr/bin/env python3
"""
MetaECU Copilot — Autonomous Sound Design & Cinematic Soundtrack Generator.

Synthesizes a bespoke 120-BPM motorsport synthwave soundtrack with layered
physical audio effects (engine sweeps, turbo whistle, clutch shudder, alarm horn,
automotive relay clicks, and CAN-bus bursts) matching the live recording milestones.
"""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 48000


def envelope(n_samples: int, attack_s: float, decay_s: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    n_att = int(attack_s * sr)
    n_dec = int(decay_s * sr)
    env = np.ones(n_samples, dtype=np.float32)
    if n_att > 0:
        env[:n_att] = np.linspace(0.001, 1.0, n_att)
    if n_dec > 0 and n_dec < n_samples:
        env[-n_dec:] = np.linspace(1.0, 0.0001, n_dec)
    return env


def make_noise_burst(duration_s: float, freq: float, q: float, peak: float) -> np.ndarray:
    n = int(duration_s * SAMPLE_RATE)
    noise = (np.random.rand(n).astype(np.float32) * 2.0 - 1.0)
    t = np.linspace(0, duration_s, n, endpoint=False)
    filtered = noise * np.sin(2 * np.pi * freq * t)
    env = envelope(n, 0.005, duration_s * 0.7)
    return (filtered * env * peak).astype(np.float32)


def make_engine_sweep(start_rpm: float, end_rpm: float, duration_s: float, peak: float = 0.35) -> np.ndarray:
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    rpm = start_rpm * (end_rpm / start_rpm) ** (t / duration_s)
    crank_f = rpm / 30.0
    phase_crank = 2 * np.pi * np.cumsum(crank_f) / SAMPLE_RATE
    crank_wave = 2.0 * (phase_crank / (2 * np.pi) - np.floor(phase_crank / (2 * np.pi) + 0.5))
    
    sub_f = rpm / 60.0
    phase_sub = 2 * np.pi * np.cumsum(sub_f) / SAMPLE_RATE
    sub_wave = 2.0 * np.abs(2.0 * (phase_sub / (2 * np.pi) - np.floor(phase_sub / (2 * np.pi) + 0.5))) - 1.0
    
    turbo_f = 1600.0 + (rpm / end_rpm) * 4400.0
    phase_turbo = 2 * np.pi * np.cumsum(turbo_f) / SAMPLE_RATE
    turbo_wave = np.sin(phase_turbo) * 0.22
    
    noise = (np.random.rand(n).astype(np.float32) * 2.0 - 1.0) * 0.08
    combined = crank_wave * 0.5 + sub_wave * 0.35 + turbo_wave + noise
    env = envelope(n, 0.15, 0.2)
    return (combined * env * peak).astype(np.float32)


def make_alarm_horn(duration_s: float, peak: float = 0.45) -> np.ndarray:
    n = int(duration_s * SAMPLE_RATE)
    audio = np.zeros(n, dtype=np.float32)
    burst_dur = 0.14
    n_burst = int(burst_dur * SAMPLE_RATE)
    cur = 0
    high_tone = True
    while cur + n_burst <= n:
        f = 620.0 if high_tone else 466.0
        t = np.linspace(0, burst_dur, n_burst, endpoint=False)
        sq = np.sign(np.sin(2 * np.pi * f * t))
        env = envelope(n_burst, 0.01, 0.02)
        audio[cur:cur + n_burst] += sq * env * peak
        cur += int(0.18 * SAMPLE_RATE)
        high_tone = not high_tone
    return audio


def make_clutch_shudder(duration_s: float = 0.6, peak: float = 0.6) -> np.ndarray:
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    saw = 2.0 * (t * 42.0 - np.floor(t * 42.0 + 0.5))
    noise = (np.random.rand(n).astype(np.float32) * 2.0 - 1.0)
    crunch = (saw * 0.6 + noise * 0.7)
    crunch = np.tanh(crunch * 2.5)
    env = envelope(n, 0.02, duration_s * 0.6)
    return (crunch * env * peak).astype(np.float32)


def make_relay_click_and_chime(peak: float = 0.5) -> np.ndarray:
    dur = 0.8
    n = int(dur * SAMPLE_RATE)
    audio = np.zeros(n, dtype=np.float32)
    t = np.linspace(0, dur, n, endpoint=False)
    
    strike1 = make_noise_burst(0.04, 2400, 1.2, 0.4)
    audio[:len(strike1)] += strike1
    strike2 = make_noise_burst(0.035, 1800, 1.2, 0.28)
    audio[int(0.065 * SAMPLE_RATE):int(0.065 * SAMPLE_RATE) + len(strike2)] += strike2
    
    idx_chime = int(0.09 * SAMPLE_RATE)
    t_ch = t[idx_chime:]
    chime1 = np.sin(2 * np.pi * 880 * t_ch) * np.exp(-t_ch * 8.0) * 0.25
    chime2 = np.sin(2 * np.pi * 1318 * t_ch) * np.exp(-t_ch * 6.0) * 0.18
    audio[idx_chime:] += chime1 + chime2
    return (audio * peak).astype(np.float32)


def make_can_bus_burst(peak: float = 0.3) -> np.ndarray:
    dur = 0.35
    n = int(dur * SAMPLE_RATE)
    audio = np.zeros(n, dtype=np.float32)
    for i in range(8):
        f = 3200 + (i % 4) * 500
        chip_dur = 0.025
        t = np.linspace(0, chip_dur, int(chip_dur * SAMPLE_RATE), endpoint=False)
        chirp = np.sin(2 * np.pi * f * t) * envelope(len(t), 0.002, 0.005) * 0.2
        idx = int(i * 0.038 * SAMPLE_RATE)
        if idx + len(chirp) <= n:
            audio[idx:idx + len(chirp)] += chirp
    return (audio * peak).astype(np.float32)


def generate_music_track(total_s: float) -> np.ndarray:
    n_total = int(total_s * SAMPLE_RATE)
    track_l = np.zeros(n_total, dtype=np.float32)
    track_r = np.zeros(n_total, dtype=np.float32)
    
    bpm = 120.0
    beat_s = 60.0 / bpm
    sixteenth_s = beat_s / 4.0
    
    notes = {
        'D1': 36.71, 'D2': 73.42, 'F1': 43.65, 'G1': 49.00,
        'A1': 55.00, 'C2': 65.41, 'D3': 146.83, 'F3': 174.61,
        'A3': 220.0, 'C4': 261.63, 'D4': 293.66, 'E4': 329.63,
        'F4': 349.23, 'A4': 440.0, 'C5': 523.25
    }
    
    # 1. Kick drum
    kick_dur = 0.18
    n_kick = int(kick_dur * SAMPLE_RATE)
    t_k = np.linspace(0, kick_dur, n_kick, endpoint=False)
    f_k = 150.0 * np.exp(-t_k * 22.0) + 35.0
    phase_k = 2 * np.pi * np.cumsum(f_k) / SAMPLE_RATE
    kick = np.sin(phase_k) * np.exp(-t_k * 14.0) * 0.65
    
    # 2. Snare
    snare_dur = 0.14
    n_snare = int(snare_dur * SAMPLE_RATE)
    t_s = np.linspace(0, snare_dur, n_snare, endpoint=False)
    snare_noise = (np.random.rand(n_snare).astype(np.float32) * 2 - 1) * np.exp(-t_s * 25.0)
    snare_body = np.sin(2 * np.pi * 180.0 * t_s) * np.exp(-t_s * 35.0) * 0.4
    snare = (snare_noise * 0.6 + snare_body) * 0.45
    
    total_beats = int(total_s / beat_s)
    for b in range(total_beats):
        t_pos = b * beat_s
        idx = int(t_pos * SAMPLE_RATE)
        vol_duck = 0.35 if (25.0 <= t_pos <= 37.0) else 1.0
        
        if idx + n_kick <= n_total:
            track_l[idx:idx + n_kick] += kick * vol_duck
            track_r[idx:idx + n_kick] += kick * vol_duck
            
        if b % 2 == 1:
            if idx + n_snare <= n_total:
                track_l[idx:idx + n_snare] += snare * 0.85 * vol_duck
                track_r[idx:idx + n_snare] += snare * 0.85 * vol_duck
                
        for sub in (0.0, 0.25):
            h_idx = int((t_pos + sub) * SAMPLE_RATE)
            h_n = int(0.04 * SAMPLE_RATE)
            if h_idx + h_n <= n_total:
                h_noise = (np.random.rand(h_n).astype(np.float32) * 2 - 1) * np.linspace(1, 0, h_n) * 0.08
                track_l[h_idx:h_idx + h_n] += h_noise * vol_duck
                track_r[h_idx:h_idx + h_n] += h_noise * vol_duck
    
    # 3. Synth bassline
    bass_pattern = ['D1', 'D1', 'D2', 'D1', 'D1', 'D1', 'F1', 'G1',
                    'D1', 'D1', 'D2', 'D1', 'A1', 'G1', 'F1', 'C2']
    total_16ths = int(total_s / sixteenth_s)
    n_16 = int(sixteenth_s * SAMPLE_RATE)
    t_16 = np.linspace(0, sixteenth_s, n_16, endpoint=False)
    
    for i in range(total_16ths):
        t_pos = i * sixteenth_s
        idx = int(t_pos * SAMPLE_RATE)
        note_name = bass_pattern[i % len(bass_pattern)]
        freq = notes[note_name]
        
        phase = 2 * np.pi * freq * t_16
        saw = 2.0 * (phase / (2 * np.pi) - np.floor(phase / (2 * np.pi) + 0.5))
        sub = np.sin(2 * np.pi * (freq / 2.0) * t_16) * 0.6
        bass_note = (saw * 0.6 + sub) * np.exp(-t_16 * 18.0) * 0.38
        
        vol_duck = 0.3 if (25.0 <= t_pos <= 37.0) else 1.0
        if idx + n_16 <= n_total:
            track_l[idx:idx + n_16] += bass_note * vol_duck
            track_r[idx:idx + n_16] += bass_note * vol_duck
            
    # 4. Melodic Arpeggio
    arp_notes = ['D3', 'F3', 'A3', 'C4', 'D4', 'F4', 'D4', 'A3',
                 'G1', 'D3', 'F3', 'G1', 'A3', 'C4', 'E4', 'D4']
    for i in range(total_16ths):
        t_pos = i * sixteenth_s
        if t_pos < 8.0 or (25.0 <= t_pos <= 37.0):
            continue
        idx = int(t_pos * SAMPLE_RATE)
        freq = notes.get(arp_notes[i % len(arp_notes)], 293.66)
        t_arp = np.linspace(0, sixteenth_s * 1.5, int(sixteenth_s * 1.5 * SAMPLE_RATE), endpoint=False)
        arp_wave = np.sin(2 * np.pi * freq * t_arp) * np.exp(-t_arp * 9.0) * 0.15
        
        pan = 0.5 + 0.3 * np.sin(2 * np.pi * 0.25 * t_pos)
        n_a = len(arp_wave)
        if idx + n_a <= n_total:
            track_l[idx:idx + n_a] += arp_wave * (1.0 - pan)
            track_r[idx:idx + n_a] += arp_wave * pan

    return np.vstack([track_l, track_r])


def overlay_sfx(soundtrack: np.ndarray) -> np.ndarray:
    stereo = np.copy(soundtrack)
    n_total = stereo.shape[1]
    
    def inject(sfx_mono: np.ndarray, t_start_s: float, gain_l: float = 1.0, gain_r: float = 1.0):
        idx = int(t_start_s * SAMPLE_RATE)
        n = len(sfx_mono)
        if idx + n <= n_total:
            stereo[0, idx:idx + n] += sfx_mono * gain_l
            stereo[1, idx:idx + n] += sfx_mono * gain_r
        elif idx < n_total:
            rem = n_total - idx
            stereo[0, idx:] += sfx_mono[:rem] * gain_l
            stereo[1, idx:] += sfx_mono[:rem] * gain_r

    # T=0.0s: Sub-bass boom
    t_boom = np.linspace(0, 1.5, int(1.5 * SAMPLE_RATE), endpoint=False)
    boom = np.sin(2 * np.pi * (55.0 - 20.0 * t_boom) * t_boom) * np.exp(-t_boom * 2.8) * 0.7
    inject(boom, 0.0, 1.0, 1.0)
    
    # T=8.5s: Ingest turbo spool
    t_sp = np.linspace(0, 1.2, int(1.2 * SAMPLE_RATE), endpoint=False)
    spool = np.sin(2 * np.pi * (1200 + 3200 * t_sp) * t_sp) * envelope(len(t_sp), 0.1, 0.3) * 0.25
    inject(spool, 8.5, 0.8, 1.0)
    
    # T=15.0s: Keystroke click
    click = make_noise_burst(0.04, 3200, 2.5, 0.35)
    inject(click, 15.0, 1.0, 0.8)
    
    # T=21.0s - 26.0s: Dyno revving up
    dyno1 = make_engine_sweep(1100, 2400, 5.0, peak=0.45)
    inject(dyno1, 21.0, 1.0, 1.0)
    
    # T=26.0s: CLUTCH SHUDDER & INTERCEPT ALARM (SHOWSTOPPER)
    shudder = make_clutch_shudder(0.75, peak=0.85)
    inject(shudder, 26.0, 1.2, 1.2)
    alarm = make_alarm_horn(10.0, peak=0.65)
    inject(alarm, 26.2, 1.0, 1.0)
    
    # T=36.5s: Self-Correction Loop digital chirps
    inject(make_can_bus_burst(peak=0.35), 36.5, 0.9, 0.9)
    
    # T=40.0s - 45.0s: Second smooth pass
    dyno2 = make_engine_sweep(1500, 4200, 5.0, peak=0.42)
    inject(dyno2, 40.0, 1.0, 1.0)
    
    # T=44.5s: Automotive Relay Click + Confirmation Chime
    relay_chime = make_relay_click_and_chime(peak=0.7)
    inject(relay_chime, 44.5, 1.0, 1.0)
    
    # T=56.0s: Dyno sweep / highway pass
    t_pass = np.linspace(0, 3.0, int(3.0 * SAMPLE_RATE), endpoint=False)
    pass_whoosh = (np.random.rand(len(t_pass)).astype(np.float32) * 2 - 1) * envelope(len(t_pass), 0.5, 1.0) * 0.28
    inject(pass_whoosh, 56.5, 0.5, 1.1)
    
    # T=62.5s: SAM 3.1 Vision scan
    t_v = np.linspace(0, 0.8, int(0.8 * SAMPLE_RATE), endpoint=False)
    vision_sweep = np.sin(2 * np.pi * (3500 - 2200 * t_v) * t_v) * envelope(len(t_v), 0.05, 0.2) * 0.22
    inject(vision_sweep, 62.5, 0.7, 1.0)
    
    # T=68.0s: HIL Flasher CAN-Bus Burst
    inject(make_can_bus_burst(peak=0.4), 68.0, 1.0, 0.8)
    inject(make_can_bus_burst(peak=0.35), 69.5, 0.8, 1.0)
    
    # T=70.0s: Outro Grand Finale Boom
    inject(boom * 1.2, 70.0, 1.0, 1.0)

    max_val = np.max(np.abs(stereo))
    if max_val > 0.98:
        stereo = stereo * (0.95 / max_val)
    return stereo


def build_audio(out_wav: Path, total_dur: float = 74.2) -> Path:
    print(f"Synthesizing 120-BPM motorsport soundtrack ({total_dur:.1f}s)...")
    music = generate_music_track(total_dur)
    print("Overlaying synchronized physical sound effects...")
    master_stereo = overlay_sfx(music)
    pcm16 = (master_stereo.T * 32767.0).astype(np.int16)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(out_wav), SAMPLE_RATE, pcm16)
    print(f"Audio Render Complete: {out_wav}")
    return out_wav


if __name__ == "__main__":
    out = Path("demo_assets/_live_tmp/soundtrack.wav")
    build_audio(out, 74.2)

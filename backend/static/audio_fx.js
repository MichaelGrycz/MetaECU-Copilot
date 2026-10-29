/* MetaECU Motorsport Audio FX — pure Web Audio API synthesis, no audio files.
 *
 *  - spool():  sub-bass turbo spool-up (file .bin dropped / stock loaded)
 *  - alarm():  pulsing ECU overload warning horn (SAFETY GATE INTERCEPT)
 *  - pass():   automotive relay click + soft confirmation chime (GATE PASS)
 *  - power():  short key-on blip when a calibration run starts
 *
 * All sounds honour a single master mute persisted in localStorage.
 * The AudioContext is created lazily on the first user gesture (autoplay policy).
 */
(function () {
  "use strict";

  let ctx = null;
  let master = null;
  let alarmTimer = null;
  let muted = localStorage.getItem("metaecu_muted") === "1";

  function ac() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = muted ? 0 : 0.9;
      master.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  function env(node, t0, a, peak, d) {
    node.gain.setValueAtTime(0.0001, t0);
    node.gain.exponentialRampToValueAtTime(peak, t0 + a);
    node.gain.exponentialRampToValueAtTime(0.0001, t0 + a + d);
  }

  function osc(type, f0, f1, t0, dur, peak) {
    const c = ac();
    if (!c) return;
    const o = c.createOscillator();
    const g = c.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f0, t0);
    if (f1) o.frequency.exponentialRampToValueAtTime(f1, t0 + dur);
    env(g, t0, 0.012, peak, dur);
    o.connect(g).connect(master);
    o.start(t0);
    o.stop(t0 + dur + 0.08);
  }

  function noiseBurst(t0, dur, freq, q, peak) {
    const c = ac();
    if (!c) return;
    const len = Math.max(1, (dur * c.sampleRate) | 0);
    const buf = c.createBuffer(1, len, c.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / len);
    const src = c.createBufferSource();
    src.buffer = buf;
    const bp = c.createBiquadFilter();
    bp.type = "bandpass";
    bp.frequency.value = freq;
    bp.Q.value = q;
    const g = c.createGain();
    env(g, t0, 0.004, peak, dur);
    src.connect(bp).connect(g).connect(master);
    src.start(t0);
  }

  /* --- 1. Turbo spool: sub-bass 38->92 Hz + rising turbine whine ---------- */
  function spool() {
    const c = ac();
    if (!c) return;
    const t = c.currentTime;
    osc("sine", 38, 94, t, 0.9, 0.5); // sub-bass swell
    osc("triangle", 220, 1750, t + 0.08, 0.75, 0.05); // turbine whine
    osc("sawtooth", 55, 110, t, 0.55, 0.07); // exhaust grit
    noiseBurst(t + 0.05, 0.6, 900, 0.8, 0.04); // intake hiss
  }

  /* --- 2. Overload alarm: 3 pulsing two-tone warning horn bursts ---------- */
  function alarmOnce() {
    const c = ac();
    if (!c) return;
    const t = c.currentTime;
    for (let i = 0; i < 3; i++) {
      const t0 = t + i * 0.34;
      osc("square", 620, 620, t0, 0.15, 0.1);
      osc("square", 466, 466, t0 + 0.17, 0.15, 0.1);
    }
  }
  function alarmStart() {
    alarmStop();
    alarmOnce();
    alarmTimer = setInterval(alarmOnce, 1150);
  }
  function alarmStop() {
    if (alarmTimer) {
      clearInterval(alarmTimer);
      alarmTimer = null;
    }
  }

  /* --- 3. Relay click + confirmation chime (checksum PASS) ---------------- */
  function pass() {
    alarmStop();
    const c = ac();
    if (!c) return;
    const t = c.currentTime;
    noiseBurst(t, 0.05, 2400, 1.2, 0.35); // relay contact strike
    noiseBurst(t + 0.07, 0.04, 1800, 1.2, 0.2); // relay settle
    osc("sine", 880, 880, t + 0.1, 0.22, 0.1); // soft confirm A5
    osc("sine", 1318, 1318, t + 0.18, 0.3, 0.08); // E6 tail
  }

  /* --- 4. Key-on blip when a run starts ------------------------------------ */
  function power() {
    const c = ac();
    if (!c) return;
    const t = c.currentTime;
    osc("square", 196, 196, t, 0.09, 0.06);
    osc("square", 294, 294, t + 0.11, 0.12, 0.06);
  }

  /* --- 5. Turbo flutter (stututu / blow-off valve release) ---------------- */
  function flutter() {
    const c = ac();
    if (!c) return;
    const t = c.currentTime;
    // Series of rapidly decaying pressure pulses
    const chirps = [
      { t: 0.0, f: 940, p: 0.18, d: 0.08 },
      { t: 0.09, f: 880, p: 0.15, d: 0.07 },
      { t: 0.17, f: 810, p: 0.12, d: 0.06 },
      { t: 0.24, f: 740, p: 0.09, d: 0.05 },
      { t: 0.3, f: 680, p: 0.06, d: 0.05 },
      { t: 0.36, f: 610, p: 0.03, d: 0.04 },
    ];
    chirps.forEach((ch) => {
      osc("triangle", ch.f, ch.f * 0.75, t + ch.t, ch.d, ch.p);
      noiseBurst(t + ch.t, ch.d * 0.9, ch.f * 1.5, 2.0, ch.p * 0.4);
    });
  }

  function setMuted(m) {
    muted = m;
    localStorage.setItem("metaecu_muted", m ? "1" : "0");
    if (master) master.gain.value = m ? 0 : 0.9;
    if (m) alarmStop();
    updateButton();
  }

  let btn = null;
  function updateButton() {
    if (btn) btn.textContent = muted ? "🔇 AUDIO: OFF" : "🔊 AUDIO: ON";
  }

  function initButton(el) {
    btn = el;
    updateButton();
    btn.addEventListener("click", () => {
      ac();
      setMuted(!muted);
      if (!muted) pass();
    });
  }

  window.MetaFx = { spool, alarmOnce, alarmStart, alarmStop, pass, power, flutter, setMuted, initButton, ac };
})();

/* MetaECU Motorsport Audio FX — pure Web Audio API synthesis, no audio files.
 *
 *  - spool():         sub-bass turbo spool-up (file .bin dropped / stock loaded)
 *  - alarmStart():    pulsing ECU overload warning horn (SAFETY GATE INTERCEPT)
 *  - alarmStop():     stops warning horn
 *  - pass():          automotive relay click + soft confirmation chime (GATE PASS)
 *  - power():         short key-on blip when a calibration run starts
 *  - flutter():       turbo blow-off valve release (wastegate chatter / stututu)
 *  - clutchShudder(): harsh metallic crunch & judder when overtorque limit is breached
 *  - canBusBurst():   digital chirps representing high-speed KWP2000 / CAN bus flashing
 *  - engineSweep():   full acoustic 4-cylinder turbo-diesel dyno sweep (1100 -> 4500 RPM)
 *  - stopEngineSweep(): silences any active dyno run
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
  let activeSweep = null;

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

  /* --- 1. Turbo spool: sub-bass 38->94 Hz + rising turbine whine ---------- */
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

  /* --- 5. Turbo flutter (wastegate chatter / stututu blow-off) ------------- */
  function flutter() {
    const c = ac();
    if (!c) return;
    const t = c.currentTime;
    const chirps = [
      { t: 0.0, f: 940, p: 0.22, d: 0.09 },
      { t: 0.09, f: 870, p: 0.18, d: 0.08 },
      { t: 0.17, f: 790, p: 0.14, d: 0.07 },
      { t: 0.25, f: 710, p: 0.1, d: 0.06 },
      { t: 0.32, f: 630, p: 0.07, d: 0.05 },
      { t: 0.39, f: 550, p: 0.04, d: 0.05 },
    ];
    chirps.forEach((ch) => {
      osc("triangle", ch.f, ch.f * 0.72, t + ch.t, ch.d, ch.p);
      noiseBurst(t + ch.t, ch.d * 0.95, ch.f * 1.6, 2.2, ch.p * 0.45);
    });
  }

  /* --- 6. Clutch shudder (mechanical crunch & harsh judder) ---------------- */
  function clutchShudder() {
    const c = ac();
    if (!c) return;
    const t = c.currentTime;
    osc("sawtooth", 48, 28, t, 0.5, 0.4);
    osc("square", 96, 52, t + 0.02, 0.42, 0.3);
    noiseBurst(t, 0.38, 380, 3.5, 0.45);
    noiseBurst(t + 0.1, 0.3, 580, 4.5, 0.35);
  }

  /* --- 7. CAN-Bus / KWP2000 Flasher digital packet chirps ------------------ */
  function canBusBurst() {
    const c = ac();
    if (!c) return;
    const t = c.currentTime;
    for (let i = 0; i < 5; i++) {
      osc("sine", 3400 + i * 350, 3400 + i * 350, t + i * 0.028, 0.016, 0.05);
    }
  }

  /* --- 8. Full Acoustic 4-Cylinder Turbo-Diesel Engine Dyno Sweep ---------- */
  function stopEngineSweep() {
    if (activeSweep) {
      activeSweep.stop();
      activeSweep = null;
    }
  }

  function engineSweep({
    startRpm = 1100,
    endRpm = 4500,
    duration = 3.6,
    failAtRpm = null,
    onProgress = null,
    onFail = null,
    onDone = null,
  } = {}) {
    stopEngineSweep();
    const c = ac();
    if (!c) {
      if (onDone) onDone();
      return;
    }

    const t0 = c.currentTime;
    const dur = duration;

    // Master bus for this pull
    const pullGain = c.createGain();
    pullGain.gain.setValueAtTime(0.001, t0);
    pullGain.gain.linearRampToValueAtTime(0.38, t0 + 0.18);
    pullGain.connect(master);

    // 1. Primary Crankshaft Firing Frequency (sawtooth: F = RPM / 30 Hz)
    const crankOsc = c.createOscillator();
    crankOsc.type = "sawtooth";
    crankOsc.frequency.setValueAtTime(startRpm / 30, t0);
    crankOsc.frequency.exponentialRampToValueAtTime(endRpm / 30, t0 + dur);

    // Engine block resonator filter
    const blockFilter = c.createBiquadFilter();
    blockFilter.type = "bandpass";
    blockFilter.frequency.setValueAtTime(220, t0);
    blockFilter.Q.value = 2.2;

    // 2. Sub-bass exhaust pipe rumble
    const subOsc = c.createOscillator();
    subOsc.type = "triangle";
    subOsc.frequency.setValueAtTime(startRpm / 60, t0);
    subOsc.frequency.exponentialRampToValueAtTime(endRpm / 60, t0 + dur);
    const subGain = c.createGain();
    subGain.gain.value = 0.55;

    // 3. High-RPM turbocharger spool whistle
    const turboOsc = c.createOscillator();
    turboOsc.type = "sine";
    turboOsc.frequency.setValueAtTime(1600, t0);
    turboOsc.frequency.exponentialRampToValueAtTime(6200, t0 + dur);
    const turboGain = c.createGain();
    turboGain.gain.setValueAtTime(0.001, t0);
    turboGain.gain.linearRampToValueAtTime(0.09, t0 + dur * 0.45);

    // 4. Turbo air intake rush noise
    const noiseLen = Math.max(1, (dur * c.sampleRate) | 0);
    const noiseBuf = c.createBuffer(1, noiseLen, c.sampleRate);
    const nData = noiseBuf.getChannelData(0);
    for (let i = 0; i < noiseLen; i++) nData[i] = Math.random() * 2 - 1;
    const noiseSrc = c.createBufferSource();
    noiseSrc.buffer = noiseBuf;
    const noiseFilter = c.createBiquadFilter();
    noiseFilter.type = "bandpass";
    noiseFilter.frequency.setValueAtTime(1100, t0);
    noiseFilter.frequency.exponentialRampToValueAtTime(3600, t0 + dur);
    noiseFilter.Q.value = 1.3;
    const noiseGain = c.createGain();
    noiseGain.gain.setValueAtTime(0.001, t0);
    noiseGain.gain.linearRampToValueAtTime(0.07, t0 + dur * 0.5);

    // Connections
    crankOsc.connect(blockFilter).connect(pullGain);
    subOsc.connect(subGain).connect(pullGain);
    turboOsc.connect(turboGain).connect(pullGain);
    noiseSrc.connect(noiseFilter).connect(noiseGain).connect(pullGain);

    crankOsc.start(t0);
    subOsc.start(t0);
    turboOsc.start(t0);
    noiseSrc.start(t0);

    const startTime = performance.now();
    let animId = null;
    let stopped = false;

    function cleanup() {
      if (stopped) return;
      stopped = true;
      if (animId) cancelAnimationFrame(animId);
      try {
        const ct = c.currentTime;
        pullGain.gain.setValueAtTime(pullGain.gain.value, ct);
        pullGain.gain.exponentialRampToValueAtTime(0.0001, ct + 0.08);
        setTimeout(() => {
          try {
            crankOsc.stop();
            subOsc.stop();
            turboOsc.stop();
            noiseSrc.stop();
            pullGain.disconnect();
          } catch (e) {}
        }, 110);
      } catch (e) {}
    }

    function tick() {
      if (stopped) return;
      const elapsed = (performance.now() - startTime) / 1000;
      const progress = Math.min(1, elapsed / dur);
      const currentRpm = startRpm + (endRpm - startRpm) * Math.pow(progress, 1.15);

      // Physics-grounded boost and torque values matching our Saab 1.9 TiD Z19DTH
      const boost = 0.25 + 1.3 * Math.min(1, Math.max(0, (currentRpm - 1200) / 750));
      let torque;
      if (failAtRpm && currentRpm >= 1900) {
        // In dangerous 450 Nm run: simulate aggressive overtorque
        torque = 320 + (currentRpm - 1200) * 0.12;
        if (torque > 438.5) torque = 438.5;
      } else {
        // Safe calibrated run (369 Nm peak @ 2000 RPM)
        torque =
          currentRpm < 1800
            ? 250 + (currentRpm - 1100) * 0.17
            : currentRpm <= 3000
              ? 369.0 - (currentRpm - 2000) * 0.035
              : 334.0 - (currentRpm - 3000) * 0.075;
      }
      const hp = ((torque * currentRpm) / 7120) * 1.36; // PS (metric horsepower)

      // Check for failure trigger
      if (failAtRpm && currentRpm >= failAtRpm) {
        cleanup();
        clutchShudder();
        alarmStart();
        if (onFail) onFail(currentRpm, boost, 438.5);
        return;
      }

      if (onProgress) onProgress(currentRpm, boost, hp, torque, progress);

      if (progress >= 1) {
        cleanup();
        flutter(); // wastegate blowoff sound
        setTimeout(() => {
          pass();
          if (onDone) onDone();
        }, 300);
        return;
      }
      animId = requestAnimationFrame(tick);
    }

    animId = requestAnimationFrame(tick);
    activeSweep = { stop: cleanup };
    return activeSweep;
  }

  function setMuted(m) {
    muted = m;
    localStorage.setItem("metaecu_muted", m ? "1" : "0");
    if (master) master.gain.value = m ? 0 : 0.9;
    if (m) {
      alarmStop();
      stopEngineSweep();
    }
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

  window.MetaFx = {
    spool,
    alarmOnce,
    alarmStart,
    alarmStop,
    pass,
    power,
    flutter,
    clutchShudder,
    canBusBurst,
    engineSweep,
    stopEngineSweep,
    setMuted,
    initButton,
    ac,
  };
})();

# MetaECU Copilot — Cinema-Grade Demo Video Script (110s)

**Format:** 1080p Full HD @ 30 FPS, stereo motorsport synthwave audio + physical acoustic FX, burned-in subtitles.  
**Length:** 1 minute 50 seconds (110.0 seconds) — fast-paced, high engagement.  
**Video File:** `demo_assets/MetaECU_Copilot_Demo.mp4` (11.5 MB)  
**Live URL:** `https://michaelgrycz--metaecu-copilot-web.us-east.modal.run`  
**GitHub:** `https://github.com/MichaelGrycz/MetaECU-Copilot`  

---

## 🎬 Edit Decision List (EDL) & Narration Script

| Time | Scene | On-Screen Visual | Audio Design / SFX | Narration (EN) |
|---|---|---|---|---|
| **0:00–0:04** | 01. Hook & Title | MetaECU Copilot motorsport title card, glowing cyan accents, Meta Hackathon 2026 badge. | Deep sub-bass boom + high-tech riser whoosh | "Every AI tuning tool today is a chatbot guessing numbers. MetaECU Copilot is completely different." |
| **0:04–0:09** | 02. Rule Compliance | Split compliance card: Pre-existing assets vs Built entirely this week during hackathon. | Digital pulse rhythm begins | "Pre-existing was our raw binary and catalogue; built entirely this week is our autonomous, verifiable calibration engine." |
| **0:09–0:14** | 03. Stage 1 Ingest | Macro zoom into ECU Hardware card: Bosch EDC16C39, Motorola MPC562, Checksum 0xD01FE500. | Low turbo spool-up whistle + mechanical click | "We ingest the real stock flash of a Bosch EDC16C39 with 774 defined maps, axes, and physical units." |
| **0:14–0:19** | 04. Stage 2 Intent | Tuner input: "Give me 450 Nm, maximum power" (Aggressive Boundary Test), Muse Spark 1.3 selected. | Mechanical keyboard keystroke click | "The tuner sets their goal in natural language: 'Give me 450 Nm, maximum power' — an aggressive boundary test." |
| **0:19–0:24** | 05. AI War Room | Close-up on AI Thought Stream: Muse Spark vectoring indicated torque & rail ceiling across 774 symbols. | High-frequency data processing pulses | "Meta Muse Spark plans the calibration as structured JSON, vectoring indicated torque across 774 symbols." |
| **0:24–0:30** | 06. Virtual Dyno #1 | Virtual Dyno Cell: Tachometer and boost needles sweeping up as engine revs climb towards 2200 RPM. | Real engine acceleration roar + turbo boost building | "We spin up the Virtual Dyno Cell. The engine revs and boost builds toward 2200 RPM..." |
| **0:30–0:37** | 07. CLUTCH INTERCEPT | Flashing crimson alert: `CRITICAL SAFETY INTERCEPT: 438.5 Nm > 377 Nm GM F40 LIMIT!`. Red overload zone. | **METALLIC CLUTCH SHUDDER + PULSING ALARM KLAKSON** | "CRITICAL SAFETY INTERCEPT! The deterministic gate detects clutch shear breakaway on the GM F40 transmission!" |
| **0:37–0:43** | 08. Physics Gate | Physics calculation: Indicated (450 Nm) minus Friction @ 90°C = 438.5 Nm > 377 Nm clutch limit. | Warning alarm subsides, diagnostic beep | "A human tuner or naive LLM would slip the clutch and destroy the dual-mass flywheel. MetaECU halts it." |
| **0:43–0:49** | 09. Self-Correction | Thought Stream: Violation report sent back into Muse Spark. Autonomous recalculation clamping to 369 Nm. | High-tech whoosh + rapid replanning digital chirp | "The violation report feeds back into our self-correction loop. Muse autonomously replans inside the safe envelope." |
| **0:49–0:55** | 10. Dyno Pull #2 PASS | Second pull runs silky smooth: tachometer sweeps cleanly to redline, green badge: `PASS: 185.4 HP / 369 Nm`. | Smooth engine pass + **automotive relay click + confirmation chime** | "Attempt two passes! 369 Nm effective torque, 1600 bar rail pressure, zero slip, and 185.4 horsepower." |
| **0:55–1:01** | 11. 3D Map Studio | Full-screen interactive 3D WebGL map surface with surgical delta difference heatmap. | Subtle holographic sweep whoosh | "In the 3D Map Studio, visual grounding inspects the exact surgical delta applied to the calibration tables." |
| **1:01–1:08** | 12. Ghost Car Drag | Side-by-side road telemetry animation (33 WOT sessions): Stock 4.90s boost lag vs MetaECU 1.34s (-3.56s faster!). | Turbo spool + rushing highway pass whoosh | "Our Ghost Car simulator replays 33 real highway sessions: stock turbo lag took 4.90s; MetaECU hits 1.55 bar in 1.34s!" |
| **1:08–1:15** | 13. SAM 3.1 Vision | Uploaded dyno chart segmented by SAM 3.1, detecting torque valley at 2400 RPM and geometry recommendation. | Laser vision scan sweep / radar ping | "SAM 3.1 Vision Studio analyzes dyno graphs, grounds torque valleys, and optimizes turbo geometry." |
| **1:15–1:22** | 14. HIL Flasher | KWP2000 / UDS diagnostic protocol terminal over CAN 500 kbps: Seed-Key challenge unlocked by Meta AI. | Rapid CAN-bus packet chirp chatter | "To flash the hardware, our HIL flasher executes genuine KWP2000 diagnostic protocols over CAN 500 kbps." |
| **1:22–1:29** | 15. Checksum Sealing | Sealed binary notification: Additive sum `0xD01FE500` verified, exact 2,097,152 bytes ready for download. | Heavy metallic vault latch sound effect | "The binary is sealed with a verified 32-bit Bosch checksum — 0xD01FE500 — ready for immediate vehicle flashing." |
| **1:29–1:35** | 16. Digital Assets | Official Certificate of Safe Calibration (cryptographic proof) + HTML Motorsport Spec Card with QR. | Confirmation glass chime | "Every calibration ships with an Official Certificate of Safe Calibration and motorsport spec card." |
| **1:35–1:42** | 17. Multiplatform | Modal serverless cloud, native zero-console Windows `.exe`, and installable PWA shown side by side. | Rising synth chord | "Deployable 24/7 on Modal serverless cloud, as a native zero-console desktop app, or headless CLI." |
| **1:42–1:50** | 18. Grand Finale | Closing card: Architecture diagram, Live Modal URL, GitHub repo, Meta Global AI Hackathon badge. | Final climactic synth chord + sub-bass outro hit | "AI that proposes. Physics that disposes. MetaECU Copilot. Try the live demo at our Modal cloud link!" |

---

## 🛠️ Reproduction & Regeneration

To regenerate the video and soundtrack at any time:
```bash
python tools/build_cinematic_audio.py   # Synthesizes 48kHz stereo soundtrack with motorsport SFX
python tools/build_cinematic_video.py   # Compiles 18-scene Full HD video -> demo_assets/MetaECU_Copilot_Demo.mp4
```

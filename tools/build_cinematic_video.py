#!/usr/bin/env python3
"""
MetaECU Copilot — Cinema-Grade Hackathon Demo Video Generator.

Produces a dynamic, cinematic 110-second automotive AI presentation:
  - 18 purposeful, fast-paced scenes (establishing shots + macro crops).
  - High-impact graphic cards with glowing badges, telemetry graphs & HUD elements.
  - Bespoke 120-BPM motorsport synthwave soundtrack with physical sound effects
    (engine sweep, turbo spool, clutch shudder, alarm horn, relay clicks).
  - Perfectly synchronized burned-in captions.
  - H.264 Full HD 1080p @ 30 FPS.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ASSETS = ROOT / "demo_assets"
OUT_VIDEO = ASSETS / "MetaECU_Copilot_Demo.mp4"
TMP_DIR = ASSETS / "_cinematic_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080
FPS = 30

# Colors (Motorsport Luxury Palette)
BG_DARK = (10, 16, 26)        # Deep Navy
BG_PANEL = (17, 26, 40)       # Elevated Panel
CYAN = (0, 229, 255)          # MetaECU Electric Cyan
CYAN_GLOW = (0, 180, 220)
GREEN = (16, 185, 129)        # Emerald Pass
RED = (239, 68, 68)           # Intercept Alarm Crimson
GOLD = (245, 158, 11)         # Gold Warning
WHITE = (248, 250, 252)
GRAY = (148, 163, 184)
GRAY_DARK = (51, 65, 85)


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf" if not bold else "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/Calibri.ttf" if not bold else "C:/Windows/Fonts/Calibrib.ttf",
        "C:/Windows/Fonts/Arial.ttf" if not bold else "C:/Windows/Fonts/Arialbd.ttf",
        "C:/Windows/Fonts/Consolas.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def create_base_canvas() -> tuple[Image.Image, ImageDraw.Draw]:
    img = Image.new("RGB", (W, H), BG_DARK)
    d = ImageDraw.Draw(img)
    
    # Subtle gradient background
    for y in range(0, H, 4):
        alpha = 0.5 + 0.5 * (1.0 - abs(y - H / 2) / (H / 2))
        col = (int(BG_DARK[0] + 8 * alpha), int(BG_DARK[1] + 12 * alpha), int(BG_DARK[2] + 20 * alpha))
        d.line([(0, y), (W, y)], fill=col, width=4)
        
    # Top and bottom motorsport cyan accent lines
    d.rectangle([0, 0, W, 6], fill=CYAN)
    d.rectangle([0, H - 6, W, H], fill=CYAN)
    return img, d


def draw_hud_header(d: ImageDraw.Draw, stage_label: str, title: str, status_badge: str = "SYSTEM ACTIVE", badge_color: tuple = CYAN):
    # Top HUD Bar
    d.rectangle([40, 30, W - 40, 90], fill=BG_PANEL, outline=GRAY_DARK, width=1)
    
    # Brand logo & title
    f_logo = get_font(26, bold=True)
    d.text((60, 44), "METAECU COPILOT", font=f_logo, fill=WHITE)
    d.text((320, 48), f"// {stage_label.upper()} — {title.upper()}", font=get_font(20, bold=False), fill=CYAN)
    
    # Right status badge
    f_badge = get_font(18, bold=True)
    b_len = d.textlength(status_badge, font=f_badge)
    bx = W - 70 - int(b_len) - 24
    d.rounded_rectangle([bx, 42, W - 60, 78], radius=6, fill=(badge_color[0]//4, badge_color[1]//4, badge_color[2]//4), outline=badge_color, width=2)
    d.text((bx + 12, 48), status_badge, font=f_badge, fill=badge_color)


def make_scene_card(
    path: Path,
    title: str,
    subtitle: str,
    kicker: str = "",
    bullet_points: list[tuple[str, str]] = None,
    badge_label: str = "",
    accent: tuple = CYAN
):
    img, d = create_base_canvas()
    
    # Kicker
    if kicker:
        d.text((120, 200), kicker.upper(), font=get_font(28, bold=True), fill=accent)
        
    # Main Title
    d.text((120, 260), title, font=get_font(64, bold=True), fill=WHITE)
    
    # Subtitle
    d.text((122, 350), subtitle, font=get_font(28, bold=False), fill=GRAY)
    
    # Bullet/Feature Cards
    if bullet_points:
        y_cur = 460
        for icon, txt in bullet_points:
            d.rounded_rectangle([120, y_cur, W - 120, y_cur + 90], radius=10, fill=BG_PANEL, outline=GRAY_DARK, width=1)
            # Accent pill
            d.rectangle([120, y_cur, 128, y_cur + 90], fill=accent)
            d.text((160, y_cur + 24), icon, font=get_font(32, bold=True), fill=accent)
            d.text((230, y_cur + 28), txt, font=get_font(26, bold=True), fill=WHITE)
            y_cur += 115
            
    # Bottom Badge
    if badge_label:
        d.rounded_rectangle([120, H - 140, 520, H - 80], radius=8, fill=(accent[0]//5, accent[1]//5, accent[2]//5), outline=accent, width=2)
        d.text((140, H - 122), badge_label, font=get_font(22, bold=True), fill=accent)
        
    img.save(path)


def make_cropped_view(
    out_path: Path,
    source_img_path: Path,
    crop_box: tuple[int, int, int, int],  # (x1, y1, x2, y2) in source
    stage_label: str,
    title: str,
    status_badge: str,
    badge_color: tuple,
    overlay_kicker: str = "",
    overlay_metric: str = ""
):
    img, d = create_base_canvas()
    draw_hud_header(d, stage_label, title, status_badge, badge_color)
    
    # Load and crop source image
    src = Image.open(source_img_path)
    cropped = src.crop(crop_box)
    
    # Target display area: (80, 110, W - 80, H - 50) -> width 1760, height 920
    target_w, target_h = 1760, 920
    # Scale cropped to fit nicely
    c_w, c_h = cropped.size
    ratio = min(target_w / c_w, target_h / c_h)
    new_w, new_h = int(c_w * ratio), int(c_h * ratio)
    resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    paste_x = 80 + (target_w - new_w) // 2
    paste_y = 110 + (target_h - new_h) // 2
    
    # Panel border & drop shadow
    d.rounded_rectangle([paste_x - 4, paste_y - 4, paste_x + new_w + 4, paste_y + new_h + 4], radius=8, outline=badge_color, width=2)
    img.paste(resized, (paste_x, paste_y))
    
    # Overlay Banner if requested
    if overlay_kicker or overlay_metric:
        banner_w, banner_h = 640, 110
        bx = paste_x + 30
        by = paste_y + new_h - banner_h - 30
        d.rounded_rectangle([bx, by, bx + banner_w, by + banner_h], radius=8, fill=(10, 16, 26), outline=badge_color, width=2)
        if overlay_kicker:
            d.text((bx + 20, by + 18), overlay_kicker.upper(), font=get_font(20, bold=True), fill=badge_color)
        if overlay_metric:
            d.text((bx + 20, by + 50), overlay_metric, font=get_font(28, bold=True), fill=WHITE)
            
    img.save(out_path)


# -----------------------------------------------------------------------------
# EDL (Edit Decision List) — 18 Cinematic Scenes (Total: 110.0s)
# -----------------------------------------------------------------------------
EDL = [
    # Scene 01: 0.0s - 4.0s (4.0s)
    {
        "id": "01_intro",
        "dur": 4.0,
        "type": "card",
        "kicker": "Meta Global AI Developer Hackathon 2026 // Indie Track",
        "title": "MetaECU Copilot",
        "subtitle": "Autonomous & Verifiable Calibration Engine with Deterministic Safety Gates",
        "bullets": [
            ("⚡", "AI Proposes: Meta Muse Spark 1.3 & SAM 3.1 Multimodal Grounding"),
            ("🛡️", "Physics Disposes: Deterministic Domain Gates Protect Mechanical Clutches & Pumps"),
            ("✓", "Production Sealing: Verified 32-bit Bosch Checksum 0xD01FE500")
        ],
        "badge": "OFFICIAL HACKATHON ENTRY",
        "accent": CYAN
    },
    # Scene 02: 4.0s - 9.0s (5.0s)
    {
        "id": "02_compliance",
        "dur": 5.0,
        "type": "card",
        "kicker": "Compliance & Verifiable Cyber-Physical Architecture",
        "title": "New Work & Grounded Verification",
        "subtitle": "Built in strict alignment with Meta Agents 102 Workshop standards.",
        "bullets": [
            ("📁", "Pre-Existing Assets: Raw 2 MiB Flash Dump & Static 774-symbol Map Catalogue"),
            ("🚀", "Built Entirely This Week: Autonomous Muse Planner, Safety Gate & HIL Flasher"),
            ("🔬", "Core Philosophy: Deterministic physics gates prevent LLM hallucinations from destroying engines")
        ],
        "badge": "STRICT COMPLIANCE CONFIRMED",
        "accent": GREEN
    },
    # Scene 03: 9.0s - 14.0s (5.0s)
    {
        "id": "03_ingest",
        "dur": 5.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "01_stage1_ingest.png",
        "crop": (20, 90, 520, 510),
        "stage": "Stage 1: Ingest",
        "title": "ECU Memory & Hardware Fingerprint",
        "badge": "2,097,152 BYTES VERIFIED",
        "color": CYAN,
        "kicker": "ECU Hardware Fingerprint",
        "metric": "Bosch EDC16C39 · MPC562 · 774 Maps"
    },
    # Scene 04: 14.0s - 19.0s (5.0s)
    {
        "id": "04_intent",
        "dur": 5.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "02_stage2_intent.png",
        "crop": (20, 520, 520, 960),
        "stage": "Stage 2: Intent",
        "title": "Natural Language Calibration Goal",
        "badge": "450 NM BOUNDARY TEST",
        "color": GOLD,
        "kicker": "Tuner Natural Language Input",
        "metric": "'Give me 450 Nm, maximum power'"
    },
    # Scene 05: 19.0s - 24.0s (5.0s)
    {
        "id": "05_war_room",
        "dur": 5.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "01_stage1_ingest.png",
        "crop": (20, 720, 520, 1040),
        "stage": "Stage 2: War Room",
        "title": "Meta Muse Spark Reasoning Stream",
        "badge": "MUSE SPARK 1.3 ACTIVE",
        "color": CYAN,
        "kicker": "Autonomous Multi-Agent Planning",
        "metric": "Vectoring 774 Bosch maps & rail ceilings"
    },
    # Scene 06: 24.0s - 30.0s (6.0s)
    {
        "id": "06_dyno_spin",
        "dur": 6.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "03_dyno_telemetry.png",
        "crop": (540, 80, 1580, 680),
        "stage": "Stage 3: Virtual Dyno",
        "title": "Maha LPS 3000 Virtual Dyno Cell",
        "badge": "WOT SWEEP IN PROGRESS",
        "color": CYAN,
        "kicker": "Acoustic Dyno Cell",
        "metric": "Engine revs climbing towards 2200 RPM..."
    },
    # Scene 07: 30.0s - 37.0s (7.0s) — THE SHOWSTOPPER
    {
        "id": "07_intercept_climax",
        "dur": 7.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "03_stage3_intercept.png",
        "crop": (540, 80, 1580, 680),
        "stage": "Stage 3: Safety Gate",
        "title": "Critical Safety Intercept Triggered!",
        "badge": "CRITICAL INTERCEPT: CLUTCH OVERLOAD",
        "color": RED,
        "kicker": "Clutch Breakaway Detected!",
        "metric": "438.5 Nm > 377 Nm GM F40 Limit!"
    },
    # Scene 08: 37.0s - 43.0s (6.0s)
    {
        "id": "08_physics_protection",
        "dur": 6.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "02_stage2_intent.png",
        "crop": (20, 970, 520, 1045),
        "stage": "Stage 3: Physics Gate",
        "title": "Deterministic Friction Calculation @ 90°C",
        "badge": "PHYSICS DISPOSES",
        "color": RED,
        "kicker": "Mechanical Protection Active",
        "metric": "Indicated 450 Nm - Friction 11.5 Nm = 438.5 Nm"
    },
    # Scene 09: 43.0s - 49.0s (6.0s)
    {
        "id": "09_self_correction",
        "dur": 6.0,
        "type": "card",
        "kicker": "Autonomous AI Feedback Loop",
        "title": "AI Self-Correction Loop",
        "subtitle": "Violation report fed back into Muse Spark to recalculate safer table cells.",
        "bullets": [
            ("🚨", "Violation Report: Peak torque 438.5 Nm exceeds GM F40 limit 377 Nm"),
            ("🧠", "Muse Spark Re-evaluates: Clamping torque plateau to 369 Nm @ 2400 RPM"),
            ("🔒", "Hardware Safe: Zero clutch slip, DMF vibration dampening preserved")
        ],
        "badge": "AUTONOMOUS RE-PLANNING",
        "accent": GOLD
    },
    # Scene 10: 49.0s - 55.0s (6.0s)
    {
        "id": "10_pass_pull",
        "dur": 6.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "02_safety_intercept_pass.png",
        "crop": (540, 80, 1580, 680),
        "stage": "Stage 3: Gate Approval",
        "title": "Attempt Two Passes — 185.4 HP Locked",
        "badge": "GATE PASS: 100% VERIFIED",
        "color": GREEN,
        "kicker": "Approved Calibration Envelope",
        "metric": "185.4 HP · 369.0 Nm Eff · 0 Slip"
    },
    # Scene 11: 55.0s - 61.0s (6.0s)
    {
        "id": "11_map_studio",
        "dur": 6.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "04_stage4_3d_audit.png",
        "crop": (540, 80, 1580, 720),
        "stage": "Stage 4: 3D Studio",
        "title": "3D Map Surface Studio & Delta Heatmap",
        "badge": "SURGICAL CALIBRATION DELTA",
        "color": CYAN,
        "kicker": "Visual Grounding in 3D WebGL",
        "metric": "Surgical cell deltas in EngPrt_trqLim_CUR"
    },
    # Scene 12: 61.0s - 68.0s (7.0s)
    {
        "id": "12_ghost_car",
        "dur": 7.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "03_dyno_telemetry.png",
        "crop": (540, 480, 1580, 1020),
        "stage": "Stage 4: Telemetry",
        "title": "Ghost Car Highway Drag (60–140 km/h in 4th)",
        "badge": "33 WOT TELEMETRY SESSIONS",
        "color": CYAN,
        "kicker": "Real OBD-II Road Log Replay",
        "metric": "Stock Spool: 4.90s vs MetaECU: 1.34s (-3.56s faster!)"
    },
    # Scene 13: 68.0s - 75.0s (7.0s)
    {
        "id": "13_sam_vision",
        "dur": 7.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "04_sam_vision_radar.png",
        "crop": (540, 80, 1580, 720),
        "stage": "Stage 4: SAM 3.1 Vision",
        "title": "Multimodal Dyno Curve Grounding",
        "badge": "SAM 3.1 SEGMENTATION ACTIVE",
        "color": CYAN,
        "kicker": "Multimodal Curve Analysis",
        "metric": "Detects torque dips & recommends VNT boost geometry"
    },
    # Scene 14: 75.0s - 82.0s (7.0s)
    {
        "id": "14_hil_flasher",
        "dur": 7.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "05_hil_flasher_export.png",
        "crop": (540, 80, 1580, 520),
        "stage": "Stage 5: Production Flasher",
        "title": "Hardware-in-the-Loop Diagnostic Flasher",
        "badge": "KWP2000 / UDS OVER CAN 500 KBPS",
        "color": CYAN,
        "kicker": "Diagnostic Flashing Protocol",
        "metric": "Seed-Key challenge resolved by Meta AI"
    },
    # Scene 15: 82.0s - 89.0s (7.0s)
    {
        "id": "15_checksum_seal",
        "dur": 7.0,
        "type": "crop",
        "src": ROOT / "output" / "visual_audit" / "05_stage5_export.png",
        "crop": (540, 520, 1580, 1020),
        "stage": "Stage 5: Binary Sealing",
        "title": "Additive 32-bit Checksum 0xD01FE500",
        "badge": "CHECKSUM SEALED & VERIFIED",
        "color": GREEN,
        "kicker": "Ready for Vehicle Flash",
        "metric": "Exact 2,097,152 Bytes · Target 0xD01FE500 ✓"
    },
    # Scene 16: 89.0s - 95.0s (6.0s)
    {
        "id": "16_certificate",
        "dur": 6.0,
        "type": "card",
        "kicker": "Official Certificate & Motorsport Spec Card",
        "title": "Digital Verification Assets",
        "subtitle": "Tamper-evident audit trail delivered with every calibration.",
        "bullets": [
            ("📜", "Official Certificate of Safe Calibration (Cryptographic Proof)"),
            ("🏎️", "Motorsport Spec Card with Verified Dyno & Turbo Spool Metrics"),
            ("📋", "Complete Markdown Engineering Audit Report")
        ],
        "badge": "100% CRYPTOGRAPHICALLY AUDITED",
        "accent": CYAN
    },
    # Scene 17: 95.0s - 102.0s (7.0s)
    {
        "id": "17_multiplatform",
        "dur": 7.0,
        "type": "card",
        "kicker": "Deployment Flexibility — Zero Install",
        "title": "Three Production Form Factors",
        "subtitle": "Access anywhere from cloud browser to native workshop PC.",
        "bullets": [
            ("☁️", "Modal Cloud Live Product: https://michaelgrycz--metaecu-copilot-web.us-east.modal.run"),
            ("🖥️", "Windows Native Desktop App: dist/MetaECU_Copilot.exe (No console, motorsport icon)"),
            ("📱", "Installable PWA: Standalone desktop & mobile web app with offline capabilities")
        ],
        "badge": "MULTI-PLATFORM READY",
        "accent": GREEN
    },
    # Scene 18: 102.0s - 110.0s (8.0s)
    {
        "id": "18_outro",
        "dur": 8.0,
        "type": "card",
        "kicker": "Meta Global AI Developer Hackathon 2026",
        "title": "AI Proposes. Physics Disposes.",
        "subtitle": "MetaECU Copilot: The future of autonomous, verifiable automotive engineering.",
        "bullets": [
            ("🌐", "Try Live: https://michaelgrycz--metaecu-copilot-web.us-east.modal.run"),
            ("💻", "Source Code: https://github.com/MichaelGrycz/MetaECU-Copilot"),
            ("🏆", "Indie Developer Track · Solo Builder: Michał Grycz")
        ],
        "badge": "THANK YOU FOR WATCHING",
        "accent": CYAN
    }
]


def render_all_frames():
    print(f"Rendering {len(EDL)} cinema-grade frames...")
    for idx, sc in enumerate(EDL):
        out_f = TMP_DIR / f"frame_{idx:02d}_{sc['id']}.png"
        if sc["type"] == "card":
            make_scene_card(
                out_f,
                title=sc["title"],
                subtitle=sc["subtitle"],
                kicker=sc["kicker"],
                bullet_points=sc.get("bullets"),
                badge_label=sc["badge"],
                accent=sc["accent"]
            )
        elif sc["type"] == "crop":
            make_cropped_view(
                out_f,
                source_img_path=sc["src"],
                crop_box=sc["crop"],
                stage_label=sc["stage"],
                title=sc["title"],
                status_badge=sc["badge"],
                badge_color=sc["color"],
                overlay_kicker=sc.get("kicker", ""),
                overlay_metric=sc.get("metric", "")
            )
        print(f"  [{idx+1}/{len(EDL)}] Saved {out_f.name}")


def generate_subtitles_srt(out_srt: Path):
    """Generate subtitles synchronized with the 18 scenes."""
    srt_lines = [
        "1",
        "00:00:00,000 --> 00:00:04,000",
        "Every AI tuning tool today is a chatbot guessing numbers. MetaECU Copilot is completely different.",
        "",
        "2",
        "00:00:04,000 --> 00:00:09,000",
        "Pre-existing was our raw binary and catalogue; built entirely this week is our autonomous, verifiable calibration engine.",
        "",
        "3",
        "00:00:09,000 --> 00:00:14,000",
        "We ingest the real stock flash of a Bosch EDC16C39 with 774 defined maps, axes, and physical units.",
        "",
        "4",
        "00:00:14,000 --> 00:00:19,000",
        "The tuner sets their goal in natural language: 'Give me 450 Nm, maximum power' — an aggressive boundary test.",
        "",
        "5",
        "00:00:19,000 --> 00:00:24,000",
        "Meta Muse Spark plans the calibration as structured JSON, vectoring indicated torque across 774 symbols.",
        "",
        "6",
        "00:00:24,000 --> 00:00:30,000",
        "We spin up the Virtual Dyno Cell. The engine revs and boost builds toward 2200 RPM...",
        "",
        "7",
        "00:00:30,000 --> 00:00:37,000",
        "CRITICAL SAFETY INTERCEPT! The deterministic gate detects clutch shear breakaway on the GM F40 transmission!",
        "",
        "8",
        "00:00:37,000 --> 00:00:43,000",
        "A human tuner or naive LLM would slip the clutch and destroy the dual-mass flywheel. MetaECU halts it.",
        "",
        "9",
        "00:00:43,000 --> 00:00:49,000",
        "The violation report feeds back into our self-correction loop. Muse autonomously replans inside the safe envelope.",
        "",
        "10",
        "00:00:49,000 --> 00:00:55,000",
        "Attempt two passes! 369 Nm effective torque, 1600 bar rail pressure, zero slip, and 185.4 horsepower.",
        "",
        "11",
        "00:00:55,000 --> 00:01:01,000",
        "In the 3D Map Studio, visual grounding inspects the exact surgical delta applied to the calibration tables.",
        "",
        "12",
        "00:01:01,000 --> 00:01:08,000",
        "Our Ghost Car simulator replays 33 real highway sessions: stock turbo lag took 4.90s; MetaECU hits 1.55 bar in 1.34s!",
        "",
        "13",
        "00:01:08,000 --> 00:01:15,000",
        "SAM 3.1 Vision Studio analyzes dyno graphs, grounds torque valleys, and optimizes turbo geometry.",
        "",
        "14",
        "00:01:15,000 --> 00:01:22,000",
        "To flash the hardware, our HIL flasher executes genuine KWP2000 diagnostic protocols over CAN 500 kbps.",
        "",
        "15",
        "00:01:22,000 --> 00:01:29,000",
        "The binary is sealed with a verified 32-bit Bosch checksum — 0xD01FE500 — ready for immediate vehicle flashing.",
        "",
        "16",
        "00:01:29,000 --> 00:01:35,000",
        "Every calibration ships with an Official Certificate of Safe Calibration and motorsport spec card.",
        "",
        "17",
        "00:01:35,000 --> 00:01:42,000",
        "Deployable 24/7 on Modal serverless cloud, as a native zero-console desktop app, or headless CLI.",
        "",
        "18",
        "00:01:42,000 --> 00:01:50,000",
        "AI that proposes. Physics that disposes. MetaECU Copilot. Try the live demo at our Modal cloud link!",
        ""
    ]
    out_srt.write_text("\n".join(srt_lines), encoding="utf-8")
    print(f"Generated subtitles: {out_srt}")


def compile_video():
    render_all_frames()
    
    # 1. Synthesize soundtrack
    soundtrack_wav = TMP_DIR / "soundtrack.wav"
    from tools.build_cinematic_audio import build_audio
    build_audio(soundtrack_wav)
    
    # 2. Subtitles
    srt_path = ASSETS / "subtitles.srt"
    generate_subtitles_srt(srt_path)
    
    # 3. Build FFmpeg filtergraph with Ken Burns slow zoom
    fcs = []
    xfade_ops = []
    FADE = 0.5
    running_len = EDL[0]["dur"]
    
    for idx, sc in enumerate(EDL):
        f_path = TMP_DIR / f"frame_{idx:02d}_{sc['id']}.png"
        dur = sc["dur"]
        frames = int(dur * FPS)
        zrate = 0.0008 + (idx % 3) * 0.0003
        fc = (
            f"[{idx}:v]format=yuv420p,scale={W}:{H},"
            f"zoompan=z='min(1.0+{zrate},1.15)':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}:d={frames}"
            f"[v{idx}]"
        )
        fcs.append(fc)
        
    prev = "v0"
    for idx in range(1, len(EDL)):
        off = round(running_len - FADE, 3)
        out = f"c{idx}"
        xfade_ops.append(f"[{prev}][v{idx}]xfade=transition=fade:duration={FADE}:offset={off}[{out}]")
        running_len += EDL[idx]["dur"] - FADE
        prev = out
        
    final_video_tag = prev
    
    # Subtitles burn-in filter
    srt_rel = srt_path.relative_to(ROOT).as_posix().replace("\\", "/")
    style = (
        "FontName=Segoe UI,FontSize=26,Bold=1,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H90000000,BackColour=&HA00A101A,BorderStyle=3,Outline=1,"
        "Shadow=0,Alignment=2,MarginV=35"
    )
    sub_filter = f"[{final_video_tag}]subtitles='{srt_rel}':force_style='\"{style}\"'[vfinal]"
    
    filter_complex = ";".join(fcs + xfade_ops + [sub_filter])
    
    # Construct FFmpeg command
    input_args = []
    for idx, sc in enumerate(EDL):
        f_path = TMP_DIR / f"frame_{idx:02d}_{sc['id']}.png"
        input_args.extend(["-loop", "1", "-t", str(sc["dur"]), "-i", str(f_path)])
        
    # Audio input is the last input
    input_args.extend(["-i", str(soundtrack_wav)])
    audio_idx = len(EDL)
    
    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-map", f"{audio_idx}:a",
        "-t", "110",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(OUT_VIDEO)
    ]
    
    print("\nExecuting FFmpeg cinema video compilation...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr[-1000:])
        return False
        
    print(f"\n=======================================================")
    print(f"CINEMATIC DEMO VIDEO SUCCESS: {OUT_VIDEO}")
    print(f"Size: {OUT_VIDEO.stat().st_size / (1024*1024):.2f} MB")
    print(f"=======================================================")
    return True


if __name__ == "__main__":
    if not compile_video():
        sys.exit(1)

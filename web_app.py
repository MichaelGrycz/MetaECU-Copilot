"""
MetaECU Interactive Tuning Cockpit & Multimodal SAM Vision Studio.

    python backend/web_app.py        ->  http://localhost:8000
    (or: python web_app.py from the repo root)

FastAPI backend + single-page cockpit (Tailwind + Plotly via CDN).
All physics decisions stay in the deterministic Safety Gate; the web layer
only transports bytes and streams progress events (SSE Thought Stream).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

_f = Path(__file__).resolve()
ROOT = _f.parents[1] if _f.parent.name == "backend" else _f.parent
# Optional asset override for slim deployments (Modal container, PyInstaller EXE):
# METAECU_ASSET_ROOT points at a staged tree containing only the files the
# cockpit needs (stock .bin, map catalogue, road telemetry CSVs).
ASSET_ROOT = Path(os.environ.get("METAECU_ASSET_ROOT", str(ROOT)))
# Writable output dir: /tmp on Modal (read-only image), beside the EXE on Windows.
OUT_ROOT = Path(
    os.environ.get(
        "METAECU_OUTPUT_DIR", str(Path(tempfile.gettempdir()) / "metaecu_web")
    )
)
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    Response,
    StreamingResponse,
)

from backend import telemetry_cockpit, voice_ingest
from backend.ai_engine import muse_patcher
from backend.ai_engine.muse_planner import MusePlanner
from backend.ai_engine.sam_vision_live import analyze_dyno_image
from backend.binary_core.flash_loader import EXPECTED_SIZE, FlashImage, load_flash
from backend.binary_core.map_reader import Catalog
from backend.safety_engine import safety_gate
from backend.safety_engine.orchestrator import run_calibration

SAAB = ASSET_ROOT / "01_SAAB_9-3_1.9TID_EDC16C39"
STOCK_BIN = (
    SAAB / "02_PLIKI_SERYJNE_I_BAZOWE" / "SAAB 93 tid 2008 edc16c39 1037389375.Bin"
)
CATALOG_PATH = (
    SAAB / "03_DEFINICJE_MAP_XDF" / "BOSCH_EDC16C39_1037389375_COMPLETE_CATALOG.json"
)
STATIC = ROOT / "backend" / "static"
OUT = OUT_ROOT
OUT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MetaECU Copilot Cockpit")
CATALOG = Catalog(CATALOG_PATH)
STATE: dict = {"stock": None, "tuned": None, "report": None, "intent": ""}

MAP_CHOICES = [
    "EngPrt_trqLim_CUR",
    "EngM_trqFrc_MAP",
    "Rail_pSetPointBase_MAP",
    "PCR_pDesBas_MAP",
    "InjCrv_phiMI1Bas1_MAP",
    "FlMng_rLmbdSmkLow_MAP",
]


def _ecu_meta(flash: FlashImage, name: str) -> dict:
    return {
        "file": name,
        "ecu": "Bosch EDC16C39",
        "software": "1037389375",
        "hardware": "0281014551",
        "vehicle": "Saab 9-3 1.9 TiD (Z19DTH), GM F40",
        "size_bytes": len(flash),
        "size_ok": len(flash) == EXPECTED_SIZE,
        "checksum": f"0x{flash.compute_checksum():08X}",
        "checksum_ok": flash.checksum_ok(),
        "catalog_symbols": len(CATALOG),
    }


def _map_payload(flash: FlashImage, symbol: str) -> dict:
    m = CATALOG.read_map(flash, symbol)
    payload = m.summary()
    payload["x"] = [round(float(v), 3) for v in m.x]
    payload["y"] = [round(float(v), 3) for v in m.y]
    payload["z"] = [[round(float(v), 3) for v in row] for row in m.z]
    return payload


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/manifest.json")
def pwa_manifest():
    return FileResponse(
        STATIC / "manifest.json", media_type="application/manifest+json"
    )


@app.get("/sw.js")
def pwa_service_worker():
    # Served from root scope so the SW controls the whole cockpit.
    return FileResponse(STATIC / "sw.js", media_type="application/javascript")


@app.get("/audio_fx.js")
def audio_fx():
    return FileResponse(STATIC / "audio_fx.js", media_type="application/javascript")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(STATIC / "icon-192.png", media_type="image/png")


@app.get("/icon-192.png")
def icon_192():
    return FileResponse(STATIC / "icon-192.png", media_type="image/png")


@app.get("/icon-512.png")
def icon_512():
    return FileResponse(STATIC / "icon-512.png", media_type="image/png")


@app.get("/apple-touch-icon.png")
def apple_touch_icon():
    return FileResponse(STATIC / "apple-touch-icon.png", media_type="image/png")


@app.get("/api/meta")
def meta():
    flash = STATE["stock"] or load_flash(STOCK_BIN)
    return {
        "stock": _ecu_meta(flash, STOCK_BIN.name),
        "maps": MAP_CHOICES,
        "telemetry": telemetry_cockpit.summary(),
        "muse_available": MusePlanner().available,
    }


@app.post("/api/load-stock")
def load_stock():
    STATE["stock"] = load_flash(STOCK_BIN)
    STATE["tuned"] = None
    return _ecu_meta(STATE["stock"], STOCK_BIN.name)


@app.post("/api/upload-bin")
async def upload_bin(file: UploadFile = File(...)):
    data = await file.read()
    try:
        flash = FlashImage(data, source=file.filename or "upload.bin")
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    STATE["stock"] = flash
    STATE["tuned"] = None
    return _ecu_meta(flash, file.filename or "upload.bin")


@app.get("/api/map/{symbol}")
def get_map(symbol: str, which: str = "stock"):
    flash = STATE["tuned"] if (which == "tuned" and STATE["tuned"]) else STATE["stock"]
    if flash is None:
        flash = STATE["stock"] = load_flash(STOCK_BIN)
    try:
        return _map_payload(flash, symbol)
    except KeyError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)


class _OfflinePlanner(MusePlanner):
    """Deterministic planner for reproducible on-camera intercepts."""

    available = False
    model = "offline-deterministic"

    def __init__(self):
        pass

    def plan(self, intent, map_context="", correction_note=""):
        from backend.ai_engine.muse_planner import offline_plan

        return offline_plan(intent, correction_note)


@app.get("/api/tune")
def tune(intent: str, demo: int = 0):
    """SSE Thought Stream: plan -> patch -> gate -> (self-correct) -> done.

    demo=1 forces the deterministic offline planner so the 450 Nm Safety Gate
    intercept is reproducible on camera (live Muse often self-moderates).
    """
    stock = STATE["stock"] or load_flash(STOCK_BIN)
    STATE["stock"] = stock
    planner = _OfflinePlanner() if demo else MusePlanner()

    def events():
        def send(kind: str, **kw):
            return f"data: {json.dumps({'kind': kind, **kw})}\n\n"

        yield send("thought", text=f"Intent received: {intent!r}")
        yield send(
            "thought",
            text=f"Planner source check: Meta Model API "
            f"{'available (muse-spark-1.3)' if planner.available else 'offline fallback'}",
        )
        yield send(
            "thought",
            text="Ingesting 774-symbol Bosch catalogue, "
            "reading EngPrt_trqLim_CUR + friction map @90C...",
        )
        try:
            result = run_calibration(stock, CATALOG, intent, planner=planner)
        except RuntimeError as exc:
            yield send("error", text=str(exc))
            return
        for it in result.iterations:
            yield send(
                "thought",
                text=f"Attempt {it['attempt']} [{it['plan_source']}]: "
                f"target effective {it['target_effective_nm']:.0f} Nm "
                f"-> patching EngPrt_trqLim_CUR...",
            )
            if it["gate_passed"]:
                yield send("gate_pass", attempt=it["attempt"], metrics=it["metrics"])
            else:
                for v in it["violations"]:
                    yield send(
                        "gate_reject",
                        attempt=it["attempt"],
                        violation=v,
                        metrics=it["metrics"],
                    )
                yield send(
                    "thought",
                    text="Feeding violation report back to the "
                    "planner — self-correction in progress...",
                )
        STATE["tuned"] = result.flash
        STATE["intent"] = intent
        tuned_path = OUT / "metaecu_cockpit_tuned.bin"
        result.flash.save(tuned_path)
        s = CATALOG.read_map(stock, "EngPrt_trqLim_CUR")
        t = CATALOG.read_map(result.flash, "EngPrt_trqLim_CUR")
        yield send(
            "done",
            metrics=result.gate.metrics,
            plan=result.plan.to_dict(),
            torque={
                "rpm": [float(v) for v in s.x],
                "stock_nm": [float(v) for v in s.z[0]],
                "tuned_nm": [float(v) for v in t.z[0]],
            },
            download="/api/download-bin",
            report="/api/download-report",
        )

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/download-bin")
def download_bin():
    if STATE["tuned"] is None:
        return JSONResponse({"error": "Run a tuning session first"}, status_code=409)
    path = OUT / "metaecu_cockpit_tuned.bin"
    STATE["tuned"].save(path)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename="metaecu_cockpit_tuned.bin",
        headers={"X-Checksum": f"0x{STATE['tuned'].compute_checksum():08X}"},
    )


@app.get("/api/download-report")
def download_report():
    if STATE["tuned"] is None:
        return JSONResponse({"error": "Run a tuning session first"}, status_code=409)
    tuned = STATE["tuned"]
    gate = safety_gate.verify_final(CATALOG, tuned)
    lines = [
        "# MetaECU Copilot — Cockpit Audit Report",
        "",
        f"**Intent:** {STATE['intent']}",
        f"**Peak effective torque:** {gate.metrics.get('peak_effective_nm')} Nm "
        f"@ {gate.metrics.get('peak_effective_rpm')} rpm (limit 377 Nm)",
        f"**Rail max:** {gate.metrics.get('Rail_pSetPointBase_MAP_max_bar')} bar (limit 1600)",
        f"**Smoke lambda min:** {gate.metrics.get('smoke_lambda_min')} (stock floor 0.771)",
        f"**Checksum:** {gate.metrics.get('checksum')} (target 0xD01FE500)",
        "",
        f"**Verdict: {'PASS — approved for flashing' if gate.passed else 'FAIL'}**",
    ]
    path = OUT / "audit_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return FileResponse(
        path, media_type="text/markdown", filename="metaecu_audit_report.md"
    )


@app.post("/api/vision")
async def vision(file: UploadFile = File(...)):
    data = await file.read()
    mime = file.content_type or "image/png"
    return analyze_dyno_image(data, mime)


@app.get("/api/telemetry")
def telemetry(label: str = "v10 (po tuningu)"):
    return telemetry_cockpit.load_series(label)


@app.post("/api/voice-text")
def voice_text(text: str = Form(...)):
    return voice_ingest.translate_intent(text)


@app.post("/api/voice-audio")
async def voice_audio(file: UploadFile = File(...)):
    data = await file.read()
    result = voice_ingest.transcribe_audio(data, file.filename or "note.webm")
    if not result.get("ok"):
        return JSONResponse(result, status_code=503)
    result["intent"] = voice_ingest.translate_intent(result["text"])
    return result


def main() -> None:
    import uvicorn

    print("MetaECU Cockpit -> http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()

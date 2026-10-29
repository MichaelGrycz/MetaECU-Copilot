#!/usr/bin/env python3
"""MetaECU Copilot — Modal cloud deployment (public HTTPS Live Product).

Packages the FastAPI cockpit (backend/web_app.py), the binary core engine,
the 774-symbol Bosch catalogue, the stock 2 MiB flash and the real road
telemetry into a slim Modal container and serves it over public HTTPS.

One-time setup (see DEPLOYMENT.md):
    pip install modal
    modal setup
    modal secret create meta-secret META_API_KEY=<key> META_API_BASE_URL=https://api.meta.ai/v1

Deploy:
    modal deploy modal_deploy.py
    -> https://<user>--metaecu-copilot-web.modal.run   (URL printed by Modal)

Local smoke test of the exact packaged app (no Modal account needed):
    modal serve modal_deploy.py      # ephemeral dev URL + hot reload
    python modal_deploy.py --smoke   # in-process TestClient checks, offline-safe
"""

from __future__ import annotations

import sys
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parent
ASSETS = REPO / "build_assets" / "metaecu_assets"

APP_NAME = "metaecu-copilot"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "numpy>=1.26",
        "matplotlib>=3.8",
        "openai>=1.30",
        "python-dotenv>=1.0",
        "fastapi>=0.110",
        "uvicorn>=0.29",
        "python-multipart>=0.0.9",
        "Pillow>=10.0",
    )
    # Application code (slim: backend only, no 14 GB vehicle archives)
    .add_local_dir(REPO / "backend", remote_path="/app/backend", copy=True)
    .add_local_file(REPO / "main.py", remote_path="/app/main.py", copy=True)
    # Staged runtime assets: stock .bin (2 MiB) + catalogue + 3 telemetry CSVs
    # (~12.7 MB). Run `python tools/stage_assets.py` first — deploy fails fast
    # below if the staged tree is missing.
    .add_local_dir(ASSETS, remote_path="/assets", copy=True)
    .env(
        {
            "METAECU_ASSET_ROOT": "/assets",
            "METAECU_OUTPUT_DIR": "/tmp/metaecu_web",
            "PYTHONPATH": "/app",
        }
    )
)

app = modal.App(APP_NAME)


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name(
            "meta-secret"
        )  # META_API_KEY (+ optional META_API_BASE_URL)
    ],
    # Cockpit sessions are short interactive bursts; 1 CPU / 1 GiB is plenty
    # for numpy map math. The deterministic offline planner + Safety Gate work
    # even if the secret is absent — only live Muse reasoning needs the key.
    cpu=1.0,
    memory=1024,
    timeout=120,
    max_containers=2,
    scaledown_window=60,
)
@modal.asgi_app()
def web():
    """Serve the MetaECU FastAPI cockpit over public HTTPS."""
    sys.path.insert(0, "/app")
    from backend.web_app import app as fastapi_app

    return fastapi_app


def _smoke() -> int:
    """In-process smoke test of the exact app Modal will serve (offline-safe)."""
    import os

    os.environ.setdefault("METAECU_ASSET_ROOT", str(ASSETS))
    sys.path.insert(0, str(REPO))
    from fastapi.testclient import TestClient

    from backend.web_app import app as fastapi_app

    client = TestClient(fastapi_app)
    checks = {
        "GET /": client.get("/").status_code,
        "GET /manifest.json": client.get("/manifest.json").status_code,
        "GET /sw.js": client.get("/sw.js").status_code,
        "GET /audio_fx.js": client.get("/audio_fx.js").status_code,
        "GET /icon-512.png": client.get("/icon-512.png").status_code,
        "GET /api/meta": client.get("/api/meta").status_code,
        "GET /api/map/EngM_trqFrc_MAP": client.get(
            "/api/map/EngM_trqFrc_MAP"
        ).status_code,
    }
    failed = {k: v for k, v in checks.items() if v != 200}
    for k, v in checks.items():
        print(f"  [{'PASS' if v == 200 else 'FAIL'}] {k} -> {v}")
    meta = client.get("/api/meta").json()
    print(f"  stock checksum: {meta['stock']['checksum']} (expect 0xD01FE500)")
    tele = client.get("/api/telemetry", params={"label": "v10 (po tuningu)"}).json()
    print(f"  telemetry v10 points: {tele.get('points')} (expect 900)")
    if failed or meta["stock"]["checksum"] != "0xD01FE500" or tele.get("points") != 900:
        print("SMOKE FAILED")
        return 1
    print(
        "SMOKE PASS — packaged app is deploy-ready. Run: modal deploy modal_deploy.py"
    )
    return 0


if __name__ == "__main__":
    if not ASSETS.is_dir():
        print(
            "Staged assets missing. Run first:  python tools/stage_assets.py",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if "--smoke" in sys.argv:
        raise SystemExit(_smoke())
    print(__doc__)

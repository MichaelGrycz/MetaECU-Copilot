#!/usr/bin/env python3
"""Stage the slim runtime asset tree required by the MetaECU cockpit.

The full Saab project directory is ~14 GB (WinOLS VM images etc.). The web
app only needs five files at runtime. This script copies exactly those,
preserving the repo-relative layout, so both Modal and PyInstaller can set
METAECU_ASSET_ROOT to the staged directory.

Usage:
    python tools/stage_assets.py [dest_dir]   # default: build_assets/metaecu_assets
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

ASSETS = [
    "01_SAAB_9-3_1.9TID_EDC16C39/02_PLIKI_SERYJNE_I_BAZOWE/SAAB 93 tid 2008 edc16c39 1037389375.Bin",
    "01_SAAB_9-3_1.9TID_EDC16C39/03_DEFINICJE_MAP_XDF/BOSCH_EDC16C39_1037389375_COMPLETE_CATALOG.json",
    "01_SAAB_9-3_1.9TID_EDC16C39/04_SKRYPTY_AUDYTOW_I_TESTOW/audyty_i_raporty/telemetria_drogowa_v10/2026-10-19_18-54-36_log_obd_v10.csv",
    "01_SAAB_9-3_1.9TID_EDC16C39/04_SKRYPTY_AUDYTOW_I_TESTOW/audyty_i_raporty/telemetria_drogowa_v9/2026-10-15_11-30-23_log_obd_v9.csv",
    "01_SAAB_9-3_1.9TID_EDC16C39/04_SKRYPTY_AUDYTOW_I_TESTOW/audyty_i_raporty/telemetria_drogowa_v8/2026-10-14_14-25-13_log_obd_v8.csv",
    "2026-10-24 12-31-54.csv",
    "2026-10-26 18-20-34.csv",
    "demo_assets/output/torque_comparison.png",
]


def stage(dest: Path) -> list[dict]:
    staged = []
    # Ensure sample dyno chart exists before staging
    sample_chart = REPO / "demo_assets" / "output" / "torque_comparison.png"
    if not sample_chart.exists():
        sample_chart.parent.mkdir(parents=True, exist_ok=True)
        from demo_assets.generate_demo_assets import main as gen_demo

        gen_demo()

    for rel in ASSETS:
        src = REPO / rel
        if not src.is_file():
            print(f"Warning: asset {rel} missing, skipping.")
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        digest = hashlib.sha256(out.read_bytes()).hexdigest()[:12]
        staged.append({"path": rel, "bytes": out.stat().st_size, "sha256_12": digest})
    return staged


def main() -> int:
    dest = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else REPO / "build_assets" / "metaecu_assets"
    )
    staged = stage(dest)
    total = sum(s["bytes"] for s in staged)
    print(f"Staged {len(staged)} assets -> {dest} ({total / 1e6:.2f} MB total)")
    for s in staged:
        print(f"  {s['bytes']:>9} B  sha256:{s['sha256_12']}  {s['path']}")
    (dest / "ASSETS_MANIFEST.txt").write_text(
        "\n".join(f"{s['sha256_12']}  {s['bytes']:>9}  {s['path']}" for s in staged)
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

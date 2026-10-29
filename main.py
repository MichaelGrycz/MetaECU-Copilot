#!/usr/bin/env python3
"""
MetaECU Copilot — Autonomous & Verifiable Calibration Engine.

One-command demo:
    python main.py
    python main.py --intent "Stage 1, dynamic low end, F40 clutch protection"
    python main.py --intent "Give me 450 Nm" --out output/aggressive.bin

Pipeline: stock .bin -> Muse planner -> binary patcher -> deterministic
Safety Gate (self-correction loop) -> checksum fix -> audit report + charts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.ai_engine import sam_vision
from backend.binary_core.flash_loader import load_flash
from backend.binary_core.map_reader import Catalog
from backend.safety_engine.orchestrator import run_calibration

SAAB = ROOT / "01_SAAB_9-3_1.9TID_EDC16C39"
DEFAULT_BIN = (
    SAAB / "02_PLIKI_SERYJNE_I_BAZOWE" / "SAAB 93 tid 2008 edc16c39 1037389375.Bin"
)
DEFAULT_CATALOG = (
    SAAB / "03_DEFINICJE_MAP_XDF" / "BOSCH_EDC16C39_1037389375_COMPLETE_CATALOG.json"
)


def write_report(
    out_dir: Path, intent: str, result, stock_path: Path, tuned_path: Path
) -> Path:
    g = result.gate
    lines = [
        "# MetaECU Copilot — Calibration Audit Report",
        "",
        f"**Tuner intent:** {intent}",
        f"**Stock binary:** `{stock_path.name}`",
        f"**Tuned binary:** `{tuned_path.name}`",
        f"**Planner source:** {result.plan.source} "
        f"(target effective {result.plan.target_effective_torque_nm:.0f} Nm)",
        "",
        "## Self-correction loop",
        "",
    ]
    for it in result.iterations:
        verdict = "PASS" if it["gate_passed"] else "REJECTED"
        lines.append(
            f"- Attempt {it['attempt']} [{it['plan_source']}]: "
            f"target {it['target_effective_nm']:.0f} Nm -> Safety Gate **{verdict}**"
        )
        for v in it["violations"]:
            lines.append(f"  - Violation: {v}")
    lines += ["", "## Final Safety Gate metrics", ""]
    for k, v in g.metrics.items():
        lines.append(f"- `{k}`: {v}")
    lines += [
        "",
        f"**Final verdict: {'PASS — binary approved for flashing' if g.passed else 'FAIL'}**",
        "",
        f"Checksum: `{g.metrics.get('checksum')}` (target `0xD01FE500`)",
        "",
        "## Changed calibration",
        "",
        f"- Symbol: `{result.patch_info.get('symbol')}`",
        f"- Changed cells: {result.patch_info.get('changed_cells')}",
        "",
        "_Deterministic gate rules: F40 effective torque <= 377 Nm @90C, "
        "DMF 1500 rpm cap, rail <= 1600 bar, smoke lambda never below the "
        "stock floor (0.771), no torque spikes in 1500-4750 rpm, checksum "
        "0xD01FE500 verified on the final image. No AI output bypasses this gate._",
    ]
    report = out_dir / "audit_report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="MetaECU Copilot demo")
    ap.add_argument("--bin", default=str(DEFAULT_BIN), help="Stock .bin path")
    ap.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Catalog JSON path")
    ap.add_argument(
        "--intent",
        default="Stage 1, dynamic low end, F40 clutch protection",
        help="Natural-language tuning goal",
    )
    ap.add_argument(
        "--out",
        default=str(ROOT / "output" / "metaecu_tuned.bin"),
        help="Output tuned .bin path",
    )
    args = ap.parse_args()

    print("=" * 72)
    print("MetaECU Copilot — Autonomous & Verifiable Calibration Engine")
    print("=" * 72)
    stock = load_flash(args.bin)
    catalog = Catalog(args.catalog)
    print(
        f"[1/5] Loaded {Path(args.bin).name}: {len(stock)} bytes, "
        f"checksum 0x{stock.compute_checksum():08X} (OK={stock.checksum_ok()})"
    )
    print(f"[2/5] Catalog: {len(catalog)} Bosch symbols ingested")
    print(f"[3/5] Intent: {args.intent!r} -> planning + patching + Safety Gate loop")

    result = run_calibration(stock, catalog, args.intent)
    for it in result.iterations:
        print(
            f"      attempt {it['attempt']} [{it['plan_source']}]: "
            f"target {it['target_effective_nm']:.0f} Nm -> "
            f"{'PASS' if it['gate_passed'] else 'REJECTED ' + '; '.join(it['violations'])}"
        )

    out_path = Path(args.out)
    result.flash.save(out_path)
    out_dir = out_path.parent
    chart1 = sam_vision.render_torque_comparison(
        stock, result.flash, catalog, out_dir / "torque_comparison.png"
    )
    chart2 = sam_vision.render_3d_surface(
        result.flash, catalog, "EngM_trqFrc_MAP", out_dir / "friction_surface_3d.png"
    )
    smooth = sam_vision.analyze_surface_smoothness(result.flash, catalog)
    (out_dir / "surface_analysis.json").write_text(
        json.dumps(smooth, indent=2), encoding="utf-8"
    )
    report = write_report(out_dir, args.intent, result, Path(args.bin), out_path)

    print(
        f"[4/5] Visual grounding: {chart1.name}, {chart2.name}, surface={smooth['verdict']}"
    )
    print(
        f"[5/5] Gate {'PASS' if result.gate.passed else 'FAIL'} | "
        f"peak effective {result.gate.metrics['peak_effective_nm']} Nm | "
        f"checksum {result.gate.metrics['checksum']} | wrote {out_path} + {report}"
    )
    return 0 if result.gate.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

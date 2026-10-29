"""End-to-end tests (pytest-compatible, offline-deterministic).

Run: python -m pytest backend/test_end_to_end.py -q   (or: python backend/test_end_to_end.py)
The planner is forced offline so these tests never depend on the network;
the live Muse path is covered by backend/test_meta_api.py + main.py runs.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.ai_engine.muse_planner import MusePlanner, offline_plan
from backend.binary_core.flash_loader import load_flash
from backend.binary_core.map_reader import Catalog
from backend.safety_engine import safety_gate
from backend.safety_engine.orchestrator import run_calibration

ROOT = Path(__file__).resolve().parents[1]
SAAB = ROOT / "01_SAAB_9-3_1.9TID_EDC16C39"
ORI = SAAB / "02_PLIKI_SERYJNE_I_BAZOWE" / "SAAB 93 tid 2008 edc16c39 1037389375.Bin"
CATALOG = (
    SAAB / "03_DEFINICJE_MAP_XDF" / "BOSCH_EDC16C39_1037389375_COMPLETE_CATALOG.json"
)


class OfflinePlanner(MusePlanner):
    def __init__(self):
        pass

    def plan(self, intent, map_context="", correction_note=""):
        return offline_plan(intent, correction_note)


def _assets():
    return load_flash(ORI), Catalog(CATALOG)


def test_stock_binary_passes_gate():
    flash, cat = _assets()
    report = safety_gate.evaluate(cat, flash)
    assert report.passed, report.violations
    assert report.metrics["peak_effective_nm"] <= 377.0
    assert report.metrics["Rail_pSetPointBase_MAP_max_bar"] == 1600.0


def test_aggressive_450nm_is_rejected_then_corrected():
    flash, cat = _assets()
    result = run_calibration(flash, cat, "Give me 450 Nm", planner=OfflinePlanner())
    assert len(result.iterations) >= 2
    assert result.iterations[0]["gate_passed"] is False
    assert any("F40_CLUTCH_TORQUE" in v for v in result.iterations[0]["violations"])
    assert result.gate.passed
    assert result.flash.checksum_ok()
    assert result.gate.metrics["peak_effective_nm"] <= 377.0


def test_safe_stage1_converges_and_differs_from_stock():
    flash, cat = _assets()
    result = run_calibration(flash, cat, "Stage 1 safe", planner=OfflinePlanner())
    assert result.gate.passed
    assert result.flash.diff_count(flash) > 0


if __name__ == "__main__":
    test_stock_binary_passes_gate()
    print("[PASS] stock passes gate")
    test_aggressive_450nm_is_rejected_then_corrected()
    print("[PASS] 450 Nm rejected -> corrected")
    test_safe_stage1_converges_and_differs_from_stock()
    print("[PASS] stage 1 converges")
    print("ALL END-TO-END TESTS PASS")

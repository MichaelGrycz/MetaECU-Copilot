"""Guards the on-screen metrics against the measured v10 road-log values."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

import web_app
from backend.binary_core.flash_loader import load_flash


def test_dyno_metrics_match_measured_road_logs():
    web_app.STATE["tuned"] = load_flash(web_app.STOCK_BIN)
    payload = TestClient(web_app.app).get("/api/dyno-simulation").json()
    tuned = payload["tuned_metrics"]
    assert tuned["peak_power_km"] == 202.5
    assert tuned["peak_torque_nm"] == 376.5
    assert tuned["peak_torque_indicated_nm"] == 414.0
    assert tuned["spool_to_14bar_s"] == 1.34


def test_retired_placeholder_is_gone():
    for path in (ROOT / "web_app.py", ROOT / "backend" / "static" / "index.html"):
        assert "185.4" not in path.read_text(encoding="utf-8"), path


def test_gate_approved_plan_measures_the_v10_value():
    from backend.binary_core.map_reader import Catalog
    from backend.safety_engine.orchestrator import run_calibration
    from web_app import _OfflinePlanner

    saab = ROOT / "01_SAAB_9-3_1.9TID_EDC16C39"
    stock = load_flash(saab / "02_PLIKI_SERYJNE_I_BAZOWE" / "SAAB 93 tid 2008 edc16c39 1037389375.Bin")
    catalog = Catalog(saab / "03_DEFINICJE_MAP_XDF" / "BOSCH_EDC16C39_1037389375_COMPLETE_CATALOG.json")
    result = run_calibration(stock, catalog, "Give me 450 Nm, maximum power", planner=_OfflinePlanner())
    assert result.gate.passed
    assert len(result.iterations) >= 2
    assert result.gate.metrics["peak_effective_nm"] == 376.5


if __name__ == "__main__":
    test_dyno_metrics_match_measured_road_logs()
    test_retired_placeholder_is_gone()
    test_gate_approved_plan_measures_the_v10_value()
    print("app metrics OK")

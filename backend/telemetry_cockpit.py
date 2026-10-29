"""
Road-telemetry module: parses the real OBD road logs (Car Scanner export,
Polish column names) from the v8/v9/v10 test drives and serves chart-ready
series to the cockpit: RPM vs time, boost, rail pressure and MAF, plus the
documented WOT spool comparison (v9 4.90 s -> v10 1.34 s to 1.40 bar, 4th gear).

"Po tuningu" (after) = the v10 log shipped in the repo. "Przed tuningiem"
(before) is the v9 log when present on disk; the UI falls back to the audited
report figures when a file is missing. Nothing is synthesised.
"""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path

# METAECU_ASSET_ROOT lets slim deployments (Modal / PyInstaller) point at a
# staged asset tree instead of the full repo checkout.
ROOT = Path(
    os.environ.get("METAECU_ASSET_ROOT", str(Path(__file__).resolve().parents[1]))
)
REPORTS = (
    ROOT
    / "01_SAAB_9-3_1.9TID_EDC16C39"
    / "04_SKRYPTY_AUDYTOW_I_TESTOW"
    / "audyty_i_raporty"
)
LOGS = {
    "v13 Sport Response (2026-10-26)": ROOT / "2026-10-26 18-20-34.csv",
    "v12 Master Refinement (2026-10-24)": ROOT / "2026-10-24 12-31-54.csv",
    "v10 Spool & Punch (po tuningu)": REPORTS
    / "telemetria_drogowa_v10"
    / "2026-10-19_18-54-36_log_obd_v10.csv",
    "v9 Baseline (przed tuningiem)": REPORTS
    / "telemetria_drogowa_v9"
    / "2026-10-15_11-30-23_log_obd_v9.csv",
    "v8 Highway & Popcorn": REPORTS
    / "telemetria_drogowa_v8"
    / "2026-10-14_14-25-13_log_obd_v8.csv",
}

# Audited figures from RAPORT_TELEMETRII_V10.md (4th-gear spool test).
SPOOL_AUDIT = [
    {"label": "v9 — 4. bieg, czas do 1,40 bar", "seconds": 4.90},
    {"label": "v10 — 4. bieg, czas do 1,40 bar", "seconds": 1.34},
    {"label": "v10 — 5. bieg, czas do 1,40 bar", "seconds": 1.58},
    {"label": "v10 — 5. bieg, czas do 1,10 bar", "seconds": 0.85},
]


def _to_float(value: str) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _parse_hms(text: str) -> float | None:
    try:
        h, m, s = text.strip().split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except (ValueError, AttributeError):
        return None


def _find_column(fieldnames: list[str], needle: str) -> str | None:
    needle = needle.lower()
    for name in fieldnames:
        if needle in name.lower():
            return name
    return None


def load_series(label: str, max_points: int = 900) -> dict:
    """Downsampled time series (rpm, boost bar, rail bar, MAF g/s) for Plotly."""
    path = LOGS.get(label)
    if path is None or not path.exists():
        return {"label": label, "available": False}
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    c_time = fields[0] if fields else "time"
    c_rpm = _find_column(fields, "Obroty silnika (rpm)")
    c_boost = _find_column(fields, "Obliczone doładowanie")
    c_rail = _find_column(fields, "listwie wtryskowej")
    c_maf = _find_column(fields, "MAF")
    c_speed = _find_column(fields, "Prędkość samochodu")

    rows = list(reader)
    series = {
        "t": [],
        "rpm": [],
        "boost_bar": [],
        "rail_bar": [],
        "maf_gs": [],
        "speed_kmh": [],
    }
    t0 = None
    for row in rows:
        t = _parse_hms(row.get(c_time, ""))
        if t is None:
            continue
        if t0 is None:
            t0 = t
        series["t"].append(round(t - t0, 1))
        series["rpm"].append(_to_float(row.get(c_rpm, "")))
        series["boost_bar"].append(_to_float(row.get(c_boost, "")))
        rail_kpa = _to_float(row.get(c_rail, ""))
        series["rail_bar"].append(round(rail_kpa / 100.0, 1) if rail_kpa else None)
        series["maf_gs"].append(_to_float(row.get(c_maf, "")))
        series["speed_kmh"].append(_to_float(row.get(c_speed, "")))
    n = len(series["t"])
    if n > max_points:
        step = n / max_points
        keep = [int(i * step) for i in range(max_points)]
        series = {k: [v[i] for i in keep] for k, v in series.items()}
        n = max_points

    def _max(key: str) -> float | None:
        vals = [v for v in series[key] if v is not None]
        return round(max(vals), 2) if vals else None

    return {
        "label": label,
        "available": True,
        "points": n,
        "file": path.name,
        "peaks": {
            "rpm": _max("rpm"),
            "boost_bar": _max("boost_bar"),
            "rail_bar": _max("rail_bar"),
            "maf_gs": _max("maf_gs"),
            "speed_kmh": _max("speed_kmh"),
        },
        "series": series,
    }


def summary() -> dict:
    return {
        "logs": [
            {"label": label, "available": path.exists(), "file": path.name}
            for label, path in LOGS.items()
        ],
        "spool_audit": SPOOL_AUDIT,
        "source_report": "RAPORT_TELEMETRII_V10.md: 33 próby WOT, 202,5 KM / 414 Nm, MIL 0,0 km",
    }

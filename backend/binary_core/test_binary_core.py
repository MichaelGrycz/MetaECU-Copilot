"""Standalone test for the Binary Core Engine. Run: python backend/binary_core/test_binary_core.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from backend.binary_core.flash_loader import (
    CHECKSUM_ADDR,
    EXPECTED_SIZE,
    TARGET_CHECKSUM,
    load_flash,
)
from backend.binary_core.map_reader import Catalog

ROOT = Path(__file__).resolve().parents[2]
SAAB = ROOT / "01_SAAB_9-3_1.9TID_EDC16C39"
ORI = SAAB / "02_PLIKI_SERYJNE_I_BAZOWE" / "SAAB 93 tid 2008 edc16c39 1037389375.Bin"
CATALOG = (
    SAAB / "03_DEFINICJE_MAP_XDF" / "BOSCH_EDC16C39_1037389375_COMPLETE_CATALOG.json"
)

FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"[{status}] {name} {detail}")


def main() -> int:
    print("=" * 72)
    print("MetaECU Copilot — Binary Core Engine test")
    print("=" * 72)

    flash = load_flash(ORI)
    check("flash size == 2097152", len(flash) == EXPECTED_SIZE)
    check(
        "ORI checksum == 0xD01FE500",
        flash.checksum_ok(),
        f"(got 0x{flash.compute_checksum():08X})",
    )

    cat = Catalog(CATALOG)
    check("catalog has 774 entries", len(cat) == 774, f"(got {len(cat)})")

    trq = cat.read_map(flash, "EngPrt_trqLim_CUR")
    check("EngPrt_trqLim_CUR shape (1,25)", trq.z.shape == (1, 25), str(trq.z.shape))
    check(
        "torque limiter max ~367 Nm",
        abs(trq.z_max() - 367.0) < 1.0,
        f"(max={trq.z_max():.1f})",
    )
    # 1500 rpm must be the DMF-safe 297 Nm in stock calibration
    i1500 = int(np.where(trq.x == 1500)[0][0])
    check(
        "stock torque @1500rpm == 297 Nm",
        abs(trq.z[0, i1500] - 297.0) < 0.11,
        f"(got {trq.z[0, i1500]:.1f})",
    )

    frc = cat.read_map(flash, "EngM_trqFrc_MAP")
    check("EngM_trqFrc_MAP shape (16,16)", frc.z.shape == (16, 16))
    check(
        "friction Y axis contains 90 degC",
        bool(np.any(np.isclose(frc.y, 90.0, atol=0.1))),
        f"(y={np.round(frc.y, 1).tolist()})",
    )
    check(
        "friction values negative (drag)",
        frc.z_max() <= 0.0,
        f"(max={frc.z_max():.1f})",
    )

    rail = cat.read_map(flash, "Rail_pSetPointBase_MAP")
    # catalog factor: raw * 100 (hPa). 1600 bar = 1 600 000 hPa
    check(
        "rail setpoint <= 1600 bar (1.6e6 hPa)",
        rail.z_max() <= 1_600_000.0 + 1,
        f"(max={rail.z_max():.0f} hPa = {rail.z_max() / 1000:.0f} bar)",
    )
    check("rail setpoint max == 1600 bar", abs(rail.z_max() / 1000 - 1600.0) < 1.0)

    soi = cat.read_map(flash, "InjCrv_phiMI1Bas1_MAP")
    check(
        "SOI map readable, deg CrS range sane",
        -5.0 < soi.z_min() and soi.z_max() < 40.0,
        f"({soi.z_min():.2f}..{soi.z_max():.2f})",
    )

    # Round-trip: clone, bump torque limiter +10 Nm, fix checksum, re-read.
    mod = flash.clone()
    trq2 = cat.read_map(mod, "EngPrt_trqLim_CUR")
    trq2.z[0, i1500] += 10.0
    cat.write_map(mod, trq2)
    corr = mod.fix_checksum()
    reread = cat.read_map(mod, "EngPrt_trqLim_CUR")
    check(
        "round-trip +10 Nm persisted",
        abs(reread.z[0, i1500] - 307.0) < 0.11,
        f"(got {reread.z[0, i1500]:.1f})",
    )
    check(
        "checksum valid after edit + fix",
        mod.checksum_ok(),
        f"(correction word 0x{corr:08X} @ 0x{CHECKSUM_ADDR:06X})",
    )
    check("checksum target constant", TARGET_CHECKSUM == 0xD01FE500)
    check(
        "original untouched",
        flash.checksum_ok()
        and abs(cat.read_map(flash, "EngPrt_trqLim_CUR").z[0, i1500] - 297.0) < 0.11,
    )
    diff = mod.diff_count(flash)
    check(
        "diff is small (only edited cells + csum word)",
        0 < diff <= 8,
        f"({diff} bytes)",
    )

    print("=" * 72)
    print("RESULT:", "ALL PASS" if FAIL == 0 else f"{FAIL} FAILURE(S)")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())

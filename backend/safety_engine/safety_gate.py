"""
Deterministic Safety Gate for EDC16C39 calibrations.

Physical rules (ported from the audited F40/DMF engineering scripts — no AI
is involved in pass/fail decisions here):

1. F40 clutch: effective torque = indicated (EngPrt_trqLim_CUR) - friction
   (EngM_trqFrc_MAP interpolated @ 90 degC). Peak effective must be <= 377 Nm.
2. DMF protection: indicated torque at 1500 rpm <= 340 Nm.
3. Rail: Rail_pSetPointBase_MAP and Rail_pSetPointMax_MAP <= 1600 bar.
   (Catalog Z unit is hPa with factor 100, so raw values are read through
   the catalog and converted hPa -> bar by /1000.)
4. Smoke: FlMng_rLmbdSmkLow_MAP minimum lambda >= 0.85.
5. Smoothness: no adjacent-cell jump > 60 Nm in the torque limiter (spikes).
6. Smoke floor is relative: stock calibration already dips to lambda 0.771 in
   one corner, so tuning must never go *below the stock minimum*.

Checksum is intentionally NOT a gate rule during iteration: every patched
candidate carries a transient checksum until the orchestrator rewrites the
correction word. It is verified separately on the final image.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from backend.binary_core.flash_loader import FlashImage
from backend.binary_core.map_reader import Catalog

MAX_EFFECTIVE_TORQUE_NM = 377.0
MAX_INDICATED_1500_NM = 340.0
MAX_RAIL_BAR = 1600.0
MIN_SMOKE_LAMBDA = (
    0.85  # absolute floor for plans; gate uses stock floor (see evaluate)
)
STOCK_SMOKE_FLOOR = (
    0.771  # measured minimum of FlMng_rLmbdSmkLow_MAP in stock SW 1037389375
)
MAX_TORQUE_STEP_NM = 60.0
FRICTION_TEMP_C = 90.0


@dataclass
class GateViolation:
    rule: str
    detail: str
    measured: float
    limit: float

    def correction_hint(self) -> str:
        return f"{self.rule}: measured {self.measured:.1f}, limit {self.limit:.1f}. {self.detail}"


@dataclass
class GateReport:
    passed: bool
    violations: list[GateViolation] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def correction_note(self) -> str:
        hints = "; ".join(v.correction_hint() for v in self.violations)
        return (
            f"Clamp effective torque to <= {MAX_EFFECTIVE_TORQUE_NM:.0f} Nm "
            f"(indicated = effective + friction @90C). Violations: {hints}"
        )


def _friction_at(
    catalog: Catalog, flash: FlashImage, rpm_axis: np.ndarray
) -> np.ndarray:
    frc = catalog.read_map(flash, "EngM_trqFrc_MAP")
    # Verified layout (cross-checked with audit_transmission_f40_dmf.py on the
    # stock binary): Z is stored rpm-major — row r = rpm breakpoint frc.x[r],
    # column c = temperature breakpoint frc.y[c]. The catalog rows/cols labels
    # are transposed for this map, so we take the temperature *column*.
    t_idx = int(np.argmin(np.abs(frc.y - FRICTION_TEMP_C)))
    friction_col = np.abs(frc.z[:, t_idx])  # one value per rpm breakpoint
    return np.interp(rpm_axis, frc.x, friction_col)


def evaluate(catalog: Catalog, flash: FlashImage) -> GateReport:
    violations: list[GateViolation] = []
    metrics: dict = {}

    trq = catalog.read_map(flash, "EngPrt_trqLim_CUR")
    axis, indicated = trq.x, trq.z[0]
    friction = _friction_at(catalog, flash, axis)
    effective = indicated - friction

    band = (axis >= 1000) & (axis <= 4750)
    peak_eff = float(np.max(effective[band]))
    peak_rpm = float(axis[band][int(np.argmax(effective[band]))])
    metrics["peak_effective_nm"] = round(peak_eff, 1)
    metrics["peak_effective_rpm"] = peak_rpm
    metrics["peak_indicated_nm"] = round(float(np.max(indicated[band])), 1)
    if peak_eff > MAX_EFFECTIVE_TORQUE_NM:
        violations.append(
            GateViolation(
                "F40_CLUTCH_TORQUE",
                f"Peak effective torque {peak_eff:.1f} Nm at "
                f"{peak_rpm:.0f} rpm exceeds the F40 clutch-safe limit.",
                peak_eff,
                MAX_EFFECTIVE_TORQUE_NM,
            )
        )

    if 1500 in axis:
        ind1500 = float(indicated[axis == 1500][0])
        metrics["indicated_1500_nm"] = round(ind1500, 1)
        if ind1500 > MAX_INDICATED_1500_NM:
            violations.append(
                GateViolation(
                    "DMF_1500RPM",
                    f"Indicated torque at 1500 rpm is {ind1500:.1f} Nm; "
                    "the dual-mass flywheel limit is lower.",
                    ind1500,
                    MAX_INDICATED_1500_NM,
                )
            )

    # Spike rule guards the tuned plateau (1500-4750 rpm). Below that the stock
    # curve has factory launch/idle steps (222 Nm @1250 -> 297 Nm @1500), and
    # above it the Bosch rev-cut (260 -> 60 -> 0 Nm). Neither is a tuning spike.
    spike_band = (axis >= 1500) & (axis <= 4750)
    idx = np.where(spike_band)[0]
    steps = np.abs(np.diff(indicated[idx])) if idx.size > 1 else np.array([])
    max_step = float(np.max(steps)) if steps.size else 0.0
    metrics["max_torque_step_nm"] = round(max_step, 1)
    if max_step > MAX_TORQUE_STEP_NM:
        violations.append(
            GateViolation(
                "TORQUE_SPIKE",
                f"Adjacent torque cells jump by {max_step:.1f} Nm "
                "(spike / drivability hazard).",
                max_step,
                MAX_TORQUE_STEP_NM,
            )
        )

    for symbol in ("Rail_pSetPointBase_MAP", "Rail_pSetPointMax_MAP"):
        rail = catalog.read_map(flash, symbol)
        rail_bar = float(np.max(rail.z)) / 1000.0  # hPa -> bar
        metrics[f"{symbol}_max_bar"] = round(rail_bar, 1)
        if rail_bar > MAX_RAIL_BAR + 0.5:
            violations.append(
                GateViolation(
                    "RAIL_PRESSURE",
                    f"{symbol} peaks at {rail_bar:.1f} bar.",
                    rail_bar,
                    MAX_RAIL_BAR,
                )
            )

    smoke = catalog.read_map(flash, "FlMng_rLmbdSmkLow_MAP")
    lambda_min = float(np.min(smoke.z))
    metrics["smoke_lambda_min"] = round(lambda_min, 3)
    if lambda_min < STOCK_SMOKE_FLOOR - 0.002:
        violations.append(
            GateViolation(
                "SMOKE_LAMBDA",
                f"Smoke limiter lambda minimum {lambda_min:.3f} is below "
                f"the stock floor {STOCK_SMOKE_FLOOR}.",
                lambda_min,
                STOCK_SMOKE_FLOOR,
            )
        )

    # Reported for the audit trail; enforced on the final image by verify_final().
    metrics["checksum_ok"] = bool(flash.checksum_ok())
    metrics["checksum"] = f"0x{flash.compute_checksum():08X}"
    return GateReport(passed=not violations, violations=violations, metrics=metrics)


def verify_final(catalog: Catalog, flash: FlashImage) -> GateReport:
    """Gate + checksum enforcement, applied only after fix_checksum()."""
    report = evaluate(catalog, flash)
    if not flash.checksum_ok():
        report.passed = False
        report.violations.append(
            GateViolation(
                "CHECKSUM",
                f"Region checksum is 0x{flash.compute_checksum():08X}, "
                "expected 0xD01FE500.",
                float(flash.compute_checksum()),
                float(0xD01FE500),
            )
        )
    return report

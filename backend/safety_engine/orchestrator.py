"""
Self-correction orchestrator: planner -> patcher -> Safety Gate loop.

The gate is deterministic and always has the final word. When it rejects a
patched image, its precise violation report is fed back to the planner, which
must produce a corrected plan inside the approved physical envelope. The loop
runs at most ``max_iterations`` times and raises if it cannot converge.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.ai_engine import muse_patcher
from backend.ai_engine.muse_planner import CalibrationPlan, MusePlanner
from backend.binary_core.flash_loader import FlashImage
from backend.binary_core.map_reader import Catalog
from backend.safety_engine import safety_gate


@dataclass
class RunResult:
    flash: FlashImage
    plan: CalibrationPlan
    gate: safety_gate.GateReport
    iterations: list[dict] = field(default_factory=list)
    patch_info: dict = field(default_factory=dict)


def run_calibration(
    stock: FlashImage,
    catalog: Catalog,
    intent: str,
    planner: MusePlanner | None = None,
    max_iterations: int = 4,
) -> RunResult:
    planner = planner or MusePlanner()
    trq = catalog.read_map(stock, "EngPrt_trqLim_CUR")
    rail = catalog.read_map(stock, "Rail_pSetPointBase_MAP")
    context = (
        f"EngPrt_trqLim_CUR: stock peak indicated {trq.z_max():.0f} Nm over "
        f"{int(trq.x[0])}-{int(trq.x[-1])} rpm. "
        f"Rail_pSetPointBase_MAP: stock peak {rail.z_max() / 1000:.0f} bar. "
        f"Catalogue holds {len(catalog)} Bosch symbols."
    )

    note = ""
    iterations: list[dict] = []
    for attempt in range(1, max_iterations + 1):
        plan = planner.plan(intent, map_context=context, correction_note=note)
        candidate = stock.clone()
        patch_info = muse_patcher.apply_plan(candidate, catalog, plan)
        gate = safety_gate.evaluate(catalog, candidate)
        iterations.append(
            {
                "attempt": attempt,
                "plan_source": plan.source,
                "target_effective_nm": plan.target_effective_torque_nm,
                "gate_passed": gate.passed,
                "metrics": gate.metrics,
                "violations": [v.correction_hint() for v in gate.violations],
            }
        )
        if gate.passed:
            candidate.fix_checksum()
            final_gate = safety_gate.verify_final(catalog, candidate)
            if not final_gate.passed:  # checksum fix must never break the gate
                raise RuntimeError(
                    f"Gate failed after checksum fix: {final_gate.violations}"
                )
            return RunResult(
                flash=candidate,
                plan=plan,
                gate=final_gate,
                iterations=iterations,
                patch_info=patch_info,
            )
        note = gate.correction_note()

    raise RuntimeError(
        f"Self-correction did not converge in {max_iterations} attempts. "
        f"Last violations: {iterations[-1]['violations']}"
    )

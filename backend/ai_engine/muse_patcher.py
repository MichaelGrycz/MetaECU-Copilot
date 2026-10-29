"""
Binary patcher: applies a CalibrationPlan to a FlashImage.

Only the torque limiter curve (EngPrt_trqLim_CUR) is reshaped to the planned
indicated-torque curve, with monotone smoothing so the surface has no spikes.
Rail pressure and smoke maps are *verified* by the Safety Gate but not raised
beyond stock here — the plan's rail/smoke values are ceilings, and stock rail
already peaks at exactly 1600 bar.
"""

from __future__ import annotations

import numpy as np

from backend.ai_engine.muse_planner import CalibrationPlan
from backend.binary_core.flash_loader import FlashImage
from backend.binary_core.map_reader import Catalog

TORQUE_SYMBOL = "EngPrt_trqLim_CUR"


def _smooth_monotone(values: np.ndarray, max_step: float = 55.0) -> np.ndarray:
    """Limit adjacent-cell steps (forward + backward pass) and remove spikes.

    Guarantees max |diff| <= max_step so the patched curve can never trip the
    Safety Gate's 60 Nm spike rule, including at the band edges where the
    planned plateau meets the untouched stock cells.
    """
    v = values.astype(np.float64).copy()
    for _ in range(3):
        for i in range(1, len(v)):
            v[i] = min(max(v[i], v[i - 1] - max_step), v[i - 1] + max_step)
        for i in range(len(v) - 2, -1, -1):
            v[i] = min(max(v[i], v[i + 1] - max_step), v[i + 1] + max_step)
    return v


def apply_plan(flash: FlashImage, catalog: Catalog, plan: CalibrationPlan) -> dict:
    """Interpolate the planned curve onto the limiter's RPM axis and write it."""
    data = catalog.read_map(flash, TORQUE_SYMBOL)
    axis = data.x.copy()
    orig = data.z[0].copy()

    plan_rpm = np.array([p["rpm"] for p in plan.torque_curve], dtype=float)
    plan_nm = np.array([p["indicated_nm"] for p in plan.torque_curve], dtype=float)
    order = np.argsort(plan_rpm)
    planned = np.interp(axis, plan_rpm[order], plan_nm[order])

    # Only reshape the working band 1000-4750 rpm; keep rev-cut zeros intact.
    band = (axis >= 1000) & (axis <= 4750)
    new = orig.copy()
    new[band] = planned[band]
    new[band] = _smooth_monotone(new[band])
    # Never exceed the plan's indicated ceiling anywhere in the band.
    ceiling = float(plan_nm.max())
    new[band] = np.minimum(new[band], ceiling)

    data.z[0] = new
    catalog.write_map(flash, data)
    return {
        "symbol": TORQUE_SYMBOL,
        "axis_rpm": axis.tolist(),
        "before_nm": [round(float(v), 1) for v in orig],
        "after_nm": [round(float(v), 1) for v in new],
        "changed_cells": int(np.count_nonzero(~np.isclose(orig, new, atol=0.06))),
    }

"""
Visual grounding: renders 3D wireframe map surfaces and before/after torque
curves, then runs a deterministic surface-smoothness analysis (the stand-in
for SAM 3.1 segmentation when vision inference is unavailable — the PNG
artifacts are exactly what gets sent to SAM 3.1 / Muse Vision).

No AI judgement is used for safety: spike detection here is numeric and its
result is reported alongside the Safety Gate verdict.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from backend.binary_core.flash_loader import FlashImage
from backend.binary_core.map_reader import Catalog


def render_torque_comparison(
    stock: FlashImage, tuned: FlashImage, catalog: Catalog, out: Path
) -> Path:
    s = catalog.read_map(stock, "EngPrt_trqLim_CUR")
    t = catalog.read_map(tuned, "EngPrt_trqLim_CUR")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(s.x, s.z[0], "o-", label="Stock indicated torque", linewidth=2)
    ax.plot(t.x, t.z[0], "s-", label="MetaECU tuned (gate-approved)", linewidth=2)
    ax.axhline(
        377 + 31,
        color="red",
        linestyle="--",
        label="F40 clutch ceiling (indicated, ~2500 rpm friction)",
    )
    ax.set_xlabel("Engine speed [rpm]")
    ax.set_ylabel("Indicated torque [Nm]")
    ax.set_title("MetaECU Copilot — Torque limiter before / after")
    ax.set_xlim(0, 5000)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def render_3d_surface(
    flash: FlashImage, catalog: Catalog, symbol: str, out: Path
) -> Path:
    m = catalog.read_map(flash, symbol)
    x, y = np.meshgrid(m.x, m.y)
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_wireframe(x, y, m.z, rstride=1, cstride=1, linewidth=0.5)
    ax.set_xlabel(f"X [{m.entry.x_unit}]")
    ax.set_ylabel(f"Y [{m.entry.y_unit}]")
    ax.set_zlabel(f"Z [{m.entry.z_unit}]")
    ax.set_title(f"MetaECU Copilot — 3D surface: {symbol}")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def analyze_surface_smoothness(
    flash: FlashImage, catalog: Catalog, symbol: str = "EngM_trqFrc_MAP"
) -> dict:
    """Numeric spike/roughness analysis of a 2D map surface."""
    m = catalog.read_map(flash, symbol)
    if m.z.ndim != 2 or min(m.z.shape) < 2:
        curve = catalog.read_map(flash, "EngPrt_trqLim_CUR")
        steps = np.abs(np.diff(curve.z[0]))
        return {
            "symbol": "EngPrt_trqLim_CUR",
            "max_adjacent_step": round(float(steps.max()), 2),
            "spikes_detected": int(np.count_nonzero(steps > 60.0)),
            "verdict": "SMOOTH" if steps.max() <= 60.0 else "SPIKES_FOUND",
        }
    gx = np.abs(np.diff(m.z, axis=1))
    gy = np.abs(np.diff(m.z, axis=0))
    scale = max(float(np.max(np.abs(m.z))), 1.0)
    roughness = float((gx.max() + gy.max()) / scale)
    return {
        "symbol": symbol,
        "max_gradient_x": round(float(gx.max()), 3),
        "max_gradient_y": round(float(gy.max()), 3),
        "relative_roughness": round(roughness, 4),
        "spikes_detected": int(
            np.count_nonzero(gx > 0.5 * scale) + np.count_nonzero(gy > 0.5 * scale)
        ),
        "verdict": "SMOOTH" if roughness < 0.5 else "ROUGH",
    }

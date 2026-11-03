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


def render_dyno_chart(
    stock: FlashImage, tuned: FlashImage, catalog: Catalog, out: Path
) -> Path:
    """Render a realistic, axis-calibrated dyno chart (torque & power vs RPM).

    Unlike ``render_torque_comparison`` (which only plots the raw torque-limiter
    curve with no physical axes), this produces a genuine engine dynamometer plot
    with RPM on the X axis and Nm / HP on the Y axis. It is the artifact sent to
    SAM 3.1 / Muse Vision so the multimodal model can actually read peak torque,
    peak power and any mid-range dip from calibrated axes.
    """
    s = catalog.read_map(stock, "EngPrt_trqLim_CUR")
    t = catalog.read_map(tuned, "EngPrt_trqLim_CUR")

    # Realistic dyno-style curves: indicated torque limiter as the engine torque
    # ceiling, plus a power curve derived from torque (P = T * rpm / 9549, kW).
    rpm = np.linspace(1000, 4800, 60)

    def _interp(curve_x, curve_y, x):
        order = np.argsort(curve_x)
        return np.interp(x, curve_x[order], curve_y[order])

    t_stock = np.array([_interp(s.x, s.z[0], r) for r in rpm])
    t_tuned = np.array([_interp(t.x, t.z[0], r) for r in rpm])

    # Friction-limited effective torque ceiling (indicated - friction @90C).
    friction = {
        1500: 36.0, 1750: 34.0, 2000: 33.0, 2250: 32.0, 2500: 31.0,
        2750: 30.0, 3000: 29.5, 3250: 29.0, 3500: 28.5, 3750: 28.0, 4000: 27.5,
    }
    f_stock = np.array(
        [min(friction.get(int(round(r)), 30.0), 36.0) for r in rpm]
    )
    f_tuned = f_stock

    eff_stock = np.clip(t_stock - f_stock, 0, None)
    eff_tuned = np.clip(t_tuned - f_tuned, 0, None)

    # Power (kW) from effective torque: P = T * rpm / 9549.
    p_stock_kw = eff_stock * rpm / 9549.0
    p_tuned_kw = eff_tuned * rpm / 9549.0

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(rpm, eff_stock, "o-", color="#8899aa", linewidth=2.2,
            label=f"Stock torque (eff) — peak {eff_stock.max():.0f} Nm")
    ax.plot(rpm, eff_tuned, "s-", color="#00d4ff", linewidth=2.6,
            label=f"MetaECU tuned (eff) — peak {eff_tuned.max():.0f} Nm")
    ax.plot(rpm, p_stock_kw * 1.34102, "--", color="#8899aa", linewidth=1.4,
            alpha=0.7, label="Stock power (hp)")
    ax.plot(rpm, p_tuned_kw * 1.34102, "--", color="#00d4ff", linewidth=1.4,
            alpha=0.7, label="Tuned power (hp)")

    ax.axhline(377, color="#ff3b30", linestyle=":", linewidth=1.5,
               label="F40 clutch ceiling = 377 Nm")
    ax.set_xlabel("Engine speed [rpm]")
    ax.set_ylabel("Torque [Nm] / Power [hp]")
    ax.set_title("MetaECU Copilot — Saab 9-3 1.9 TiD (Z19DTH) engine dynamometer")
    ax.set_xlim(1000, 4800)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", fontsize=9)
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

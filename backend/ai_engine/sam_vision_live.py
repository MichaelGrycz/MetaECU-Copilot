"""
Live multimodal vision analysis (SAM 3.1 / Muse Vision via Meta Model API).

The tuner uploads a dyno chart image (PNG/JPG). The image is sent to the Meta
Model API vision endpoint and the model performs visual grounding: it locates
the torque/power curves, finds inflection points and any torque dip, and
returns a structured correction recommendation.

Deterministic offline fallback: when the Meta API is unavailable (no key,
network error, empty reasoning response) the module runs a numeric analysis
of the image itself (dark-curve extraction + dip detection) so the cockpit
still produces a physically grounded answer. The source is always reported.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

VISION_SYSTEM = (
    "You are the SAM 3.1 / Muse Vision grounding module of MetaECU Copilot, an "
    "expert Bosch EDC16C39 calibration engineer. You analyse dyno chart images "
    "(torque/power vs RPM) from a Saab 9-3 1.9 TiD (Z19DTH, Bosch EDC16C39, "
    "GM F40 gearbox). You visually segment the curves and report only what is "
    "visible on the chart."
)

VISION_PROMPT = """Analyse this dyno chart image. Perform visual grounding:
1. Identify the torque curve and the power curve and their axes.
2. Estimate peak torque [Nm] and at which RPM, peak power [hp/kW] and at which RPM.
3. Find any inflection points and any torque dip (local valley) — give the RPM range.
4. Recommend one concrete calibration correction (e.g. raise the torque limiter
   plateau, smooth SOI, adjust boost setpoint) that respects: effective torque
   <= 377 Nm on the F40 clutch, rail <= 1600 bar.
Return ONLY a JSON object (no markdown fences):
{
  "peak_torque_nm": <number or null>,
  "peak_torque_rpm": <number or null>,
  "peak_power_hp": <number or null>,
  "peak_power_rpm": <number or null>,
  "inflection_points_rpm": [<numbers>],
  "torque_dip": {"detected": <bool>, "rpm_range": [<start>, <end>] or null,
                 "depth_nm": <number or null>},
  "recommendation": "<one concrete correction>",
  "confidence": "<low|medium|high>"
}"""


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    return t[start : end + 1] if start >= 0 and end > start else t


def analyze_dyno_numeric(image_bytes: bytes) -> dict:
    """Deterministic curve extraction: dark pixels per column -> dip detection."""
    import numpy as np
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    w, h = img.size
    arr = np.asarray(img, dtype=np.float64)
    dark = arr < 110
    curve_y = np.full(w, np.nan)
    for col in range(w):
        rows = np.where(dark[:, col])[0]
        if rows.size:
            curve_y[col] = rows.mean()
    valid = ~np.isnan(curve_y)
    dip = {"detected": False, "rpm_range": None, "depth_nm": None}
    if valid.sum() > 50:
        ys = curve_y[valid]
        smooth = np.convolve(ys, np.ones(15) / 15, mode="same")
        mid = smooth[len(smooth) // 4 : 3 * len(smooth) // 4]
        if mid.size > 20:
            base = np.nanmedian(mid)
            depth = float(np.nanmax(mid) - base)  # lower on chart = higher value
            if depth > 0.08 * h:
                idx = int(np.nanargmax(mid))
                dip = {
                    "detected": True,
                    "rpm_range": ["~40% of chart width", "~60% of chart width"],
                    "depth_nm": None,
                    "_note": "pixel-domain dip; RPM/Nm need axis calibration",
                }
    return {
        "peak_torque_nm": None,
        "peak_torque_rpm": None,
        "peak_power_hp": None,
        "peak_power_rpm": None,
        "inflection_points_rpm": [],
        "torque_dip": dip,
        "recommendation": (
            "Numeric fallback: re-run with Meta Vision for axis-calibrated values. "
            "If a mid-range dip is confirmed, raise EngPrt_trqLim_CUR plateau "
            "smoothness in 2000-2500 rpm and verify smoke lambda stays >= stock floor."
        ),
        "confidence": "low",
        "source": "numeric_fallback",
        "image_size": [w, h],
    }


def analyze_dyno_image(image_bytes: bytes, mime: str = "image/png") -> dict:
    """Live Meta Vision analysis with deterministic numeric fallback."""
    api_key = os.getenv("META_API_KEY", "")
    base_url = os.getenv("META_API_BASE_URL", "https://api.meta.ai/v1")
    model = os.getenv("META_VISION_MODEL", os.getenv("META_MODEL", "muse-spark-1.3"))
    if api_key and not api_key.startswith("LLM_..."):
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url)
            b64 = base64.b64encode(image_bytes).decode()
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": VISION_SYSTEM},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{b64}"},
                            },
                        ],
                    },
                ],
                # Vision on a reasoning model needs a generous budget.
                max_tokens=4000,
            )
            msg = resp.choices[0].message
            content = (
                msg.get("content")
                if isinstance(msg, dict)
                else getattr(msg, "content", "")
            )
            if not content:
                raise ValueError("empty vision response (reasoning budget)")
            data = json.loads(_strip_fences(content))
            data["source"] = "meta_vision"
            data["model"] = model
            return data
        except Exception as exc:
            result = analyze_dyno_numeric(image_bytes)
            result["vision_error"] = f"{type(exc).__name__}: {exc}"[:200]
            return result
    result = analyze_dyno_numeric(image_bytes)
    result["vision_error"] = "META_API_KEY not configured"
    return result

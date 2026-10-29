"""
Muse Spark & Wonder & Open-Weight calibration planner.

Translates a tuner's natural-language intent into a structured, machine-checkable
calibration plan (JSON). Supports:
- Meta Model API (muse-spark-1.3, muse-wonder-1.0)
- Baseten Open-Weight API (meta-models/muse-spark-open-1026)
- Deterministic offline planner for test reproducibility and on-camera demos.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

PLAN_SCHEMA_HINT = """
Return ONLY a JSON object (no markdown fences) with this schema:
{
  "intent": "<echo of the tuner goal, short>",
  "target_effective_torque_nm": <number, effective Nm at the clutch>,
  "torque_curve": [{"rpm": <int>, "indicated_nm": <number>}, ...],
  "rail_pressure_max_bar": <number>,
  "smoke_lambda_min": <number>,
  "rationale": "<short engineering justification>"
}
Constraints you MUST respect in your plan:
- Effective torque = indicated torque - friction torque (EngM_trqFrc_MAP @90C).
- NEVER plan effective torque above 377 Nm (F40 clutch protection) — but the
  Safety Gate will reject anything above it, and this demo intentionally tests
  that an over-ambitious request gets corrected.
- Rail pressure must never exceed 1600 bar (Bosch CP1H).
- Smoke lambda lower limit must stay >= 0.85.
- Torque at 1500 rpm must stay low (DMF protection): indicated <= 340 Nm.
"""

SYSTEM_PROMPT = (
    "You are MetaECU Copilot, an expert Bosch EDC16C39 calibration engineer. "
    "You plan precise, physically safe diesel calibrations for a Saab 9-3 1.9 TiD "
    "(Z19DTH) with a GM F40 manual gearbox. You reason in indicated vs effective "
    "torque and never guess addresses — the deterministic Safety Gate verifies "
    "every plan against the real binary before anything is written."
)

FRICTION_90C = {
    1500: 36.0,
    1750: 34.0,
    2000: 33.0,
    2250: 32.0,
    2500: 31.0,
    2750: 30.0,
    3000: 29.5,
    3250: 29.0,
    3500: 28.5,
    3750: 28.0,
    4000: 27.5,
}


@dataclass
class CalibrationPlan:
    intent: str
    target_effective_torque_nm: float
    torque_curve: list[dict]  # [{rpm, indicated_nm}]
    rail_pressure_max_bar: float = 1600.0
    smoke_lambda_min: float = 0.90
    rationale: str = ""
    source: str = "offline"  # "muse" | "baseten" | "offline"
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "target_effective_torque_nm": self.target_effective_torque_nm,
            "torque_curve": self.torque_curve,
            "rail_pressure_max_bar": self.rail_pressure_max_bar,
            "smoke_lambda_min": self.smoke_lambda_min,
            "rationale": self.rationale,
            "source": self.source,
        }


def _parse_torque_request(text: str) -> float | None:
    m = re.search(r"(\d{3})\s*nm", text.lower())
    return float(m.group(1)) if m else None


def offline_plan(intent: str, correction_note: str = "") -> CalibrationPlan:
    """Deterministic planner used offline and as the self-correction fallback."""
    asked = _parse_torque_request(intent)
    if correction_note:
        m = re.search(r"clamp.*?(\d+(?:\.\d+)?)\s*nm", correction_note.lower())
        target_eff = float(m.group(1)) if m else 377.0
    elif asked:
        target_eff = asked
    elif "stage 1" in intent.lower():
        target_eff = 390.0
    else:
        target_eff = 360.0

    rpms = [1500, 1750, 2000, 2250, 2500, 2750, 3000, 3250, 3500, 3750, 4000]
    curve = []
    for rpm in rpms:
        if rpm == 1500:
            eff = min(target_eff * 0.82, 300.0)
        elif rpm in (2000, 2250, 2500):
            eff = target_eff
        elif rpm >= 3500:
            eff = target_eff * 0.88
        else:
            eff = target_eff * 0.97
        curve.append({"rpm": rpm, "indicated_nm": round(eff + FRICTION_90C[rpm], 1)})

    return CalibrationPlan(
        intent=intent,
        target_effective_torque_nm=float(target_eff),
        torque_curve=curve,
        rail_pressure_max_bar=1600.0,
        smoke_lambda_min=0.90,
        rationale=(
            "Offline deterministic plan. "
            + (
                f"Self-correction applied: {correction_note}"
                if correction_note
                else "Plateau shaped around 2000-2500 rpm, tapered top end, soft 1500 rpm for DMF."
            )
        ),
        source="offline",
    )


class MusePlanner:
    def __init__(self, model: str | None = None, provider: str | None = None):
        self.model = model or os.getenv("META_MODEL", "muse-spark-1.3")
        self.provider = provider or (
            "baseten" if "meta-models/" in self.model else "meta"
        )

        if self.provider == "baseten":
            self.api_key = os.getenv("BASETEN_API_KEY", os.getenv("META_API_KEY", ""))
            self.base_url = os.getenv(
                "BASETEN_API_BASE_URL", "https://inference.baseten.co/v1"
            )
        else:
            self.api_key = os.getenv("META_API_KEY", "")
            self.base_url = os.getenv("META_API_BASE_URL", "https://api.meta.ai/v1")

        self.available = bool(self.api_key) and not self.api_key.startswith("LLM_...")

    def plan(
        self, intent: str, map_context: str = "", correction_note: str = ""
    ) -> CalibrationPlan:
        if self.available:
            try:
                return self._plan_via_api(intent, map_context, correction_note)
            except Exception as exc:
                plan = offline_plan(intent, correction_note)
                plan.rationale += (
                    f" [{self.provider.upper()} API fallback: {type(exc).__name__}]"
                )
                return plan
        return offline_plan(intent, correction_note)

    def _plan_via_api(
        self, intent: str, map_context: str, correction_note: str
    ) -> CalibrationPlan:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        user = f"Tuner goal: {intent}\n"
        if map_context:
            user += f"\nRelevant map metadata from the real binary:\n{map_context}\n"
        if correction_note:
            user += (
                f"\nSAFETY GATE CORRECTION (mandatory): {correction_note}\n"
                "Produce a corrected plan inside the approved limits."
            )
        user += PLAN_SCHEMA_HINT

        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            max_tokens=4000,
        )
        msg = resp.choices[0].message
        content = (
            msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        )
        data = json.loads(_strip_fences(content))
        curve = [
            {"rpm": int(p["rpm"]), "indicated_nm": float(p["indicated_nm"])}
            for p in data["torque_curve"]
        ]
        return CalibrationPlan(
            intent=str(data.get("intent", intent)),
            target_effective_torque_nm=float(data["target_effective_torque_nm"]),
            torque_curve=curve,
            rail_pressure_max_bar=float(data.get("rail_pressure_max_bar", 1600.0)),
            smoke_lambda_min=float(data.get("smoke_lambda_min", 0.90)),
            rationale=str(data.get("rationale", "")),
            source=self.provider,
            raw=data,
        )


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    return t[start : end + 1] if start >= 0 and end > start else t

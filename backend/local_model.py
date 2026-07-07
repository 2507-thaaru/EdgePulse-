"""
Local reasoning layer — the "draft" step.

Runs on the edge (in the real product: automotive SoC/NPU; in this demo:
your laptop, via Ollama). Takes one telemetry snapshot plus a short
rolling history, and produces a structured Diagnosis by reasoning over
relationships between signals rather than checking each one against a
fixed threshold.

This call must never block on the network — it talks only to a local
Ollama instance (http://localhost:11434 by default) and must return a
usable diagnosis even if Ollama is briefly slow, which is why a
rule-based fallback exists below. The fallback is deliberately simple:
it exists so the live demo never goes silent, not as a substitute for
the model's reasoning.
"""

from __future__ import annotations

import json
import os
import httpx
from backend.models import TelemetrySnapshot, Diagnosis, Severity

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "tinyllama")

SYSTEM_PROMPT = """You are an embedded vehicle-health reasoning system. You receive a live \
sensor snapshot and recent history from a vehicle. Your job is to reason about \
RELATIONSHIPS between signals (not just single values against fixed limits) and \
decide whether the vehicle is in a normal, advisory, warning, or critical state.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{
  "severity": "normal" | "advisory" | "warning" | "critical",
  "summary": "<one plain-language sentence>",
  "reasoning": "<one sentence: which signals, in combination, led to this>",
  "recommendation": "<one concrete, actionable sentence for the driver or fleet operator>",
  "contributing_signals": ["<signal_name>", "..."]
}

Guidance:
- "normal": values are within healthy range for the driving mode.
- "advisory": a slow trend worth tracking (e.g. gradual wear), not urgent.
- "warning": a combination of signals suggests elevated risk soon.
- "critical": multiple signals together indicate likely imminent failure.
Do not flag "critical" from a single mildly elevated value alone — reason about combinations.
"""


def _build_user_prompt(current: TelemetrySnapshot, history: list[TelemetrySnapshot]) -> str:
    history_lines = [
        f"t-{len(history) - i}: engine={h.engine_temp_c}C oil={h.oil_pressure_kpa}kPa "
        f"batt={h.battery_voltage_v}V brakeWear={h.brake_wear_pct}% altLoad={h.alternator_load_pct}%"
        for i, h in enumerate(history)
    ]
    return (
        f"Recent history (oldest to newest):\n" + "\n".join(history_lines) + "\n\n"
        f"Current snapshot:\n"
        f"engine_temp_c={current.engine_temp_c}, oil_pressure_kpa={current.oil_pressure_kpa}, "
        f"battery_voltage_v={current.battery_voltage_v}, brake_wear_pct={current.brake_wear_pct}, "
        f"alternator_load_pct={current.alternator_load_pct}, coolant_level_pct={current.coolant_level_pct}, "
        f"driving_mode={current.driving_mode}, rpm={current.rpm}, speed_kmh={current.speed_kmh}\n\n"
        f"Return the JSON diagnosis now."
    )


async def get_local_diagnosis(
    current: TelemetrySnapshot,
    history: list[TelemetrySnapshot],
    timeout_seconds: float = 6.0,
) -> Diagnosis:
    prompt = _build_user_prompt(current, history)
    payload = {
        "model": LOCAL_MODEL_NAME,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            resp.raise_for_status()
            raw = resp.json().get("response", "").strip()
            parsed = json.loads(raw)
            return Diagnosis(
                severity=Severity(parsed["severity"]),
                summary=parsed["summary"],
                reasoning=parsed["reasoning"],
                recommendation=parsed["recommendation"],
                contributing_signals=parsed.get("contributing_signals", []),
                source="local",
            )
    except Exception as exc:  # noqa: BLE001 — demo must degrade, never crash
        return _fallback_rule_based_diagnosis(current, error=str(exc))


def _fallback_rule_based_diagnosis(current: TelemetrySnapshot, error: str) -> Diagnosis:
    """
    Minimal safety net if Ollama is unreachable or returns malformed output.
    This is NOT the product's reasoning — it's a demo-reliability fallback
    so a dropped local-model call never produces dead air on screen.
    """
    signals = []
    severity = Severity.NORMAL

    if current.oil_pressure_kpa < 260 and current.engine_temp_c > 100:
        severity = Severity.CRITICAL
        signals = ["oil_pressure_kpa", "engine_temp_c"]
    elif current.brake_wear_pct > 80:
        severity = Severity.WARNING
        signals = ["brake_wear_pct"]
    elif current.brake_wear_pct > 50 or current.battery_voltage_v < 12.0:
        severity = Severity.ADVISORY
        signals = ["brake_wear_pct", "battery_voltage_v"]

    return Diagnosis(
        severity=severity,
        summary=f"[fallback reasoning — local model unavailable: {error[:60]}]",
        reasoning="Rule-based fallback triggered because the local model call failed.",
        recommendation="Retry local model connection; treat this reading as provisional.",
        contributing_signals=signals,
        source="local-fallback",
    )

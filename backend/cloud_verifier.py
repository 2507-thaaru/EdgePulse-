"""
Cloud verification layer — the "verify" step.

Sits outside the critical path: the vehicle never waits on this to act.
When connectivity is available, this asynchronously re-runs the same
telemetry context through a larger model (via Groq's API) and compares
its judgment to the local model's. Disagreements are logged for later
model evaluation and offline improvement — this file does NOT retrain
anything live; it only records disagreement events (see disagreement_log.jsonl).
"""

from __future__ import annotations

import json
import os
import time
import httpx
from backend.models import TelemetrySnapshot, Diagnosis, Severity, VerificationResult

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.1-70b-versatile")

DISAGREEMENT_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "disagreement_log.jsonl")

SYSTEM_PROMPT = """You are a high-capacity vehicle-health verification model. You will be shown \
a telemetry snapshot and a diagnosis produced by a smaller, faster local model. Independently \
assess the telemetry yourself, then judge whether you agree with the local model's severity \
and reasoning.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{
  "agreement": true | false,
  "cloud_severity": "normal" | "advisory" | "warning" | "critical",
  "cloud_summary": "<your own one-sentence assessment>",
  "notes": "<one sentence explaining why you agree or disagree>"
}
"""


def _build_user_prompt(telemetry: TelemetrySnapshot, local_diagnosis: Diagnosis) -> str:
    return (
        f"Telemetry: engine_temp_c={telemetry.engine_temp_c}, oil_pressure_kpa={telemetry.oil_pressure_kpa}, "
        f"battery_voltage_v={telemetry.battery_voltage_v}, brake_wear_pct={telemetry.brake_wear_pct}, "
        f"alternator_load_pct={telemetry.alternator_load_pct}, coolant_level_pct={telemetry.coolant_level_pct}, "
        f"driving_mode={telemetry.driving_mode}\n\n"
        f"Local model diagnosis: severity={local_diagnosis.severity.value}, "
        f"summary=\"{local_diagnosis.summary}\", reasoning=\"{local_diagnosis.reasoning}\"\n\n"
        f"Return the JSON verification now."
    )


async def verify_diagnosis(
    telemetry: TelemetrySnapshot,
    local_diagnosis: Diagnosis,
    timeout_seconds: float = 8.0,
) -> VerificationResult:
    """
    Returns verified=False (not an exception) if the cloud call can't be
    made — e.g. no connectivity, no API key, or a network failure. This
    mirrors production behavior: verification is best-effort and never
    blocks the vehicle's local decision.
    """
    if not telemetry.connectivity:
        return VerificationResult(
            original_diagnosis=local_diagnosis,
            cloud_diagnosis=None,
            agreement=True,      # no information to disagree with — not a claim of correctness
            notes="Offline — cloud verification skipped, local diagnosis stands.",
            verified=False,
        )

    if not GROQ_API_KEY:
        return VerificationResult(
            original_diagnosis=local_diagnosis,
            cloud_diagnosis=None,
            agreement=True,
            notes="No GROQ_API_KEY configured — cloud verification skipped.",
            verified=False,
        )

    payload = {
        "model": GROQ_MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(telemetry, local_diagnosis)},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)

        cloud_diagnosis = Diagnosis(
            severity=Severity(parsed["cloud_severity"]),
            summary=parsed["cloud_summary"],
            reasoning="Cloud independent assessment.",
            recommendation=local_diagnosis.recommendation,
            contributing_signals=local_diagnosis.contributing_signals,
            source="cloud",
        )
        agreement = bool(parsed["agreement"])

        result = VerificationResult(
            original_diagnosis=local_diagnosis,
            cloud_diagnosis=cloud_diagnosis,
            agreement=agreement,
            notes=parsed.get("notes", ""),
            verified=True,
        )

        if not agreement:
            _log_disagreement(telemetry, result)

        return result

    except Exception as exc:  # noqa: BLE001 — verification failures must not crash the loop
        return VerificationResult(
            original_diagnosis=local_diagnosis,
            cloud_diagnosis=None,
            agreement=True,
            notes=f"Cloud verification call failed: {str(exc)[:80]}",
            verified=False,
        )


def _log_disagreement(telemetry: TelemetrySnapshot, result: VerificationResult) -> None:
    """
    Appends one JSON line per disagreement. In production this feed is
    what an offline retraining pipeline would consume to improve the
    local model over time. Nothing here modifies the local model live.
    """
    record = {
        "timestamp": time.time(),
        "telemetry": telemetry.model_dump(),
        "local_severity": result.original_diagnosis.severity.value,
        "cloud_severity": result.cloud_diagnosis.severity.value if result.cloud_diagnosis else None,
        "notes": result.notes,
    }
    try:
        with open(DISAGREEMENT_LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # logging failure should never break the demo

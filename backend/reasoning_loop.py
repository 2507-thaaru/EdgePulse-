"""
The orchestration loop.

This is the piece that actually implements the "draft locally, verify
when possible" pattern:

  1. Every tick, pull one telemetry snapshot.
  2. The local model reasons over it immediately (never waits on network).
  3. Every VERIFICATION_INTERVAL_CYCLES ticks — OR immediately if the
     local model just raised severity to "warning"/"critical" — the
     cloud model is asked to independently verify, asynchronously.
  4. Results (telemetry + diagnosis + optional verification) are pushed
     to any connected dashboard clients and kept in a short rolling
     history buffer for the next local reasoning call.

Verification is throttled deliberately: continuously verifying every
cycle would reintroduce the network dependency this architecture exists
to avoid. Verifying only periodically — plus immediately on severity
escalation — mirrors how the local model should carry the routine load
while the cloud model spot-checks and calibrates it.
"""

from __future__ import annotations

import asyncio
import os
from collections import deque
from backend.models import TelemetrySnapshot, Diagnosis, ReasoningCycleResult, Severity
from backend.telemetry_generator import TelemetryGenerator
from backend.local_model import get_local_diagnosis
from backend.cloud_verifier import verify_diagnosis

VERIFICATION_INTERVAL_CYCLES = int(os.getenv("VERIFICATION_INTERVAL_CYCLES", "5"))
TELEMETRY_TICK_SECONDS = float(os.getenv("TELEMETRY_TICK_SECONDS", "2"))
HISTORY_LENGTH = 6

_ESCALATED = {Severity.WARNING, Severity.CRITICAL}


class ReasoningLoop:
    def __init__(self) -> None:
        self.generator = TelemetryGenerator()
        self.history: deque[TelemetrySnapshot] = deque(maxlen=HISTORY_LENGTH)
        self.recent_results: deque[ReasoningCycleResult] = deque(maxlen=HISTORY_LENGTH)
        self._cycle_count = 0
        self._last_severity: Severity = Severity.NORMAL
        self._subscribers: list[asyncio.Queue] = []
        self._task: asyncio.Task | None = None

    # --- subscription plumbing for the dashboard's websocket ---
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def _publish(self, result: ReasoningCycleResult) -> None:
        for q in list(self._subscribers):
            await q.put(result)

    # --- control from API endpoints ---
    def set_scenario(self, scenario: str) -> None:
        self.generator.set_scenario(scenario)
        self.history.clear()
        self.recent_results.clear()
        self._cycle_count = 0

    def set_connectivity(self, online: bool) -> None:
        self.generator.set_connectivity(online)
        
    def set_recorded_demo(self, enabled: bool) -> None:
        self.generator.set_recorded_demo(enabled)
        
    def get_state(self) -> dict:
        return {
            "scenario": self.generator.scenario,
            "connectivity": self.generator.connectivity,
            "recorded_demo": self.generator.recorded_demo,
            "recent_results": [r.model_dump(mode="json") for r in self.recent_results],
        }

    # --- the loop itself ---
    async def run_forever(self) -> None:
        while True:
            await self.run_one_cycle()
            await asyncio.sleep(TELEMETRY_TICK_SECONDS)

    async def run_one_cycle(self) -> ReasoningCycleResult:
        self._cycle_count += 1
        telemetry = self.generator.tick()
        
        # Terminal Logging
        print(f"\n\033[96m[Telemetry Ticks]\033[0m Cycle {self._cycle_count} | Mode: {telemetry.scenario.upper()} | Link: {'ONLINE' if telemetry.connectivity else 'OFFLINE'}")

        # Step 1: local model reasons immediately — no network dependency.
        print("\033[93m[Edge Inference]\033[0m Querying local AI model...")
        diagnosis = await get_local_diagnosis(telemetry, list(self.history))
        self.history.append(telemetry)

        sev_color = "\033[92m" if diagnosis.severity.value == "normal" else ("\033[93m" if diagnosis.severity.value == "advisory" else "\033[91m")
        print(f"\033[93m[Edge Inference]\033[0m Local Diagnosis complete: {sev_color}{diagnosis.severity.value.upper()}\033[0m")

        # Step 2: decide whether this cycle also gets cloud verification.
        should_verify = (
            self._cycle_count % VERIFICATION_INTERVAL_CYCLES == 0
            or (diagnosis.severity in _ESCALATED and self._last_severity not in _ESCALATED)
        )
        self._last_severity = diagnosis.severity

        verification = None
        if should_verify:
            if telemetry.connectivity:
                print("\033[94m[Cloud Verifier]\033[0m Initiating asynchronous cloud verification (Llama 70B)...")
            else:
                print("\033[91m[Cloud Verifier]\033[0m Offline - Verification skipped.")
            verification = await verify_diagnosis(telemetry, diagnosis)
            if verification and verification.verified:
                res_color = "\033[92mAGREEMENT" if verification.agreement else "\033[91mDISAGREEMENT (LOGGED)"
                print(f"\033[94m[Cloud Verifier]\033[0m Result: {res_color}\033[0m")

        result = ReasoningCycleResult(telemetry=telemetry, diagnosis=diagnosis, verification=verification)
        self.recent_results.append(result)
        await self._publish(result)
        return result


# Single shared instance used by the FastAPI app.
loop = ReasoningLoop()

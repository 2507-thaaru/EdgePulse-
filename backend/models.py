"""
Shared data schemas for EdgePulse.

Every object that moves between the telemetry generator, the local
reasoning model, the cloud verifier, and the dashboard is defined here,
so all three layers agree on shape.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import time


class Severity(str, Enum):
    NORMAL = "normal"
    ADVISORY = "advisory"        # everyday / predictive-health tier
    WARNING = "warning"          # elevated risk, not yet critical
    CRITICAL = "critical"        # rare-event / critical-detection tier


class TelemetrySnapshot(BaseModel):
    """One tick of simulated vehicle sensor data."""
    timestamp: float = Field(default_factory=time.time)
    engine_temp_c: float
    oil_pressure_kpa: float
    battery_voltage_v: float
    brake_wear_pct: float          # 0 = new, 100 = fully worn
    alternator_load_pct: float
    coolant_level_pct: float
    rpm: int
    speed_kmh: float
    driving_mode: str              # "city" | "highway" | "idle"
    connectivity: bool             # simulates signal availability
    scenario: str                  # which injected scenario is active


class Diagnosis(BaseModel):
    """Output of the local reasoning model for one telemetry snapshot."""
    timestamp: float = Field(default_factory=time.time)
    severity: Severity
    summary: str                   # one-line plain-language diagnosis
    reasoning: str                 # which signals/relationships drove this
    recommendation: str            # what the driver/fleet operator should do
    contributing_signals: list[str] = Field(default_factory=list)
    source: str = "local"          # "local" or "cloud"


class VerificationResult(BaseModel):
    """Result of the cloud model checking a local diagnosis."""
    timestamp: float = Field(default_factory=time.time)
    original_diagnosis: Diagnosis
    cloud_diagnosis: Optional[Diagnosis] = None
    agreement: bool
    notes: str                     # explanation of agreement/disagreement
    verified: bool                 # False if cloud call failed / offline


class ReasoningCycleResult(BaseModel):
    """What the orchestrator emits to the dashboard after each cycle."""
    telemetry: TelemetrySnapshot
    diagnosis: Diagnosis
    verification: Optional[VerificationResult] = None

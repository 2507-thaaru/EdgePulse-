"""
Synthetic telemetry generator.

Produces OBD/sensor-style vehicle data on a tick. Exists so the demo can
show real reasoning behavior without needing an actual vehicle or a
physical OBD-II adapter. Four scenarios are built in and can be switched
live during a demo:

  - "normal"            : healthy vehicle, small realistic noise only
  - "gradual_wear"       : slow, everyday drift (brake wear, battery aging)
                            -> exercises the Predictive Health tier
  - "multi_symptom"      : several individually-minor anomalies compound
                            at once -> exercises Critical Pattern Detection
  - "low_connectivity"   : same as multi_symptom, but with `connectivity`
                            forced False, to demonstrate the local model
                            continuing to reason and act with no cloud link

Call `set_scenario()` and `set_connectivity()` from an API endpoint to
switch these live while the dashboard is open.
"""

from __future__ import annotations

import random
import time
from backend.models import TelemetrySnapshot

VALID_SCENARIOS = {"normal", "gradual_wear", "multi_symptom", "low_connectivity"}


class TelemetryGenerator:
    def __init__(self) -> None:
        self.scenario = "normal"
        self.connectivity = True
        self.recorded_demo = False
        self._tick_count = 0
        self._rng = random.Random()
        self._seed_base = 42

        # Baseline "healthy" values — everything drifts from here.
        self._engine_temp = 90.0          # celsius, healthy ~85-95
        self._oil_pressure = 320.0        # kPa, healthy ~280-350
        self._battery_voltage = 12.6      # volts, healthy ~12.4-14.4
        self._brake_wear = 15.0           # percent worn
        self._alternator_load = 45.0      # percent
        self._coolant_level = 95.0        # percent

    def set_scenario(self, scenario: str) -> None:
        if scenario not in VALID_SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario}'. Valid: {VALID_SCENARIOS}")
        self.scenario = scenario
        self._tick_count = 0
        if self.recorded_demo:
            self._rng.seed(self._seed_base)
            
        if scenario == "low_connectivity":
            self.connectivity = False
        else:
            self.connectivity = True

    def set_connectivity(self, online: bool) -> None:
        self.connectivity = online
        
    def set_recorded_demo(self, enabled: bool) -> None:
        self.recorded_demo = enabled
        if enabled:
            self._rng.seed(self._seed_base)

    def tick(self) -> TelemetrySnapshot:
        self._tick_count += 1
        noise = lambda scale: self._rng.uniform(-scale, scale)

        if self.scenario == "normal":
            engine_temp = self._engine_temp + noise(1.5)
            oil_pressure = self._oil_pressure + noise(5)
            battery_voltage = self._battery_voltage + noise(0.1)
            brake_wear = self._brake_wear
            alternator_load = self._alternator_load + noise(5)
            coolant_level = self._coolant_level

        elif self.scenario in ("gradual_wear",):
            # Slow, monotonic drift — the everyday predictive-maintenance case.
            drift = min(self._tick_count * 0.15, 40)
            engine_temp = self._engine_temp + noise(1.5)
            oil_pressure = self._oil_pressure - (drift * 0.4) + noise(5)
            battery_voltage = self._battery_voltage - (drift * 0.01) + noise(0.1)
            brake_wear = min(self._brake_wear + drift, 95)
            alternator_load = self._alternator_load + noise(5)
            coolant_level = self._coolant_level - (drift * 0.05)

        elif self.scenario in ("multi_symptom", "low_connectivity"):
            # Several individually-minor anomalies compounding at once —
            # none alone would cross a classic threshold, but together
            # they form a recognizable pre-failure pattern.
            ramp = min(self._tick_count * 0.8, 25)
            engine_temp = self._engine_temp + (ramp * 0.6) + noise(1.5)
            oil_pressure = self._oil_pressure - (ramp * 1.2) + noise(5)
            battery_voltage = self._battery_voltage - (ramp * 0.02) + noise(0.1)
            brake_wear = self._brake_wear + (ramp * 0.1)
            alternator_load = self._alternator_load + (ramp * 1.5) + noise(5)
            coolant_level = self._coolant_level - (ramp * 0.3)

        else:
            engine_temp, oil_pressure, battery_voltage = self._engine_temp, self._oil_pressure, self._battery_voltage
            brake_wear, alternator_load, coolant_level = self._brake_wear, self._alternator_load, self._coolant_level

        driving_mode = self._rng.choice(["city", "highway", "idle"])
        rpm = {"city": 1800, "highway": 2600, "idle": 800}[driving_mode] + int(noise(100))
        speed = {"city": 40, "highway": 100, "idle": 0}[driving_mode] + noise(5)

        return TelemetrySnapshot(
            timestamp=time.time(),
            engine_temp_c=round(engine_temp, 1),
            oil_pressure_kpa=round(oil_pressure, 1),
            battery_voltage_v=round(battery_voltage, 2),
            brake_wear_pct=round(brake_wear, 1),
            alternator_load_pct=round(alternator_load, 1),
            coolant_level_pct=round(coolant_level, 1),
            rpm=max(rpm, 0),
            speed_kmh=round(max(speed, 0), 1),
            driving_mode=driving_mode,
            connectivity=self.connectivity,
            scenario=self.scenario,
        )

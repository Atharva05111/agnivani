"""Simulated plant: four fire zones plus a pump room.

Stands in for a live feed from an IoT gateway. Real detections (e.g. an edge
flame-detection camera) can be pushed in through /api/events/detection.
"""
from __future__ import annotations

import random
import time
from dataclasses import asdict, dataclass, field

WARN_TEMP, FIRE_TEMP = 45.0, 57.0
WARN_SMOKE, FIRE_SMOKE = 1.5, 4.0
NOMINAL_PRESSURE = 7.2


@dataclass
class Zone:
    id: str
    label: str          # English label for the dashboard
    exit_no: int
    base_temp: float
    temp: float = 0.0
    smoke: float = 0.0
    status: str = "normal"  # normal | warning | fire
    burning: bool = False

    def __post_init__(self):
        self.temp = self.base_temp
        self.smoke = 0.2


@dataclass
class PumpRoom:
    pressure: float = NOMINAL_PRESSURE
    main_pump: bool = False
    jockey_pump: bool = False
    tank: float = 94.0


@dataclass
class Alarm:
    id: int
    zone: str
    source: str           # sensor | camera | manual
    started_at: float
    acknowledged: bool = False
    confidence: float | None = None


@dataclass
class Plant:
    zones: dict[str, Zone] = field(default_factory=lambda: {
        "A": Zone("A", "Production floor", 1, 31.0),
        "B": Zone("B", "Warehouse", 2, 29.0),
        "C": Zone("C", "Server room", 3, 23.0),
        "D": Zone("D", "Canteen", 1, 30.0),
    })
    pumps: PumpRoom = field(default_factory=PumpRoom)
    alarm: Alarm | None = None
    _alarm_seq: int = 0
    _pump_start_at: float | None = None
    events: list[dict] = field(default_factory=list)

    # ------------------------------------------------------------- control
    def ignite(self, zone_id: str) -> None:
        self.zones[zone_id].burning = True
        self._log(f"Drill: incident started in {self.zones[zone_id].label}")

    def raise_alarm(self, zone_id: str, source: str, confidence: float | None = None) -> Alarm:
        if self.alarm is None:
            self._alarm_seq += 1
            self.alarm = Alarm(self._alarm_seq, zone_id, source, time.time(), confidence=confidence)
            self._pump_start_at = time.time() + 3.0
            z = self.zones[zone_id]
            z.status = "fire"
            self._log(f"Fire alarm: {z.label} ({source})")
        return self.alarm

    def acknowledge(self) -> bool:
        if self.alarm and not self.alarm.acknowledged:
            self.alarm.acknowledged = True
            self._log("Alarm silenced by operator")
            return True
        return False

    def reset(self) -> None:
        for z in self.zones.values():
            z.burning = False
            z.temp, z.smoke, z.status = z.base_temp, 0.2, "normal"
        self.pumps = PumpRoom(tank=self.pumps.tank)
        self.alarm = None
        self._pump_start_at = None
        self._log("System reset")

    # ---------------------------------------------------------------- tick
    def tick(self) -> Alarm | None:
        """Advance the simulation one step. Returns a new Alarm if one was raised."""
        new_alarm = None
        for z in self.zones.values():
            if z.burning:
                z.temp = min(92.0, z.temp + random.uniform(2.5, 4.5))
                z.smoke = min(14.0, z.smoke + random.uniform(0.5, 1.1))
            else:
                z.temp += (z.base_temp - z.temp) * 0.1 + random.uniform(-0.25, 0.25)
                z.smoke = max(0.0, z.smoke + (0.2 - z.smoke) * 0.2 + random.uniform(-0.05, 0.05))
            if z.status != "fire":
                if z.temp >= FIRE_TEMP and z.smoke >= FIRE_SMOKE:
                    had = self.alarm
                    alarm = self.raise_alarm(z.id, "sensor")
                    z.status = "fire"
                    if had is None:
                        new_alarm = alarm
                elif z.temp >= WARN_TEMP or z.smoke >= WARN_SMOKE:
                    if z.status != "warning":
                        self._log(f"Warning: {z.label} rising ({z.temp:.0f} °C)")
                    z.status = "warning"
                else:
                    z.status = "normal"

        p = self.pumps
        if self._pump_start_at and time.time() >= self._pump_start_at and not p.main_pump:
            p.main_pump = True
            self._log("Main fire pump started automatically")
        if p.main_pump:
            p.pressure += (6.4 - p.pressure) * 0.3 + random.uniform(-0.05, 0.05)
            p.tank = max(5.0, p.tank - 0.12)
        else:
            p.pressure += (NOMINAL_PRESSURE - p.pressure) * 0.3 + random.uniform(-0.04, 0.04)
            p.jockey_pump = p.pressure < NOMINAL_PRESSURE - 0.15
        return new_alarm

    # --------------------------------------------------------------- views
    def _log(self, msg: str) -> None:
        self.events.insert(0, {"t": time.time(), "msg": msg})
        del self.events[30:]

    def snapshot(self) -> dict:
        return {
            "zones": [
                {k: v for k, v in asdict(z).items() if k != "burning"} | {"temp": round(z.temp, 1), "smoke": round(z.smoke, 1)}
                for z in self.zones.values()
            ],
            "pumps": {**asdict(self.pumps), "pressure": round(self.pumps.pressure, 1), "tank": round(self.pumps.tank)},
            "alarm": asdict(self.alarm) if self.alarm else None,
            "events": self.events[:12],
        }

"""
Electric Vehicle (EV) charger model for the GridOS digital twin.

Models a Level 2 or DC fast charger with configurable power levels,
session management, and smart-charging (V1G) capability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChargerState(str, Enum):
    """EV charger operating state."""

    IDLE = "idle"
    CHARGING = "charging"
    COMPLETE = "complete"
    FAULT = "fault"


@dataclass
class EVCharger:
    """Electric vehicle charger.

    Parameters
    ----------
    charger_id:
        Unique charger identifier.
    bus_id:
        Bus to which the charger is connected.
    max_power_kw:
        Maximum charging power in kW.
    min_power_kw:
        Minimum modulated power in kW (for smart charging).
    efficiency:
        Charger efficiency (0–1).
    ev_battery_kwh:
        Connected EV battery capacity in kWh.
    ev_soc:
        Current EV state of charge (0–1).
    target_soc:
        Target SoC for the charging session.
    """

    charger_id: str
    bus_id: str
    max_power_kw: float = 22.0
    min_power_kw: float = 1.4
    efficiency: float = 0.95
    ev_battery_kwh: float = 60.0
    ev_soc: float = 0.3
    target_soc: float = 0.9

    # Runtime
    state: ChargerState = ChargerState.IDLE
    p_output_kw: float = 0.0
    setpoint_kw: float = 0.0

    @property
    def ev_soc_percent(self) -> float:
        return self.ev_soc * 100.0

    @property
    def energy_needed_kwh(self) -> float:
        """Remaining energy to reach target SoC."""
        return max((self.target_soc - self.ev_soc) * self.ev_battery_kwh, 0.0)

    def plug_in(
        self, ev_battery_kwh: float = 60.0, ev_soc: float = 0.3, target_soc: float = 0.9
    ) -> None:
        """Start a new charging session."""
        self.ev_battery_kwh = ev_battery_kwh
        self.ev_soc = ev_soc
        self.target_soc = target_soc
        self.state = ChargerState.CHARGING
        self.setpoint_kw = self.max_power_kw
        logger.info(
            "EV plugged in at %s: battery=%.0f kWh, SoC=%.0f%%, target=%.0f%%",
            self.charger_id,
            ev_battery_kwh,
            ev_soc * 100,
            target_soc * 100,
        )

    def unplug(self) -> None:
        """End the charging session."""
        self.state = ChargerState.IDLE
        self.p_output_kw = 0.0
        self.setpoint_kw = 0.0

    def set_power(self, p_kw: float) -> None:
        """Set smart-charging power setpoint (V1G)."""
        self.setpoint_kw = max(self.min_power_kw, min(p_kw, self.max_power_kw))

    def update(self, dt: float, grid_state: dict | None = None) -> None:
        """Advance the charger model by one time step.

        Parameters
        ----------
        dt:
            Time step in seconds.
        grid_state:
            Optional grid conditions.
        """
        if self.state != ChargerState.CHARGING:
            self.p_output_kw = 0.0
            return

        dt_h = dt / 3600.0
        p = min(self.setpoint_kw, self.max_power_kw)

        energy_delivered = p * dt_h * self.efficiency
        energy_needed = self.energy_needed_kwh

        if energy_delivered >= energy_needed:
            energy_delivered = energy_needed
            p = energy_delivered / (dt_h * self.efficiency) if dt_h > 0 else 0.0
            self.state = ChargerState.COMPLETE

        self.ev_soc += (
            energy_delivered / self.ev_battery_kwh if self.ev_battery_kwh > 0 else 0.0
        )
        self.ev_soc = min(self.ev_soc, self.target_soc)
        self.p_output_kw = p  # power drawn from grid (load perspective)

    def __repr__(self) -> str:
        return (
            f"EVCharger(id={self.charger_id!r}, bus={self.bus_id!r}, "
            f"state={self.state.value}, EV_SoC={self.ev_soc_percent:.1f}%, "
            f"P={self.p_output_kw:.1f} kW)"
        )

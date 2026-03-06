"""
Battery Energy Storage System (BESS) model for the GridOS digital twin.

Implements a first-order equivalent-circuit model with state-of-charge
tracking, round-trip efficiency, and power/energy constraints.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Battery:
    """Battery energy storage system.

    Parameters
    ----------
    battery_id:
        Unique battery identifier.
    bus_id:
        Bus to which the battery is connected.
    capacity_kwh:
        Usable energy capacity in kWh.
    max_charge_kw:
        Maximum charging power in kW.
    max_discharge_kw:
        Maximum discharging power in kW.
    efficiency:
        Round-trip efficiency (0–1).
    soc_min:
        Minimum allowed state of charge (0–1).
    soc_max:
        Maximum allowed state of charge (0–1).
    soc:
        Current state of charge (0–1).
    """

    battery_id: str
    bus_id: str
    capacity_kwh: float = 100.0
    max_charge_kw: float = 50.0
    max_discharge_kw: float = 50.0
    efficiency: float = 0.92
    soc_min: float = 0.1
    soc_max: float = 0.95
    soc: float = 0.5

    # Runtime state
    p_output_kw: float = 0.0  # positive = discharging, negative = charging
    setpoint_kw: float = 0.0

    @property
    def soc_percent(self) -> float:
        """State of charge as a percentage."""
        return self.soc * 100.0

    @property
    def energy_available_kwh(self) -> float:
        """Energy available for discharge above soc_min."""
        return (self.soc - self.soc_min) * self.capacity_kwh

    @property
    def energy_headroom_kwh(self) -> float:
        """Energy headroom for charging below soc_max."""
        return (self.soc_max - self.soc) * self.capacity_kwh

    def set_power(self, p_kw: float) -> None:
        """Set the desired power setpoint.

        Positive = discharge, negative = charge.
        """
        self.setpoint_kw = p_kw

    def update(self, dt: float, grid_state: dict | None = None) -> None:
        """Advance the battery model by one time step.

        Parameters
        ----------
        dt:
            Time step in seconds.
        grid_state:
            Optional grid conditions (unused in this model).
        """
        dt_h = dt / 3600.0  # convert to hours

        p = self.setpoint_kw

        # Clamp to power limits
        p = min(p, self.max_discharge_kw) if p > 0 else max(p, -self.max_charge_kw)

        # Energy change
        if p > 0:
            # Discharging
            energy_out = p * dt_h
            max_energy = self.energy_available_kwh
            if energy_out > max_energy:
                energy_out = max_energy
                p = energy_out / dt_h if dt_h > 0 else 0.0
            self.soc -= energy_out / self.capacity_kwh
        else:
            # Charging (p is negative)
            energy_in = abs(p) * dt_h * self.efficiency
            max_energy = self.energy_headroom_kwh
            if energy_in > max_energy:
                energy_in = max_energy
                p = -(energy_in / (dt_h * self.efficiency)) if dt_h > 0 else 0.0
            self.soc += energy_in / self.capacity_kwh

        # Clamp SoC
        self.soc = max(self.soc_min, min(self.soc, self.soc_max))
        self.p_output_kw = p

    def __repr__(self) -> str:
        return (
            f"Battery(id={self.battery_id!r}, bus={self.bus_id!r}, "
            f"SoC={self.soc_percent:.1f}%, P={self.p_output_kw:.1f} kW)"
        )

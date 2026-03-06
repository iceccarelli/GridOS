"""
Photovoltaic (PV) system model for the GridOS digital twin.

Implements a simplified single-diode-equivalent model that converts
irradiance and temperature into AC power output, accounting for
inverter efficiency and curtailment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PV:
    """Photovoltaic generation system.

    Parameters
    ----------
    pv_id:
        Unique PV system identifier.
    bus_id:
        Bus to which the PV system is connected.
    rated_kw:
        Nameplate DC rating in kW.
    efficiency:
        Overall system efficiency (0–1), including inverter losses.
    temp_coeff:
        Power temperature coefficient in %/°C (typically −0.4 for Si).
    tilt_deg:
        Panel tilt angle in degrees.
    azimuth_deg:
        Panel azimuth in degrees (180 = south-facing in northern hemisphere).
    """

    pv_id: str
    bus_id: str
    rated_kw: float = 10.0
    efficiency: float = 0.18
    temp_coeff: float = -0.004  # per °C relative to 25 °C
    tilt_deg: float = 30.0
    azimuth_deg: float = 180.0
    area_m2: float = 55.0  # approximate for 10 kWp

    # Runtime state
    irradiance_w_m2: float = 0.0
    temperature_c: float = 25.0
    p_output_kw: float = 0.0
    curtailment_kw: float = 0.0

    def update(self, dt: float, grid_state: dict | None = None) -> None:
        """Compute PV output for the current time step.

        Parameters
        ----------
        dt:
            Time step in seconds.
        grid_state:
            Must contain ``irradiance_w_m2`` and optionally
            ``temperature_c``.
        """
        if grid_state is not None:
            self.irradiance_w_m2 = grid_state.get(
                "irradiance_w_m2", self.irradiance_w_m2
            )
            self.temperature_c = grid_state.get("temperature_c", self.temperature_c)

        # DC power from irradiance
        p_dc = self.area_m2 * self.efficiency * self.irradiance_w_m2 / 1000.0  # kW

        # Temperature derating
        delta_t = self.temperature_c - 25.0
        temp_factor = 1.0 + self.temp_coeff * delta_t
        temp_factor = max(temp_factor, 0.0)

        p_dc *= temp_factor

        # Clip to rated capacity
        p_dc = min(p_dc, self.rated_kw)

        # Apply curtailment
        self.p_output_kw = max(p_dc - self.curtailment_kw, 0.0)

    def curtail(self, amount_kw: float) -> float:
        """Apply active power curtailment.

        Returns the actual curtailed amount.
        """
        actual = min(amount_kw, self.p_output_kw)
        self.curtailment_kw = actual
        logger.info("PV %s curtailed by %.2f kW", self.pv_id, actual)
        return actual

    def reset_curtailment(self) -> None:
        self.curtailment_kw = 0.0

    def __repr__(self) -> str:
        return (
            f"PV(id={self.pv_id!r}, bus={self.bus_id!r}, "
            f"rated={self.rated_kw} kW, output={self.p_output_kw:.2f} kW)"
        )

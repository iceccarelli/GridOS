"""
Bus (node) model for the GridOS digital twin.

A bus represents an electrical node in the distribution network.  It
aggregates injected and consumed power from connected components and
maintains a per-unit voltage magnitude and angle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Bus:
    """Electrical bus (node) in the grid model.

    Parameters
    ----------
    bus_id:
        Unique bus identifier.
    name:
        Human-readable bus name.
    base_kv:
        Base voltage in kilovolts.
    voltage_pu:
        Voltage magnitude in per-unit (initialised to 1.0).
    angle_deg:
        Voltage angle in degrees (initialised to 0.0).
    is_slack:
        Whether this bus is the slack / reference bus.
    p_inject_kw:
        Net active power injection (generation − load) in kW.
    q_inject_kvar:
        Net reactive power injection in kVAR.
    """

    bus_id: str
    name: str = ""
    base_kv: float = 0.4  # default LV
    voltage_pu: float = 1.0
    angle_deg: float = 0.0
    is_slack: bool = False
    p_inject_kw: float = 0.0
    q_inject_kvar: float = 0.0
    connected_components: dict[str, str] = field(default_factory=dict)

    def update(self, dt: float, grid_state: dict | None = None) -> None:
        """Update bus state after a power-flow iteration.

        Parameters
        ----------
        dt:
            Time step in seconds (unused for static bus model).
        grid_state:
            Dictionary with updated ``voltage_pu`` and ``angle_deg``
            from the power-flow solver.
        """
        if grid_state is not None:
            self.voltage_pu = grid_state.get("voltage_pu", self.voltage_pu)
            self.angle_deg = grid_state.get("angle_deg", self.angle_deg)

    def reset_injections(self) -> None:
        """Zero out power injections before re-aggregation."""
        self.p_inject_kw = 0.0
        self.q_inject_kvar = 0.0

    def add_injection(self, p_kw: float, q_kvar: float = 0.0) -> None:
        """Accumulate power injection from a connected component."""
        self.p_inject_kw += p_kw
        self.q_inject_kvar += q_kvar

    def __repr__(self) -> str:
        return (
            f"Bus(id={self.bus_id!r}, V={self.voltage_pu:.4f} pu, "
            f"P={self.p_inject_kw:.1f} kW, Q={self.q_inject_kvar:.1f} kVAR)"
        )

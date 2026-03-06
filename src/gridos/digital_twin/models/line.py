"""
Distribution line model for the GridOS digital twin.

Models a single-phase or three-phase distribution line segment with
series resistance and reactance.  Used by the power-flow solver to
compute voltage drops and losses.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Line:
    """Distribution line segment.

    Parameters
    ----------
    line_id:
        Unique line identifier.
    from_bus:
        Sending-end bus identifier.
    to_bus:
        Receiving-end bus identifier.
    r_ohm_per_km:
        Resistance in ohms per kilometre.
    x_ohm_per_km:
        Reactance in ohms per kilometre.
    length_km:
        Line length in kilometres.
    rating_kva:
        Thermal rating in kVA.
    """

    line_id: str
    from_bus: str
    to_bus: str
    r_ohm_per_km: float = 0.1
    x_ohm_per_km: float = 0.08
    length_km: float = 1.0
    rating_kva: float = 500.0

    # Computed at runtime
    p_loss_kw: float = 0.0
    q_loss_kvar: float = 0.0
    loading_percent: float = 0.0

    @property
    def r_total(self) -> float:
        """Total series resistance in ohms."""
        return self.r_ohm_per_km * self.length_km

    @property
    def x_total(self) -> float:
        """Total series reactance in ohms."""
        return self.x_ohm_per_km * self.length_km

    @property
    def z_total(self) -> float:
        """Total impedance magnitude in ohms."""
        return math.sqrt(self.r_total**2 + self.x_total**2)

    def update(self, dt: float, grid_state: dict | None = None) -> None:
        """Recompute line losses and loading from power-flow results.

        Parameters
        ----------
        dt:
            Time step in seconds (unused for static line model).
        grid_state:
            Dictionary with ``p_flow_kw``, ``q_flow_kvar``, and
            ``base_kv`` from the power-flow solver.
        """
        if grid_state is None:
            return

        p_flow = grid_state.get("p_flow_kw", 0.0)
        q_flow = grid_state.get("q_flow_kvar", 0.0)
        base_kv = grid_state.get("base_kv", 0.4)

        # Approximate current magnitude
        s_kva = math.sqrt(p_flow**2 + q_flow**2)
        if base_kv > 0:
            i_a = s_kva / (math.sqrt(3) * base_kv) if base_kv > 0 else 0.0
        else:
            i_a = 0.0

        # I²R losses
        self.p_loss_kw = 3 * (i_a**2) * self.r_total / 1000.0
        self.q_loss_kvar = 3 * (i_a**2) * self.x_total / 1000.0

        # Loading
        if self.rating_kva > 0:
            self.loading_percent = (s_kva / self.rating_kva) * 100.0
        else:
            self.loading_percent = 0.0

    def __repr__(self) -> str:
        return (
            f"Line(id={self.line_id!r}, {self.from_bus}->{self.to_bus}, "
            f"Z={self.z_total:.4f} Ω, loading={self.loading_percent:.1f}%)"
        )

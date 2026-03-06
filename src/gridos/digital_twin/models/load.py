"""
Load model for the GridOS digital twin.

Represents an electrical load connected to a bus.  Supports constant-power,
constant-impedance, and time-varying (profile-based) load models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Load:
    """Electrical load component.

    Parameters
    ----------
    load_id:
        Unique load identifier.
    bus_id:
        Bus to which the load is connected.
    p_kw:
        Active power demand in kW.
    q_kvar:
        Reactive power demand in kVAR.
    power_factor:
        Load power factor (lagging positive).
    is_controllable:
        Whether the load participates in demand response.
    profile:
        Optional time-series profile (list of per-step kW values).
    """

    load_id: str
    bus_id: str
    p_kw: float = 50.0
    q_kvar: float = 10.0
    power_factor: float = 0.95
    is_controllable: bool = False
    profile: list[float] = field(default_factory=list)

    # Runtime
    _step_index: int = 0
    curtailed_kw: float = 0.0

    def update(self, dt: float, grid_state: dict | None = None) -> None:
        """Advance the load model by one time step.

        If a profile is provided, the load follows the profile values
        sequentially.  Otherwise the load remains at its static setpoint.

        Parameters
        ----------
        dt:
            Time step in seconds.
        grid_state:
            Optional grid conditions (e.g. voltage for ZIP model).
        """
        if self.profile:
            self.p_kw = self.profile[self._step_index % len(self.profile)]
            self._step_index += 1

        # Apply curtailment
        effective_p = max(self.p_kw - self.curtailed_kw, 0.0)
        self.p_kw = effective_p

    def curtail(self, amount_kw: float) -> float:
        """Apply demand-response curtailment.

        Returns the actual curtailed amount (may be less than requested).
        """
        if not self.is_controllable:
            logger.debug(
                "Load %s is not controllable — curtailment ignored", self.load_id
            )
            return 0.0
        actual = min(amount_kw, self.p_kw)
        self.curtailed_kw = actual
        logger.info("Load %s curtailed by %.2f kW", self.load_id, actual)
        return actual

    def reset_curtailment(self) -> None:
        """Remove any active curtailment."""
        self.curtailed_kw = 0.0

    def __repr__(self) -> str:
        return (
            f"Load(id={self.load_id!r}, bus={self.bus_id!r}, "
            f"P={self.p_kw:.1f} kW, Q={self.q_kvar:.1f} kVAR)"
        )

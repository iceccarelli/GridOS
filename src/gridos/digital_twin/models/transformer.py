"""
Transformer model for the GridOS digital twin.

Models a two-winding distribution transformer with series impedance,
tap ratio, and thermal loading calculation.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Transformer:
    """Two-winding distribution transformer.

    Parameters
    ----------
    transformer_id:
        Unique transformer identifier.
    from_bus:
        High-voltage side bus identifier.
    to_bus:
        Low-voltage side bus identifier.
    rated_kva:
        Nameplate rating in kVA.
    hv_kv:
        High-voltage side rated voltage in kV.
    lv_kv:
        Low-voltage side rated voltage in kV.
    r_percent:
        Winding resistance in percent of rated impedance.
    x_percent:
        Leakage reactance in percent of rated impedance.
    tap_ratio:
        Off-load tap ratio (HV/LV turns ratio adjustment, 1.0 = nominal).
    """

    transformer_id: str
    from_bus: str
    to_bus: str
    rated_kva: float = 500.0
    hv_kv: float = 11.0
    lv_kv: float = 0.4
    r_percent: float = 1.0
    x_percent: float = 5.0
    tap_ratio: float = 1.0

    # Runtime state
    p_loss_kw: float = 0.0
    q_loss_kvar: float = 0.0
    loading_percent: float = 0.0

    @property
    def z_base_ohm(self) -> float:
        """Base impedance on the LV side (ohms)."""
        if self.rated_kva > 0:
            return (self.lv_kv**2 * 1000) / self.rated_kva
        return 1.0

    @property
    def r_ohm(self) -> float:
        """Series resistance in ohms (LV side)."""
        return (self.r_percent / 100.0) * self.z_base_ohm

    @property
    def x_ohm(self) -> float:
        """Series reactance in ohms (LV side)."""
        return (self.x_percent / 100.0) * self.z_base_ohm

    def update(self, dt: float, grid_state: dict | None = None) -> None:
        """Recompute transformer losses and loading.

        Parameters
        ----------
        dt:
            Time step in seconds.
        grid_state:
            Dictionary with ``p_flow_kw`` and ``q_flow_kvar``.
        """
        if grid_state is None:
            return

        p_flow = grid_state.get("p_flow_kw", 0.0)
        q_flow = grid_state.get("q_flow_kvar", 0.0)
        s_kva = math.sqrt(p_flow**2 + q_flow**2)

        # Current on LV side
        i_a = s_kva / (math.sqrt(3) * self.lv_kv) if self.lv_kv > 0 else 0.0

        self.p_loss_kw = 3 * (i_a**2) * self.r_ohm / 1000.0
        self.q_loss_kvar = 3 * (i_a**2) * self.x_ohm / 1000.0

        if self.rated_kva > 0:
            self.loading_percent = (s_kva / self.rated_kva) * 100.0

    def __repr__(self) -> str:
        return (
            f"Transformer(id={self.transformer_id!r}, "
            f"{self.hv_kv}kV/{self.lv_kv}kV, "
            f"{self.rated_kva} kVA, loading={self.loading_percent:.1f}%)"
        )

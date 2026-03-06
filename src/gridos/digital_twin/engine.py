"""
Digital Twin simulation engine for GridOS.

Provides :class:`GridModel` (a container for buses, lines, transformers,
and DER components) and :class:`DigitalTwinEngine` (the co-simulation
orchestrator that steps the model forward in time and records history).

The power-flow solver uses a simplified backward/forward sweep algorithm
suitable for radial distribution networks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from gridos.digital_twin.models.battery import Battery
from gridos.digital_twin.models.bus import Bus
from gridos.digital_twin.models.ev_charger import EVCharger
from gridos.digital_twin.models.line import Line
from gridos.digital_twin.models.load import Load
from gridos.digital_twin.models.pv import PV
from gridos.digital_twin.models.transformer import Transformer

logger = logging.getLogger(__name__)

ComponentType = Bus | Line | Transformer | Load | PV | Battery | EVCharger


# ── Grid Model ───────────────────────────────────────────────────────────────


@dataclass
class GridModel:
    """Container for all grid components.

    Holds buses, lines, transformers, and DER components.  Provides a
    simplified backward/forward sweep power-flow solver for radial
    distribution networks.
    """

    name: str = "default_grid"
    buses: dict[str, Bus] = field(default_factory=dict)
    lines: dict[str, Line] = field(default_factory=dict)
    transformers: dict[str, Transformer] = field(default_factory=dict)
    loads: dict[str, Load] = field(default_factory=dict)
    pvs: dict[str, PV] = field(default_factory=dict)
    batteries: dict[str, Battery] = field(default_factory=dict)
    ev_chargers: dict[str, EVCharger] = field(default_factory=dict)

    # ── Component Registration ───────────────────────────────────────

    def add_bus(self, bus: Bus) -> None:
        self.buses[bus.bus_id] = bus

    def add_line(self, line: Line) -> None:
        self.lines[line.line_id] = line

    def add_transformer(self, transformer: Transformer) -> None:
        self.transformers[transformer.transformer_id] = transformer

    def add_load(self, load: Load) -> None:
        self.loads[load.load_id] = load

    def add_pv(self, pv: PV) -> None:
        self.pvs[pv.pv_id] = pv

    def add_battery(self, battery: Battery) -> None:
        self.batteries[battery.battery_id] = battery

    def add_ev_charger(self, charger: EVCharger) -> None:
        self.ev_chargers[charger.charger_id] = charger

    # ── Aggregation ──────────────────────────────────────────────────

    def _aggregate_injections(self) -> None:
        """Aggregate DER injections onto their respective buses."""
        for bus in self.buses.values():
            bus.reset_injections()

        for load in self.loads.values():
            if load.bus_id in self.buses:
                self.buses[load.bus_id].add_injection(-load.p_kw, -load.q_kvar)

        for pv in self.pvs.values():
            if pv.bus_id in self.buses:
                self.buses[pv.bus_id].add_injection(pv.p_output_kw)

        for batt in self.batteries.values():
            if batt.bus_id in self.buses:
                self.buses[batt.bus_id].add_injection(batt.p_output_kw)

        for ev in self.ev_chargers.values():
            if ev.bus_id in self.buses:
                # EV charger is a load
                self.buses[ev.bus_id].add_injection(-ev.p_output_kw)

    # ── Power Flow (Simplified BFS) ─────────────────────────────────

    def _build_adjacency(self) -> dict[str, list[str]]:
        """Build adjacency list from lines and transformers."""
        adj: dict[str, list[str]] = {bid: [] for bid in self.buses}
        for line in self.lines.values():
            if line.from_bus in adj:
                adj[line.from_bus].append(line.to_bus)
            if line.to_bus in adj:
                adj[line.to_bus].append(line.from_bus)
        for tx in self.transformers.values():
            if tx.from_bus in adj:
                adj[tx.from_bus].append(tx.to_bus)
            if tx.to_bus in adj:
                adj[tx.to_bus].append(tx.from_bus)
        return adj

    def _find_slack(self) -> str | None:
        """Return the bus_id of the slack bus."""
        for bus in self.buses.values():
            if bus.is_slack:
                return bus.bus_id
        return None

    def simulate(
        self, max_iterations: int = 50, tolerance: float = 1e-4
    ) -> dict[str, Any]:
        """Run a simplified backward/forward sweep power flow.

        Returns a summary dictionary with convergence info, total losses,
        and per-bus voltages.
        """
        self._aggregate_injections()

        slack_id = self._find_slack()
        if slack_id is None:
            logger.warning("No slack bus defined — skipping power flow")
            return {"converged": False, "reason": "no_slack_bus"}

        # Initialise voltages
        for bus in self.buses.values():
            if bus.is_slack:
                bus.voltage_pu = 1.0
                bus.angle_deg = 0.0

        converged = False
        iteration = 0
        total_p_loss = 0.0
        total_q_loss = 0.0

        for _iteration in range(1, max_iterations + 1):
            max_delta = 0.0

            # Forward sweep — propagate voltage from slack to leaves
            for line in self.lines.values():
                from_bus = self.buses.get(line.from_bus)
                to_bus = self.buses.get(line.to_bus)
                if from_bus is None or to_bus is None:
                    continue

                # Simplified voltage drop: ΔV ≈ (P·R + Q·X) / (V · kV²)
                base_kv = from_bus.base_kv if from_bus.base_kv > 0 else 0.4
                v_from = from_bus.voltage_pu * base_kv
                if v_from > 0:
                    p = to_bus.p_inject_kw  # net injection at receiving end
                    q = to_bus.q_inject_kvar
                    delta_v = (p * line.r_total + q * line.x_total) / (v_from * 1000)
                    new_v_pu = from_bus.voltage_pu - delta_v / base_kv
                    new_v_pu = max(new_v_pu, 0.8)  # clamp
                    max_delta = max(max_delta, abs(to_bus.voltage_pu - new_v_pu))
                    to_bus.voltage_pu = new_v_pu

                # Update line losses
                line.update(
                    0,
                    {
                        "p_flow_kw": abs(to_bus.p_inject_kw),
                        "q_flow_kvar": abs(to_bus.q_inject_kvar),
                        "base_kv": base_kv,
                    },
                )

            # Similarly for transformers
            for tx in self.transformers.values():
                from_bus = self.buses.get(tx.from_bus)
                to_bus = self.buses.get(tx.to_bus)
                if from_bus is None or to_bus is None:
                    continue
                tx.update(
                    0,
                    {
                        "p_flow_kw": abs(to_bus.p_inject_kw),
                        "q_flow_kvar": abs(to_bus.q_inject_kvar),
                    },
                )

            if max_delta < tolerance:
                converged = True
                break

        # Compute total losses
        total_p_loss = sum(ln.p_loss_kw for ln in self.lines.values()) + sum(
            t.p_loss_kw for t in self.transformers.values()
        )
        total_q_loss = sum(ln.q_loss_kvar for ln in self.lines.values()) + sum(
            t.q_loss_kvar for t in self.transformers.values()
        )

        result = {
            "converged": converged,
            "iterations": iteration,
            "max_delta_pu": tolerance if converged else max_delta,
            "total_p_loss_kw": total_p_loss,
            "total_q_loss_kvar": total_q_loss,
            "bus_voltages": {
                bid: {"voltage_pu": b.voltage_pu, "angle_deg": b.angle_deg}
                for bid, b in self.buses.items()
            },
        }
        logger.info(
            "Power flow %s in %d iterations (loss=%.2f kW)",
            "converged" if converged else "did not converge",
            iteration,
            total_p_loss,
        )
        return result


# ── Digital Twin Engine ──────────────────────────────────────────────────────


class DigitalTwinEngine:
    """Co-simulation orchestrator.

    Steps the :class:`GridModel` forward in time, updates all components,
    runs power flow, and records history for analysis.

    Parameters
    ----------
    grid_model:
        The grid model to simulate.
    dt_seconds:
        Simulation time step in seconds (default 900 = 15 min).
    """

    def __init__(self, grid_model: GridModel, dt_seconds: float = 900.0) -> None:
        self.grid = grid_model
        self.dt = dt_seconds
        self.current_time: datetime = datetime.utcnow()
        self.step_count: int = 0
        self.history: list[dict[str, Any]] = []

    def set_conditions(self, conditions: dict[str, Any]) -> None:
        """Set environmental conditions for the next step.

        Parameters
        ----------
        conditions:
            Dictionary with keys like ``irradiance_w_m2``,
            ``temperature_c``, etc.
        """
        for pv in self.grid.pvs.values():
            pv.update(self.dt, conditions)

    def step(self, conditions: dict[str, Any] | None = None) -> dict[str, Any]:
        """Advance the simulation by one time step.

        Parameters
        ----------
        conditions:
            Optional environmental conditions for this step.

        Returns
        -------
        dict
            Power-flow results and component states.
        """
        # Update DER components
        if conditions:
            for pv in self.grid.pvs.values():
                pv.update(self.dt, conditions)

        for load in self.grid.loads.values():
            load.update(self.dt)

        for batt in self.grid.batteries.values():
            batt.update(self.dt)

        for ev in self.grid.ev_chargers.values():
            ev.update(self.dt)

        # Run power flow
        pf_result = self.grid.simulate()

        # Record snapshot
        snapshot = {
            "step": self.step_count,
            "time": self.current_time.isoformat(),
            "power_flow": pf_result,
            "total_generation_kw": sum(pv.p_output_kw for pv in self.grid.pvs.values())
            + sum(
                b.p_output_kw for b in self.grid.batteries.values() if b.p_output_kw > 0
            ),
            "total_load_kw": sum(ld.p_kw for ld in self.grid.loads.values())
            + sum(ev.p_output_kw for ev in self.grid.ev_chargers.values()),
            "total_storage_kw": sum(
                b.p_output_kw for b in self.grid.batteries.values()
            ),
            "battery_soc": {
                bid: b.soc_percent for bid, b in self.grid.batteries.items()
            },
            "bus_voltages": pf_result.get("bus_voltages", {}),
        }
        self.history.append(snapshot)

        self.current_time += timedelta(seconds=self.dt)
        self.step_count += 1

        return snapshot

    def run(
        self,
        steps: int,
        conditions_series: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Run multiple simulation steps.

        Parameters
        ----------
        steps:
            Number of time steps to simulate.
        conditions_series:
            Optional list of per-step environmental conditions.

        Returns
        -------
        list[dict]
            List of per-step snapshots.
        """
        results: list[dict[str, Any]] = []
        for i in range(steps):
            cond = (
                conditions_series[i]
                if conditions_series and i < len(conditions_series)
                else None
            )
            results.append(self.step(cond))
        return results

    def reset(self) -> None:
        """Reset the engine state."""
        self.step_count = 0
        self.history.clear()
        self.current_time = datetime.utcnow()

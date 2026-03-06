"""
MILP-based energy management scheduler for GridOS.

Uses PuLP to formulate and solve a Mixed-Integer Linear Programming
problem that minimises energy cost (or maximises self-consumption)
subject to battery, load, and grid constraints.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    """Configuration for the optimisation problem.

    Parameters
    ----------
    time_horizon_hours:
        Planning horizon in hours.
    time_step_minutes:
        Granularity of each time step in minutes.
    battery_capacity_kwh:
        Usable battery capacity in kWh.
    battery_max_charge_kw:
        Maximum charge rate in kW.
    battery_max_discharge_kw:
        Maximum discharge rate in kW.
    battery_efficiency:
        Round-trip efficiency (0–1).
    battery_soc_min:
        Minimum SoC (0–1).
    battery_soc_max:
        Maximum SoC (0–1).
    battery_soc_initial:
        Initial SoC (0–1).
    grid_import_limit_kw:
        Maximum power import from the main grid.
    grid_export_limit_kw:
        Maximum power export to the main grid.
    import_price:
        Electricity import price per kWh (can be array for TOU).
    export_price:
        Electricity export price per kWh.
    """

    time_horizon_hours: int = 24
    time_step_minutes: int = 15
    battery_capacity_kwh: float = 100.0
    battery_max_charge_kw: float = 50.0
    battery_max_discharge_kw: float = 50.0
    battery_efficiency: float = 0.92
    battery_soc_min: float = 0.1
    battery_soc_max: float = 0.95
    battery_soc_initial: float = 0.5
    grid_import_limit_kw: float = 200.0
    grid_export_limit_kw: float = 200.0
    import_price: float = 0.25  # $/kWh or array
    export_price: float = 0.05  # $/kWh

    @property
    def n_steps(self) -> int:
        return int(self.time_horizon_hours * 60 / self.time_step_minutes)

    @property
    def dt_hours(self) -> float:
        return self.time_step_minutes / 60.0


@dataclass
class ScheduleResult:
    """Result of the optimisation run."""

    status: str = "unsolved"
    objective_value: float = 0.0
    battery_power_kw: list[float] = field(default_factory=list)
    battery_soc: list[float] = field(default_factory=list)
    grid_import_kw: list[float] = field(default_factory=list)
    grid_export_kw: list[float] = field(default_factory=list)
    net_load_kw: list[float] = field(default_factory=list)
    solver_time_seconds: float = 0.0


class Scheduler:
    """MILP energy management scheduler.

    Parameters
    ----------
    config:
        Scheduler configuration.
    """

    def __init__(self, config: SchedulerConfig | None = None) -> None:
        self.config = config or SchedulerConfig()
        self._pulp_available: bool = False

        try:
            import pulp  # noqa: F401

            self._pulp_available = True
        except ImportError:
            logger.warning(
                "PuLP not installed — Scheduler will use a greedy heuristic."
            )

    def solve(
        self,
        load_forecast_kw: np.ndarray,
        solar_forecast_kw: np.ndarray,
        import_prices: np.ndarray | None = None,
        export_prices: np.ndarray | None = None,
    ) -> ScheduleResult:
        """Solve the optimal dispatch problem.

        Parameters
        ----------
        load_forecast_kw:
            1-D array of forecasted load for each time step (kW).
        solar_forecast_kw:
            1-D array of forecasted solar generation for each step (kW).
        import_prices:
            Optional per-step import prices ($/kWh).
        export_prices:
            Optional per-step export prices ($/kWh).

        Returns
        -------
        ScheduleResult
            Optimal battery dispatch schedule and grid exchange.
        """
        n = self.config.n_steps
        if len(load_forecast_kw) < n or len(solar_forecast_kw) < n:
            raise ValueError(
                f"Forecast arrays must have at least {n} elements "
                f"(got load={len(load_forecast_kw)}, solar={len(solar_forecast_kw)})"
            )

        if self._pulp_available:
            return self._solve_milp(
                load_forecast_kw[:n],
                solar_forecast_kw[:n],
                import_prices[:n] if import_prices is not None else None,
                export_prices[:n] if export_prices is not None else None,
            )
        return self._solve_greedy(load_forecast_kw[:n], solar_forecast_kw[:n])

    # ── MILP Solver ──────────────────────────────────────────────────

    def _solve_milp(
        self,
        load_kw: np.ndarray,
        solar_kw: np.ndarray,
        import_prices: np.ndarray | None,
        export_prices: np.ndarray | None,
    ) -> ScheduleResult:
        import time

        import pulp

        cfg = self.config
        n = cfg.n_steps
        dt = cfg.dt_hours

        # Prices
        c_imp = (
            import_prices if import_prices is not None else np.full(n, cfg.import_price)
        )
        c_exp = (
            export_prices if export_prices is not None else np.full(n, cfg.export_price)
        )

        # Problem
        prob = pulp.LpProblem("GridOS_EnergyScheduler", pulp.LpMinimize)

        # Decision variables
        p_charge = [
            pulp.LpVariable(f"p_chg_{t}", 0, cfg.battery_max_charge_kw)
            for t in range(n)
        ]
        p_discharge = [
            pulp.LpVariable(f"p_dis_{t}", 0, cfg.battery_max_discharge_kw)
            for t in range(n)
        ]
        p_import = [
            pulp.LpVariable(f"p_imp_{t}", 0, cfg.grid_import_limit_kw) for t in range(n)
        ]
        p_export = [
            pulp.LpVariable(f"p_exp_{t}", 0, cfg.grid_export_limit_kw) for t in range(n)
        ]
        soc = [
            pulp.LpVariable(f"soc_{t}", cfg.battery_soc_min, cfg.battery_soc_max)
            for t in range(n + 1)
        ]

        # Binary variables to prevent simultaneous charge/discharge
        z = [pulp.LpVariable(f"z_{t}", cat="Binary") for t in range(n)]

        # Objective: minimise net import cost
        prob += pulp.lpSum(
            c_imp[t] * p_import[t] * dt - c_exp[t] * p_export[t] * dt for t in range(n)
        )

        # Constraints
        # Initial SoC
        prob += soc[0] == cfg.battery_soc_initial

        for t in range(n):
            net_load = float(load_kw[t]) - float(solar_kw[t])

            # Power balance
            prob += p_import[t] - p_export[t] + p_discharge[t] - p_charge[t] == net_load

            # SoC dynamics
            prob += soc[t + 1] == (
                soc[t]
                + (cfg.battery_efficiency * p_charge[t] * dt / cfg.battery_capacity_kwh)
                - (
                    p_discharge[t]
                    * dt
                    / (cfg.battery_efficiency * cfg.battery_capacity_kwh)
                )
            )

            # Mutual exclusion of charge / discharge
            prob += p_charge[t] <= cfg.battery_max_charge_kw * z[t]
            prob += p_discharge[t] <= cfg.battery_max_discharge_kw * (1 - z[t])

        # Solve
        t0 = time.time()
        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=60)
        prob.solve(solver)
        solve_time = time.time() - t0

        status = pulp.LpStatus[prob.status]
        logger.info("MILP solved: status=%s, time=%.2fs", status, solve_time)

        result = ScheduleResult(
            status=status,
            objective_value=pulp.value(prob.objective) or 0.0,
            battery_power_kw=[
                float(pulp.value(p_discharge[t]) or 0)
                - float(pulp.value(p_charge[t]) or 0)
                for t in range(n)
            ],
            battery_soc=[float(pulp.value(soc[t]) or 0) * 100 for t in range(n + 1)],
            grid_import_kw=[float(pulp.value(p_import[t]) or 0) for t in range(n)],
            grid_export_kw=[float(pulp.value(p_export[t]) or 0) for t in range(n)],
            net_load_kw=[float(load_kw[t] - solar_kw[t]) for t in range(n)],
            solver_time_seconds=solve_time,
        )
        return result

    # ── Greedy Heuristic ─────────────────────────────────────────────

    def _solve_greedy(
        self, load_kw: np.ndarray, solar_kw: np.ndarray
    ) -> ScheduleResult:
        """Simple greedy heuristic when PuLP is not available."""
        cfg = self.config
        n = cfg.n_steps
        dt = cfg.dt_hours

        soc = cfg.battery_soc_initial
        battery_power: list[float] = []
        soc_history: list[float] = [soc * 100]
        grid_import: list[float] = []
        grid_export: list[float] = []

        for t in range(n):
            net = float(load_kw[t] - solar_kw[t])

            if net > 0:
                # Deficit — discharge battery first
                discharge = min(net, cfg.battery_max_discharge_kw)
                energy = discharge * dt
                available = (soc - cfg.battery_soc_min) * cfg.battery_capacity_kwh
                if energy > available:
                    discharge = available / dt if dt > 0 else 0
                soc -= discharge * dt / cfg.battery_capacity_kwh
                remaining = net - discharge
                battery_power.append(discharge)
                grid_import.append(max(remaining, 0))
                grid_export.append(0)
            else:
                # Surplus — charge battery
                surplus = -net
                charge = min(surplus, cfg.battery_max_charge_kw)
                headroom = (cfg.battery_soc_max - soc) * cfg.battery_capacity_kwh
                energy = charge * dt * cfg.battery_efficiency
                if energy > headroom:
                    charge = headroom / (dt * cfg.battery_efficiency) if dt > 0 else 0
                soc += charge * dt * cfg.battery_efficiency / cfg.battery_capacity_kwh
                remaining = surplus - charge
                battery_power.append(-charge)
                grid_import.append(0)
                grid_export.append(max(remaining, 0))

            soc = max(cfg.battery_soc_min, min(soc, cfg.battery_soc_max))
            soc_history.append(soc * 100)

        return ScheduleResult(
            status="Greedy",
            objective_value=0.0,
            battery_power_kw=battery_power,
            battery_soc=soc_history,
            grid_import_kw=grid_import,
            grid_export_kw=grid_export,
            net_load_kw=[float(load_kw[t] - solar_kw[t]) for t in range(n)],
        )

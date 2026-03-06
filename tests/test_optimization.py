"""
Tests for the GridOS optimisation module.
"""

from __future__ import annotations

import numpy as np
import pytest

from gridos.optimization.scheduler import Scheduler, SchedulerConfig


class TestSchedulerConfig:
    """Tests for SchedulerConfig."""

    def test_defaults(self):
        cfg = SchedulerConfig()
        assert cfg.n_steps == 96  # 24h / 15min
        assert cfg.dt_hours == 0.25

    def test_custom(self):
        cfg = SchedulerConfig(time_horizon_hours=48, time_step_minutes=30)
        assert cfg.n_steps == 96  # 48h / 30min


class TestScheduler:
    """Tests for the Scheduler."""

    def test_greedy_solver(self):
        """Test the greedy heuristic (always available)."""
        cfg = SchedulerConfig(
            time_horizon_hours=24,
            time_step_minutes=15,
            battery_capacity_kwh=100,
            battery_max_charge_kw=50,
            battery_max_discharge_kw=50,
        )
        scheduler = Scheduler(cfg)
        # Force greedy
        scheduler._pulp_available = False

        n = cfg.n_steps
        load = np.full(n, 60.0)
        solar = np.concatenate(
            [
                np.zeros(24),  # night
                np.linspace(0, 40, 24),  # morning ramp
                np.full(24, 40),  # midday
                np.linspace(40, 0, 24),  # evening ramp
            ]
        )

        result = scheduler.solve(load, solar)
        assert result.status == "Greedy"
        assert len(result.battery_power_kw) == n
        assert len(result.battery_soc) == n + 1

    def test_milp_solver(self):
        """Test the MILP solver (requires PuLP)."""
        try:
            import importlib.util

            if importlib.util.find_spec("pulp") is None:
                pytest.skip("PuLP not installed")
        except (ImportError, ModuleNotFoundError):
            pytest.skip("PuLP not installed")

        cfg = SchedulerConfig(
            time_horizon_hours=24,
            time_step_minutes=15,
            battery_capacity_kwh=100,
        )
        scheduler = Scheduler(cfg)
        n = cfg.n_steps
        load = np.full(n, 60.0)
        solar = np.concatenate(
            [
                np.zeros(24),
                np.linspace(0, 40, 24),
                np.full(24, 40),
                np.linspace(40, 0, 24),
            ]
        )

        result = scheduler.solve(load, solar)
        assert result.status == "Optimal"
        assert len(result.battery_power_kw) == n

    def test_insufficient_forecast_length(self):
        scheduler = Scheduler()
        with pytest.raises(ValueError, match="at least"):
            scheduler.solve(np.array([1.0]), np.array([1.0]))

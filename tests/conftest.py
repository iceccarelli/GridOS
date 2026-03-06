"""
Shared pytest fixtures for the GridOS test suite.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture
def sample_telemetry():
    """Return a sample DERTelemetry instance."""
    from gridos.models.common import DERStatus, DERTelemetry

    return DERTelemetry(
        device_id="test-pv-001",
        timestamp=datetime.now(timezone.utc),
        power_kw=8.5,
        reactive_power_kvar=1.2,
        voltage_v=235.0,
        current_a=12.3,
        frequency_hz=50.01,
        status=DERStatus.ONLINE,
    )


@pytest.fixture
def sample_grid_model():
    """Return a simple grid model with one bus, one PV, one load, and one battery."""
    from gridos.digital_twin.engine import GridModel
    from gridos.digital_twin.models.battery import Battery
    from gridos.digital_twin.models.bus import Bus
    from gridos.digital_twin.models.line import Line
    from gridos.digital_twin.models.load import Load
    from gridos.digital_twin.models.pv import PV

    grid = GridModel(name="test_grid")

    # Slack bus
    slack = Bus(bus_id="bus_0", name="Slack", base_kv=11.0, is_slack=True)
    grid.add_bus(slack)

    # LV bus
    lv_bus = Bus(bus_id="bus_1", name="LV Bus", base_kv=0.4)
    grid.add_bus(lv_bus)

    # Line
    line = Line(
        line_id="line_01",
        from_bus="bus_0",
        to_bus="bus_1",
        r_ohm_per_km=0.2,
        x_ohm_per_km=0.1,
        length_km=0.5,
        rating_kva=500,
    )
    grid.add_line(line)

    # Load
    load = Load(load_id="load_1", bus_id="bus_1", p_kw=50, q_kvar=10)
    grid.add_load(load)

    # PV
    pv = PV(pv_id="pv_1", bus_id="bus_1", rated_kw=20)
    grid.add_pv(pv)

    # Battery
    battery = Battery(
        battery_id="batt_1",
        bus_id="bus_1",
        capacity_kwh=100,
        max_charge_kw=50,
        max_discharge_kw=50,
        soc=0.5,
    )
    grid.add_battery(battery)

    return grid


@pytest.fixture
def sample_timeseries():
    """Return a synthetic 7-day load time series (15-min intervals)."""
    np.random.seed(42)
    n = 7 * 96  # 7 days × 96 steps/day
    base = 50 + 30 * np.sin(np.linspace(0, 14 * np.pi, n))
    noise = np.random.normal(0, 3, n)
    return (base + noise).astype(np.float32)

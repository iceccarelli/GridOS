#!/usr/bin/env python3
"""
GridOS Quick Start Demo
=======================

This script demonstrates the core GridOS capabilities:
1. Building a grid model with DER components
2. Running a digital twin simulation
3. Generating a forecast
4. Running the optimisation scheduler

Run with: python notebooks/01_quickstart.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from gridos.digital_twin.engine import DigitalTwinEngine, GridModel
from gridos.digital_twin.models.battery import Battery
from gridos.digital_twin.models.bus import Bus
from gridos.digital_twin.models.ev_charger import EVCharger
from gridos.digital_twin.models.line import Line
from gridos.digital_twin.models.load import Load
from gridos.digital_twin.models.pv import PV
from gridos.digital_twin.models.transformer import Transformer
from gridos.digital_twin.ml.forecaster import LSTMForecaster
from gridos.digital_twin.ml.anomaly_detector import IsolationForestDetector
from gridos.optimization.scheduler import Scheduler, SchedulerConfig


def build_sample_grid() -> GridModel:
    """Build a sample distribution grid model."""
    grid = GridModel(name="demo_microgrid")

    # Buses
    grid.add_bus(Bus(bus_id="bus_slack", name="Grid Connection", base_kv=11.0, is_slack=True))
    grid.add_bus(Bus(bus_id="bus_tx_lv", name="Transformer LV", base_kv=0.4))
    grid.add_bus(Bus(bus_id="bus_res", name="Residential", base_kv=0.4))
    grid.add_bus(Bus(bus_id="bus_comm", name="Commercial", base_kv=0.4))

    # Transformer
    grid.add_transformer(Transformer(
        transformer_id="tx_main",
        from_bus="bus_slack",
        to_bus="bus_tx_lv",
        rated_kva=500,
        hv_kv=11.0,
        lv_kv=0.4,
    ))

    # Lines
    grid.add_line(Line(
        line_id="line_res",
        from_bus="bus_tx_lv",
        to_bus="bus_res",
        r_ohm_per_km=0.2,
        x_ohm_per_km=0.1,
        length_km=0.3,
    ))
    grid.add_line(Line(
        line_id="line_comm",
        from_bus="bus_tx_lv",
        to_bus="bus_comm",
        r_ohm_per_km=0.15,
        x_ohm_per_km=0.08,
        length_km=0.5,
    ))

    # Loads
    grid.add_load(Load(load_id="load_res", bus_id="bus_res", p_kw=80, q_kvar=15))
    grid.add_load(Load(load_id="load_comm", bus_id="bus_comm", p_kw=120, q_kvar=25))

    # PV systems
    grid.add_pv(PV(pv_id="pv_res", bus_id="bus_res", rated_kw=30, area_m2=165))
    grid.add_pv(PV(pv_id="pv_comm", bus_id="bus_comm", rated_kw=50, area_m2=275))

    # Battery
    grid.add_battery(Battery(
        battery_id="batt_comm",
        bus_id="bus_comm",
        capacity_kwh=200,
        max_charge_kw=100,
        max_discharge_kw=100,
        soc=0.5,
    ))

    # EV Charger
    ev = EVCharger(charger_id="ev_res", bus_id="bus_res", max_power_kw=22)
    ev.plug_in(ev_battery_kwh=60, ev_soc=0.3, target_soc=0.9)
    grid.add_ev_charger(ev)

    return grid


def demo_digital_twin():
    """Demonstrate the digital twin simulation."""
    print("=" * 60)
    print("  GridOS Digital Twin Demo")
    print("=" * 60)

    grid = build_sample_grid()
    engine = DigitalTwinEngine(grid, dt_seconds=900)

    # Simulate 24 hours (96 × 15-min steps)
    irradiance_profile = np.concatenate([
        np.zeros(24),                          # 00:00–06:00 (night)
        np.linspace(0, 900, 24),               # 06:00–12:00 (morning)
        np.linspace(900, 800, 12),             # 12:00–15:00 (afternoon)
        np.linspace(800, 0, 24),               # 15:00–21:00 (evening)
        np.zeros(12),                          # 21:00–24:00 (night)
    ])

    conditions = [
        {"irradiance_w_m2": float(irradiance_profile[i]), "temperature_c": 25.0}
        for i in range(96)
    ]

    print(f"\nSimulating {grid.name} for 24 hours (96 steps)...")
    results = engine.run(96, conditions)

    print(f"\nSimulation complete! {len(results)} steps recorded.")
    print(f"Final bus voltages:")
    for bid, v in results[-1]["bus_voltages"].items():
        print(f"  {bid}: {v['voltage_pu']:.4f} pu")
    print(f"Total generation (last step): {results[-1]['total_generation_kw']:.1f} kW")
    print(f"Total load (last step): {results[-1]['total_load_kw']:.1f} kW")


def demo_forecasting():
    """Demonstrate the forecasting module."""
    print("\n" + "=" * 60)
    print("  GridOS Forecasting Demo")
    print("=" * 60)

    # Generate synthetic load data
    np.random.seed(42)
    n = 7 * 96  # 7 days
    t = np.linspace(0, 7 * 2 * np.pi, n)
    load = 60 + 30 * np.sin(t) + np.random.normal(0, 3, n)
    load = load.astype(np.float32)

    forecaster = LSTMForecaster(lookback=96, horizon=96)
    recent = load[-96:]
    forecast = forecaster.predict(recent)

    print(f"\nInput: last 96 values (mean={recent.mean():.1f} kW)")
    print(f"Forecast: next 96 values (mean={forecast.mean():.1f} kW)")
    print(f"Model: {'LSTM' if forecaster._torch_available else 'Persistence fallback'}")


def demo_anomaly_detection():
    """Demonstrate anomaly detection."""
    print("\n" + "=" * 60)
    print("  GridOS Anomaly Detection Demo")
    print("=" * 60)

    np.random.seed(42)
    normal = np.random.randn(500, 3) * 10 + 50
    anomalies = np.array([[200, 200, 200], [0, 0, 0], [-50, 300, -100]])
    X = np.vstack([normal, anomalies])

    detector = IsolationForestDetector(contamination=0.01)
    detector.fit(X)
    predictions = detector.predict(X)

    n_anomalies = predictions.sum()
    print(f"\nAnalysed {len(X)} samples")
    print(f"Detected {n_anomalies} anomalies")
    print(f"Anomaly rate: {n_anomalies/len(X)*100:.1f}%")


def demo_optimization():
    """Demonstrate the optimisation scheduler."""
    print("\n" + "=" * 60)
    print("  GridOS Optimisation Demo")
    print("=" * 60)

    config = SchedulerConfig(
        time_horizon_hours=24,
        time_step_minutes=15,
        battery_capacity_kwh=200,
        battery_max_charge_kw=100,
        battery_max_discharge_kw=100,
        battery_soc_initial=0.5,
    )
    scheduler = Scheduler(config)

    n = config.n_steps
    load = np.full(n, 80.0) + 20 * np.sin(np.linspace(0, 2 * np.pi, n))
    solar = np.concatenate([
        np.zeros(24),
        np.linspace(0, 60, 24),
        np.linspace(60, 50, 12),
        np.linspace(50, 0, 24),
        np.zeros(12),
    ])

    result = scheduler.solve(load.astype(np.float32), solar.astype(np.float32))

    print(f"\nOptimisation status: {result.status}")
    print(f"Objective value: ${result.objective_value:.2f}")
    print(f"Solver time: {result.solver_time_seconds:.3f}s")
    print(f"Battery SoC range: {min(result.battery_soc):.1f}% – {max(result.battery_soc):.1f}%")
    print(f"Max grid import: {max(result.grid_import_kw):.1f} kW")
    print(f"Max grid export: {max(result.grid_export_kw):.1f} kW")


if __name__ == "__main__":
    demo_digital_twin()
    demo_forecasting()
    demo_anomaly_detection()
    demo_optimization()
    print("\n" + "=" * 60)
    print("  All demos completed successfully!")
    print("=" * 60)

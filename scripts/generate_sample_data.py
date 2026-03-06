#!/usr/bin/env python3
"""
Generate sample time-series data for GridOS testing and demos.

Creates CSV files with synthetic load profiles, solar irradiance,
and battery state-of-charge data.

Usage::

    python scripts/generate_sample_data.py --days 30 --output data/
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np


def generate_load_profile(
    start: datetime, days: int, step_minutes: int = 15
) -> list[dict]:
    """Generate a synthetic residential load profile."""
    np.random.seed(42)
    n = int(days * 24 * 60 / step_minutes)
    records = []

    for i in range(n):
        t = start + timedelta(minutes=i * step_minutes)
        hour = t.hour + t.minute / 60.0

        # Base load with daily pattern
        base = 40 + 25 * np.sin((hour - 6) * np.pi / 12)
        # Morning peak
        if 6 <= hour <= 9:
            base += 20 * np.sin((hour - 6) * np.pi / 3)
        # Evening peak
        if 17 <= hour <= 22:
            base += 30 * np.sin((hour - 17) * np.pi / 5)
        # Weekend reduction
        if t.weekday() >= 5:
            base *= 0.8

        noise = np.random.normal(0, 3)
        power = max(base + noise, 5.0)

        records.append({
            "timestamp": t.isoformat() + "Z",
            "power_kw": round(power, 2),
            "reactive_power_kvar": round(power * 0.2, 2),
            "voltage_v": round(230 + np.random.normal(0, 2), 1),
            "current_a": round(power * 1000 / 230 / np.sqrt(3), 2),
            "frequency_hz": round(50 + np.random.normal(0, 0.02), 3),
        })

    return records


def generate_solar_profile(
    start: datetime, days: int, step_minutes: int = 15
) -> list[dict]:
    """Generate a synthetic solar irradiance profile."""
    np.random.seed(123)
    n = int(days * 24 * 60 / step_minutes)
    records = []

    for i in range(n):
        t = start + timedelta(minutes=i * step_minutes)
        hour = t.hour + t.minute / 60.0

        # Solar irradiance (bell curve centred at noon)
        if 5 <= hour <= 20:
            irradiance = 1000 * np.sin((hour - 5) * np.pi / 15)
            irradiance = max(irradiance, 0)
            # Cloud cover variation
            cloud = np.random.uniform(0.7, 1.0)
            irradiance *= cloud
        else:
            irradiance = 0.0

        temp = 15 + 10 * np.sin((hour - 6) * np.pi / 12) + np.random.normal(0, 1)

        records.append({
            "timestamp": t.isoformat() + "Z",
            "irradiance_w_m2": round(irradiance, 1),
            "temperature_c": round(temp, 1),
            "wind_speed_ms": round(max(np.random.normal(3, 1.5), 0), 1),
        })

    return records


def write_csv(records: list[dict], filepath: Path) -> None:
    """Write records to a CSV file."""
    if not records:
        return
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    print(f"  Written {len(records)} records to {filepath}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sample data for GridOS")
    parser.add_argument("--days", type=int, default=7, help="Number of days")
    parser.add_argument("--output", type=str, default="data/", help="Output directory")
    parser.add_argument("--step", type=int, default=15, help="Step size in minutes")
    args = parser.parse_args()

    start = datetime(2025, 1, 1)
    output = Path(args.output)

    print(f"Generating {args.days}-day sample data (step={args.step}min)...")

    load = generate_load_profile(start, args.days, args.step)
    write_csv(load, output / "generated_load_profile.csv")

    solar = generate_solar_profile(start, args.days, args.step)
    write_csv(solar, output / "generated_solar_irradiance.csv")

    print("Done!")


if __name__ == "__main__":
    main()

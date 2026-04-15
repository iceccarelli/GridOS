"""Shared pytest fixtures for the reduced GridOS test suite."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gridos.api.dependencies import close_storage
from gridos.models.common import DERTelemetry


@pytest.fixture(autouse=True)
async def reset_storage() -> None:
    """Ensure each test starts with a fresh storage backend singleton."""
    await close_storage()
    yield
    await close_storage()


@pytest.fixture
def sample_telemetry() -> DERTelemetry:
    """Return a representative telemetry reading for the supported API flow."""
    return DERTelemetry(
        device_id="test-pv-001",
        timestamp=datetime.now(timezone.utc),
        power_kw=8.5,
        reactive_power_kvar=1.2,
        voltage_v=235.0,
        current_a=12.3,
        frequency_hz=50.0,
        energy_kwh=120.5,
        status="online",
    )


@pytest.fixture
def sample_telemetry_batch(sample_telemetry: DERTelemetry) -> list[DERTelemetry]:
    """Return a small telemetry batch for ingestion and query tests."""
    second = sample_telemetry.model_copy(
        update={
            "timestamp": sample_telemetry.timestamp + timedelta(minutes=5),
            "power_kw": 9.2,
        }
    )
    return [sample_telemetry, second]

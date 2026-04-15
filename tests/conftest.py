"""Shared pytest fixtures for the reduced GridOS test suite."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gridos.api.dependencies import close_storage, reset_registries
from gridos.models.common import DERTelemetry


@pytest_asyncio.fixture(autouse=True)
async def reset_runtime_state() -> None:
    """Force each test to start from the supported local-first runtime state."""
    previous_inmemory_flag = os.environ.get("GRIDOS_USE_INMEMORY_STORAGE")
    os.environ["GRIDOS_USE_INMEMORY_STORAGE"] = "true"

    reset_registries()
    await close_storage()
    yield
    reset_registries()
    await close_storage()

    if previous_inmemory_flag is None:
        os.environ.pop("GRIDOS_USE_INMEMORY_STORAGE", None)
    else:
        os.environ["GRIDOS_USE_INMEMORY_STORAGE"] = previous_inmemory_flag


@pytest.fixture
def sample_telemetry() -> DERTelemetry:
    """Return a representative telemetry reading for the supported API flow."""
    return DERTelemetry(
        device_id="test-pv-001",
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=5),
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

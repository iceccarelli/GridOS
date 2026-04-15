"""Model tests for the reduced GridOS launch path."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gridos.models.common import DERStatus, DERTelemetry, DERType, DeviceInfo, TelemetryBatch


class TestDERTelemetry:
    """Validate the telemetry model used by the supported API flow."""

    def test_create_telemetry(self, sample_telemetry) -> None:
        assert sample_telemetry.device_id == "test-pv-001"
        assert sample_telemetry.power_kw == 8.5
        assert sample_telemetry.status == DERStatus.ONLINE

    def test_telemetry_serialization_roundtrip(self, sample_telemetry) -> None:
        data = sample_telemetry.model_dump(mode="json")
        restored = DERTelemetry(**data)

        assert restored.device_id == sample_telemetry.device_id
        assert restored.power_kw == sample_telemetry.power_kw

    def test_telemetry_defaults(self) -> None:
        telemetry = DERTelemetry(device_id="dev-001", power_kw=10.0)

        assert telemetry.reactive_power_kvar == 0.0
        assert telemetry.status == DERStatus.ONLINE
        assert telemetry.voltage_v is None
        assert telemetry.frequency_hz is None

    def test_reject_unrealistic_power(self) -> None:
        with pytest.raises(ValidationError):
            DERTelemetry(device_id="dev-001", power_kw=1_500_000)


class TestDeviceInfo:
    """Validate the small device metadata model still used by the repo."""

    def test_create_device(self) -> None:
        device = DeviceInfo(
            device_id="solar-001",
            name="Rooftop PV",
            der_type=DERType.SOLAR_PV,
            rated_power_kw=10.0,
        )

        assert device.device_id == "solar-001"
        assert device.der_type == DERType.SOLAR_PV


class TestTelemetryBatch:
    """Validate batched telemetry ingestion payloads."""

    def test_batch_accepts_multiple_readings(self, sample_telemetry_batch) -> None:
        batch = TelemetryBatch(readings=sample_telemetry_batch)

        assert len(batch.readings) == 2
        assert batch.readings[0].device_id == "test-pv-001"

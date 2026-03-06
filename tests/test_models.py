"""
Tests for GridOS Pydantic data models.
"""

from __future__ import annotations

from gridos.models.common import (
    ControlCommand,
    ControlMode,
    DERStatus,
    DERTelemetry,
    DERType,
    DeviceInfo,
    TelemetryBatch,
)


class TestDERTelemetry:
    """Tests for the DERTelemetry model."""

    def test_create_telemetry(self, sample_telemetry):
        assert sample_telemetry.device_id == "test-pv-001"
        assert sample_telemetry.power_kw == 8.5
        assert sample_telemetry.status == DERStatus.ONLINE

    def test_telemetry_serialization(self, sample_telemetry):
        data = sample_telemetry.model_dump(mode="json")
        assert "device_id" in data
        assert "timestamp" in data
        restored = DERTelemetry(**data)
        assert restored.device_id == sample_telemetry.device_id

    def test_telemetry_defaults(self):
        t = DERTelemetry(device_id="dev-001", power_kw=10.0)
        assert t.reactive_power_kvar == 0.0
        assert t.status == DERStatus.ONLINE
        # frequency_hz, voltage_v, current_a default to None
        assert t.voltage_v is None
        assert t.frequency_hz is None


class TestDeviceInfo:
    """Tests for the DeviceInfo model."""

    def test_create_device(self):
        device = DeviceInfo(
            device_id="solar-001",
            name="Rooftop PV",
            der_type=DERType.SOLAR_PV,
            rated_power_kw=10.0,
        )
        assert device.der_type == DERType.SOLAR_PV
        assert device.rated_power_kw == 10.0


class TestControlCommand:
    """Tests for the ControlCommand model."""

    def test_create_command(self):
        cmd = ControlCommand(
            device_id="batt-001",
            mode=ControlMode.POWER_SETPOINT,
            setpoint_kw=25.0,
        )
        assert cmd.mode == ControlMode.POWER_SETPOINT
        assert cmd.setpoint_kw == 25.0
        assert cmd.command_id is not None

    def test_command_serialization(self):
        cmd = ControlCommand(
            device_id="batt-001",
            mode=ControlMode.DEMAND_RESPONSE,
            setpoint_kw=-10.0,
            duration_seconds=900,
            source="optimizer",
        )
        data = cmd.model_dump(mode="json")
        assert data["mode"] == "demand_response"
        restored = ControlCommand(**data)
        assert restored.setpoint_kw == -10.0


class TestTelemetryBatch:
    """Tests for the TelemetryBatch model."""

    def test_batch(self, sample_telemetry):
        batch = TelemetryBatch(readings=[sample_telemetry, sample_telemetry])
        assert len(batch.readings) == 2

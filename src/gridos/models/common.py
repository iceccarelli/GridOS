"""Common data models for the reduced GridOS launch path.

This module intentionally keeps the public model surface small. It only defines
models that are exercised by the supported end-to-end workflow: device
registration, telemetry ingestion and lookup, and basic control command
acceptance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DERType(str, Enum):
    """Small device taxonomy used by the launch-ready device registry."""

    SOLAR_PV = "solar_pv"
    BATTERY = "battery"
    EV_CHARGER = "ev_charger"
    LOAD = "load"
    OTHER = "other"


class DERStatus(str, Enum):
    """Operational state reported by a device telemetry snapshot."""

    ONLINE = "online"
    OFFLINE = "offline"
    FAULT = "fault"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class ControlMode(str, Enum):
    """Control actions still represented in the reduced launch API."""

    POWER_SETPOINT = "power_setpoint"
    SOC_TARGET = "soc_target"
    CURTAILMENT = "curtailment"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


class GridOSModel(BaseModel):
    """Shared Pydantic configuration for GridOS API models."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        use_enum_values=False,
        str_strip_whitespace=True,
    )


class DeviceInfo(GridOSModel):
    """Minimal metadata stored for a registered device."""

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique identifier for the device.",
        examples=["test-pv-001"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Human-readable device name.",
        examples=["Rooftop PV Inverter #1"],
    )
    der_type: DERType = Field(..., description="Device category.")
    rated_power_kw: float = Field(..., gt=0, description="Rated power in kW.")
    rated_energy_kwh: float | None = Field(
        default=None,
        gt=0,
        description="Rated energy capacity in kWh for storage-capable devices.",
    )
    protocol: str = Field(
        default="manual",
        min_length=1,
        max_length=64,
        description="Integration protocol label. This is descriptive at launch.",
    )
    location_lat: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Optional latitude.",
    )
    location_lon: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Optional longitude.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional free-form metadata for local deployments.",
    )


class DeviceRegistration(GridOSModel):
    """Request body for registering a device in the local registry."""

    device: DeviceInfo
    adapter_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional adapter configuration kept only as metadata at launch.",
    )


class DERTelemetry(GridOSModel):
    """Validated telemetry snapshot used throughout the supported API flow."""

    id: UUID = Field(default_factory=uuid4, description="Telemetry record identifier.")
    device_id: str = Field(..., min_length=1, max_length=128, description="Reporting device identifier.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Measurement timestamp.",
    )
    power_kw: float = Field(
        ...,
        description="Active power in kW. Positive values typically indicate generation.",
    )
    reactive_power_kvar: float = Field(
        default=0.0,
        description="Reactive power in kVAR.",
    )
    voltage_v: float | None = Field(default=None, ge=0, description="Voltage in volts.")
    current_a: float | None = Field(default=None, ge=0, description="Current in amperes.")
    frequency_hz: float | None = Field(default=None, ge=0, description="Frequency in hertz.")
    power_factor: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Power factor.",
    )
    energy_kwh: float | None = Field(default=None, ge=0, description="Cumulative energy in kWh.")
    soc_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="State of charge in percent when applicable.",
    )
    temperature_c: float | None = Field(default=None, description="Temperature in Celsius.")
    irradiance_w_m2: float | None = Field(
        default=None,
        ge=0,
        description="Solar irradiance in W/m² when applicable.",
    )
    status: DERStatus = Field(default=DERStatus.ONLINE, description="Operational status.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional telemetry metadata.")

    @model_validator(mode="after")
    def validate_ranges(self) -> "DERTelemetry":
        """Reject obviously unrealistic measurements that usually indicate bad input."""
        if abs(self.power_kw) > 1_000_000:
            raise ValueError("power_kw exceeds 1 GW and is likely invalid")
        return self


class TelemetryBatch(GridOSModel):
    """Batch telemetry payload for bulk ingestion."""

    readings: list[DERTelemetry] = Field(..., min_length=1, description="Telemetry readings to ingest.")


class GridState(GridOSModel):
    """Minimal aggregate grid snapshot for compatibility with existing imports.

    This model is intentionally modest. It represents a lightweight summary that
    a local deployment may compute externally; it does not imply forecasting,
    optimization, or digital-twin functionality.
    """

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Snapshot timestamp.",
    )
    device_count: int = Field(default=0, ge=0, description="Number of known devices.")
    online_device_count: int = Field(default=0, ge=0, description="Devices currently marked online.")
    total_power_kw: float = Field(default=0.0, description="Summed active power in kW.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional summary metadata.")


class ControlCommand(GridOSModel):
    """Basic control command accepted by the reduced launch control route."""

    command_id: UUID = Field(default_factory=uuid4, description="Command identifier.")
    device_id: str = Field(
        default="",
        max_length=128,
        description="Target device identifier. The route path may override this value.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Command creation time.",
    )
    mode: ControlMode = Field(..., description="Requested control action.")
    setpoint_kw: float | None = Field(
        default=None,
        description="Requested power setpoint for power_setpoint mode.",
    )
    soc_target_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Requested state-of-charge target for soc_target mode.",
    )
    duration_seconds: int | None = Field(
        default=None,
        gt=0,
        description="Optional requested duration in seconds.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional command metadata.")

    @model_validator(mode="after")
    def validate_mode_specific_fields(self) -> "ControlCommand":
        """Ensure the small launch command surface remains self-consistent."""
        if self.mode == ControlMode.POWER_SETPOINT and self.setpoint_kw is None:
            raise ValueError("setpoint_kw is required for power_setpoint commands")
        if self.mode == ControlMode.SOC_TARGET and self.soc_target_percent is None:
            raise ValueError("soc_target_percent is required for soc_target commands")
        return self


class DeviceRegistrationResponse(GridOSModel):
    """Structured response payload for successful device registration."""

    status: str = Field(default="registered")
    device_id: str
    device: dict[str, Any]


class TelemetryIngestResponse(GridOSModel):
    """Structured response payload for successful telemetry ingestion."""

    status: str = Field(default="ingested")
    device_id: str


class ControlCommandResponse(GridOSModel):
    """Structured response payload for control command acceptance or dispatch."""

    status: str
    device_id: str
    command_id: str
    mode: str
    message: str | None = None
    setpoint_kw: float | None = None
    soc_target_percent: float | None = None

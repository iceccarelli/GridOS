"""
Common data models for GridOS.

Defines the core Pydantic models used throughout the platform for telemetry
ingestion, device registration, control commands, and grid-state
representation.  All models use strict validation, descriptive field metadata,
and JSON-serialisable types so they can be used directly in FastAPI endpoints.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

# ── Enumerations ─────────────────────────────────────────────────────────────


class DERType(str, Enum):
    """Distributed Energy Resource type taxonomy."""

    SOLAR_PV = "solar_pv"
    BATTERY = "battery"
    EV_CHARGER = "ev_charger"
    WIND_TURBINE = "wind_turbine"
    DIESEL_GENERATOR = "diesel_generator"
    FUEL_CELL = "fuel_cell"
    LOAD = "load"
    SMART_INVERTER = "smart_inverter"
    OTHER = "other"


class DERStatus(str, Enum):
    """Operational status of a DER."""

    ONLINE = "online"
    OFFLINE = "offline"
    FAULT = "fault"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class ControlMode(str, Enum):
    """Control mode for dispatching commands."""

    POWER_SETPOINT = "power_setpoint"
    SOC_TARGET = "soc_target"
    CURTAILMENT = "curtailment"
    DEMAND_RESPONSE = "demand_response"
    VOLTAGE_REGULATION = "voltage_regulation"
    FREQUENCY_RESPONSE = "frequency_response"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


# ── Core Models ──────────────────────────────────────────────────────────────


class DeviceInfo(BaseModel):
    """Static metadata describing a registered DER."""

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique identifier for the device.",
        examples=["inv-solar-001"],
    )
    name: str = Field(
        ...,
        max_length=256,
        description="Human-readable device name.",
        examples=["Rooftop PV Inverter #1"],
    )
    der_type: DERType = Field(
        ...,
        description="Type of distributed energy resource.",
    )
    rated_power_kw: float = Field(
        ...,
        gt=0,
        description="Nameplate rated power in kilowatts.",
    )
    rated_energy_kwh: float | None = Field(
        default=None,
        gt=0,
        description="Rated energy capacity in kWh (applicable to storage).",
    )
    location_lat: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Latitude of the device location.",
    )
    location_lon: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Longitude of the device location.",
    )
    protocol: str = Field(
        default="modbus",
        description="Communication protocol (modbus, mqtt, dnp3, iec61850, opcua).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value metadata.",
    )


class DeviceRegistration(BaseModel):
    """Request body for registering a new device."""

    device: DeviceInfo
    adapter_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Protocol-specific adapter configuration.",
    )


class DERTelemetry(BaseModel):
    """Real-time telemetry reading from a DER.

    Represents a single measurement snapshot including electrical quantities,
    environmental conditions, and device status.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique telemetry record identifier.",
    )
    device_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the reporting device.",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the measurement.",
    )
    # Electrical measurements
    power_kw: float = Field(
        ...,
        description="Active power in kW (positive = generation, negative = consumption).",
    )
    reactive_power_kvar: float = Field(
        default=0.0,
        description="Reactive power in kVAR.",
    )
    voltage_v: float | None = Field(
        default=None,
        ge=0,
        description="RMS voltage in volts.",
    )
    current_a: float | None = Field(
        default=None,
        ge=0,
        description="RMS current in amperes.",
    )
    frequency_hz: float | None = Field(
        default=None,
        ge=0,
        description="Grid frequency in Hz.",
    )
    power_factor: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Power factor (cos φ).",
    )
    energy_kwh: float | None = Field(
        default=None,
        ge=0,
        description="Cumulative energy in kWh.",
    )
    # Storage-specific
    soc_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="State of charge in percent (batteries / EVs).",
    )
    # Environmental
    temperature_c: float | None = Field(
        default=None,
        description="Ambient or device temperature in Celsius.",
    )
    irradiance_w_m2: float | None = Field(
        default=None,
        ge=0,
        description="Solar irradiance in W/m² (PV systems).",
    )
    # Status
    status: DERStatus = Field(
        default=DERStatus.ONLINE,
        description="Current operational status.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional key-value telemetry metadata.",
    )

    @field_validator("power_kw")
    @classmethod
    def validate_power(cls, v: float) -> float:
        """Ensure power value is within a reasonable range."""
        if abs(v) > 1_000_000:
            raise ValueError("power_kw exceeds 1 GW — likely a sensor error")
        return v


class TelemetryBatch(BaseModel):
    """A batch of telemetry readings for bulk ingestion."""

    readings: list[DERTelemetry] = Field(
        ...,
        min_length=1,
        description="List of telemetry readings.",
    )


class ControlCommand(BaseModel):
    """Command issued to a DER for dispatch or control actions.

    Commands are validated, logged, and forwarded to the appropriate protocol
    adapter for execution on the physical device.
    """

    command_id: UUID = Field(
        default_factory=uuid4,
        description="Unique command identifier for traceability.",
    )
    device_id: str = Field(
        ...,
        min_length=1,
        description="Target device identifier.",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the command was issued.",
    )
    mode: ControlMode = Field(
        ...,
        description="Control mode / action type.",
    )
    setpoint_kw: float | None = Field(
        default=None,
        description="Power setpoint in kW (for power_setpoint mode).",
    )
    soc_target_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Target state of charge in percent (for soc_target mode).",
    )
    duration_seconds: int | None = Field(
        default=None,
        gt=0,
        description="Duration for which the command is active.",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Command priority (1 = lowest, 10 = highest).",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional mode-specific parameters.",
    )
    source: str = Field(
        default="api",
        description="Origin of the command (api, scheduler, operator).",
    )


class GridState(BaseModel):
    """Aggregated snapshot of the grid at a point in time.

    Used by the digital-twin engine and optimiser to represent the current
    operating conditions of the microgrid or distribution network.
    """

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the snapshot.",
    )
    total_generation_kw: float = Field(
        default=0.0,
        description="Total active generation across all DERs.",
    )
    total_load_kw: float = Field(
        default=0.0,
        description="Total active load.",
    )
    total_storage_kw: float = Field(
        default=0.0,
        description="Net storage power (positive = discharging).",
    )
    net_power_kw: float = Field(
        default=0.0,
        description="Net power exchange with the main grid.",
    )
    average_voltage_pu: float = Field(
        default=1.0,
        ge=0.0,
        description="Average bus voltage in per-unit.",
    )
    frequency_hz: float = Field(
        default=50.0,
        description="System frequency in Hz.",
    )
    device_telemetry: dict[str, DERTelemetry] = Field(
        default_factory=dict,
        description="Per-device telemetry keyed by device_id.",
    )

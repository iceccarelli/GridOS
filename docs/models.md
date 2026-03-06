# GridOS Data Models

GridOS uses Pydantic v2 models to define a **Common Information Model (CIM)** for Distributed Energy Resources. All data exchanged through the API and between internal components uses these strongly-typed models.

## Core Enumerations

| Enum | Values | Description |
|------|--------|-------------|
| `DERType` | solar, wind, battery, ev_charger, generator, load, microgrid, other | Type of DER device |
| `DERStatus` | online, offline, fault, maintenance, curtailed | Device operational status |
| `ControlMode` | power_setpoint, voltage_regulation, frequency_response, schedule, emergency_stop, idle | Control command mode |

## DERTelemetry

The primary telemetry model for real-time device readings.

| Field | Type | Unit | Default | Description |
|-------|------|------|---------|-------------|
| `device_id` | str | — | required | Unique device identifier |
| `timestamp` | datetime | UTC | now | Reading timestamp |
| `power_kw` | float | kW | required | Active power output |
| `reactive_power_kvar` | float | kVAR | 0.0 | Reactive power |
| `voltage_v` | float | V | 230.0 | Terminal voltage |
| `current_a` | float | A | 0.0 | Current |
| `frequency_hz` | float | Hz | 50.0 | Grid frequency |
| `status` | DERStatus | — | online | Device status |
| `soc` | float | % | None | State of charge (batteries) |
| `temperature_c` | float | C | None | Device temperature |
| `metadata` | dict | — | {} | Additional key-value pairs |

## DeviceInfo

Static device registration information.

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | str | Unique identifier |
| `name` | str | Human-readable name |
| `device_type` | DERType | Type of device |
| `rated_power_kw` | float | Nameplate capacity |
| `location` | dict | Geographic coordinates |
| `firmware_version` | str | Firmware version |
| `manufacturer` | str | Manufacturer name |
| `model` | str | Model identifier |
| `commissioned_at` | datetime | Commissioning date |

## ControlCommand

Command model for device control operations.

| Field | Type | Description |
|-------|------|-------------|
| `command_id` | str | Auto-generated UUID |
| `device_id` | str | Target device |
| `mode` | ControlMode | Control mode |
| `setpoint_kw` | float | Power setpoint |
| `duration_seconds` | int | Command duration |
| `priority` | int | Priority (1=highest) |
| `source` | str | Command source |
| `issued_at` | datetime | Issue timestamp |

## IEC 61850 Models

GridOS includes IEC 61850 logical node models for standards-compliant data exchange. See `src/gridos/models/iec61850.py` for MMXU (measurement), CSWI (switch control), and DRCC (DER controller) models.

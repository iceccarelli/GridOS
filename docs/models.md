# GridOS Data Models

GridOS uses Pydantic models to describe the core data structures exchanged through the API and across internal components. For the current lightweight release, the most important thing to understand is not standards breadth but the **small set of models that support the main end-to-end workflow**.

## Model Philosophy

The current model layer is intended to do three things well:

| Goal | Meaning |
|---|---|
| Validation | Incoming data should be checked before it is used |
| Consistency | Internal components should work from predictable structures |
| Extensibility | The model set can grow later without making the initial release confusing |

## Core Models

### `DERTelemetry`

This is the primary model for telemetry ingestion and observation data.

| Field | Meaning |
|---|---|
| `device_id` | Unique identifier for the source device |
| `timestamp` | Time of the reading |
| `power_kw` | Active power value |
| `reactive_power_kvar` | Reactive power value |
| `voltage_v` | Voltage reading |
| `current_a` | Current reading |
| `frequency_hz` | Frequency reading |
| `status` | Operational status |
| `soc` | Optional state-of-charge field |
| `temperature_c` | Optional temperature field |
| `metadata` | Optional structured extra values |

### `DeviceInfo`

This model represents static or semi-static information about a device.

| Field | Meaning |
|---|---|
| `device_id` | Unique identifier |
| `name` | Human-readable name |
| `device_type` | Device classification |
| `rated_power_kw` | Nominal power rating |
| `location` | Optional location metadata |

### `ControlCommand`

If the current launch path includes command handling, this model represents a requested action sent to a device or simulated asset.

| Field | Meaning |
|---|---|
| `command_id` | Unique command identifier |
| `device_id` | Target device |
| `mode` | Requested control mode |
| `setpoint_kw` | Requested power setpoint |
| `duration_seconds` | Requested duration |
| `priority` | Relative execution priority |
| `source` | Origin of the command |
| `issued_at` | Command timestamp |

## Scope Note

The repository may contain additional standards-inspired or protocol-specific models, but the current launch documentation should stay centered on the models that support the reduced end-to-end workflow. Advanced standards-specific sections can be restored later once the public product scope expands again.

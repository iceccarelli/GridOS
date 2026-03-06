# GridOS API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

GridOS supports two authentication methods:

### API Key

Include the API key in the `X-API-Key` header:

```http
X-API-Key: gos_your_api_key_here
```

### JWT Bearer Token

Include the JWT token in the `Authorization` header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## Endpoints

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root endpoint with API info |
| GET | `/health` | Service health check |
| GET | `/docs` | Interactive Swagger UI |
| GET | `/redoc` | ReDoc documentation |

### Devices

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/devices/` | List all registered devices |
| GET | `/api/v1/devices/{device_id}` | Get device details |
| POST | `/api/v1/devices/register` | Register a new device |
| DELETE | `/api/v1/devices/{device_id}` | Unregister a device |

#### Register Device

```json
POST /api/v1/devices/register
{
  "device": {
    "device_id": "solar-001",
    "name": "Rooftop PV System",
    "device_type": "solar",
    "rated_power_kw": 10.0,
    "location": {"lat": 52.52, "lon": 13.405}
  },
  "adapter_config": {
    "protocol": "modbus",
    "host": "192.168.1.100",
    "port": 502
  }
}
```

### Telemetry

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/telemetry/` | Ingest a single reading |
| POST | `/api/v1/telemetry/batch` | Ingest a batch of readings |
| GET | `/api/v1/telemetry/{device_id}` | Query historical data |
| GET | `/api/v1/telemetry/{device_id}/latest` | Get latest reading |

#### Ingest Telemetry

```json
POST /api/v1/telemetry/
{
  "device_id": "solar-001",
  "timestamp": "2025-01-15T10:30:00Z",
  "power_kw": 8.5,
  "reactive_power_kvar": 1.2,
  "voltage_v": 235.0,
  "current_a": 12.3,
  "frequency_hz": 50.01,
  "status": "online"
}
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start` | datetime | 24h ago | Start time (ISO 8601) |
| `end` | datetime | now | End time (ISO 8601) |
| `limit` | int | 1000 | Max records (1–50,000) |

### Control

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/control/{device_id}` | Send control command |

#### Send Command

```json
POST /api/v1/control/batt-001
{
  "device_id": "batt-001",
  "mode": "power_setpoint",
  "setpoint_kw": 25.0,
  "duration_seconds": 900,
  "source": "manual"
}
```

### Forecast

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/forecast/{device_id}` | Generate forecast |

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `horizon` | int | 96 | Steps to forecast (1–672) |

### Optimisation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/optimization/run` | Run the scheduler |
| GET | `/api/v1/optimization/schedule` | Get latest schedule |

#### Run Optimisation

```json
POST /api/v1/optimization/run
{
  "load_forecast_kw": [60, 58, 55, ...],
  "solar_forecast_kw": [0, 0, 5, ...],
  "battery_capacity_kwh": 200,
  "battery_max_charge_kw": 100,
  "battery_max_discharge_kw": 100,
  "battery_efficiency": 0.92,
  "battery_soc_initial": 0.5,
  "import_prices": [0.25, 0.25, 0.15, ...],
  "export_prices": [0.05, 0.05, 0.05, ...]
}
```

### WebSocket

Connect to `ws://localhost:8000/ws/telemetry` for live telemetry streaming.

#### Subscribe to specific devices

```
ws://localhost:8000/ws/telemetry?device_ids=solar-001,batt-001
```

#### Message format

```json
{
  "device_id": "solar-001",
  "timestamp": "2025-01-15T10:30:00Z",
  "power_kw": 8.5,
  "voltage_v": 235.0,
  "status": "online"
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Device solar-001 not found"
}
```

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request — invalid input |
| 401 | Unauthorised — missing credentials |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource does not exist |
| 409 | Conflict — resource already exists |
| 500 | Internal Server Error |

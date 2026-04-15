# GridOS Quick Start

This guide shows the fastest honest path to a working **GridOS** setup.

The current launch-ready version is intentionally small. The supported first-run path is a **FastAPI service** with **device registration**, **telemetry ingestion and lookup**, **basic control command acceptance**, and **in-memory storage by default**. Optional external storage backends can be added later, but they are not required for a successful first run.

## What This Quick Start Covers

| Step | Outcome |
|---|---|
| Install GridOS from source | Local environment is ready |
| Start the API | The supported backend is running |
| Open `/docs` | The live API surface is visible |
| Register one device | The device registry works |
| Send telemetry | The core ingest path works |
| Query latest telemetry | End-to-end data flow is confirmed |

## 1. Clone the Repository

```bash
git clone https://github.com/iceccarelli/GridOS.git
cd GridOS
```

## 2. Create and Activate a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## 3. Install the Project

```bash
pip install -e ".[dev]"
```

This installs the reduced launch runtime plus the development tools used by the repository.

## 4. Create a Local Configuration File

```bash
cp .env.example .env
```

Leave `GRIDOS_USE_INMEMORY_STORAGE=true` for the first run. That is the supported launch path.

## 5. Start the API

```bash
uvicorn gridos.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

```text
http://localhost:8000/docs
```

## 6. Check the Health Endpoint

```bash
curl http://localhost:8000/health
```

A successful response confirms that the local runtime is running.

## 7. Register a Device

```bash
curl -X POST http://localhost:8000/api/v1/devices/register   -H "Content-Type: application/json"   -d '{
    "device": {
      "device_id": "demo-device-1",
      "name": "Demo PV",
      "der_type": "solar_pv",
      "rated_power_kw": 12.5
    },
    "adapter_config": {}
  }'
```

## 8. Send a Telemetry Payload

```bash
curl -X POST http://localhost:8000/api/v1/telemetry/   -H "Content-Type: application/json"   -d '{
    "device_id": "demo-device-1",
    "timestamp": "2026-01-01T12:00:00Z",
    "power_kw": 12.5,
    "reactive_power_kvar": 1.8,
    "voltage_v": 230.0,
    "current_a": 10.4,
    "frequency_hz": 50.0,
    "status": "online"
  }'
```

## 9. Query the Latest Telemetry

```bash
curl http://localhost:8000/api/v1/telemetry/demo-device-1/latest
```

## Current Scope Boundaries

| Area | Current Status |
|---|---|
| Device registration | Supported |
| Telemetry ingest and query | Supported |
| Basic control command acceptance | Supported |
| In-memory storage | Supported by default |
| InfluxDB and TimescaleDB | Optional, not required for first run |
| Forecasting and optimization | Not part of the default launch path |
| Protocol adapter automation | Deferred |
| Digital twin workflows | Deferred |

The goal of this guide is not to promise the long-term vision. The goal is to get you to a **small, working, trustworthy** GridOS instance quickly.

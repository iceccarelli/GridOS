# GridOS Quick Start Guide

This guide will help you get GridOS running in under 5 minutes.

## Installation

### Option 1: pip install (recommended for development)

```bash
git clone https://github.com/your-org/GridOS.git
cd GridOS
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Option 2: Docker (recommended for deployment)

```bash
git clone https://github.com/your-org/GridOS.git
cd GridOS
docker-compose up --build -d
```

## Running the API

```bash
# Development mode with auto-reload
uvicorn gridos.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the Makefile
make run
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

## Running the Demo

The quick start demo showcases all major GridOS features:

```bash
make demo
# Or directly:
PYTHONPATH=src python notebooks/01_quickstart.py
```

## Register a Device

```bash
curl -X POST http://localhost:8000/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device": {
      "device_id": "solar-001",
      "name": "Rooftop PV",
      "device_type": "solar",
      "rated_power_kw": 10.0
    },
    "adapter_config": {
      "protocol": "mqtt",
      "broker": "mqtt://localhost:1883"
    }
  }'
```

## Ingest Telemetry

```bash
curl -X POST http://localhost:8000/api/v1/telemetry/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "solar-001",
    "power_kw": 8.5,
    "voltage_v": 235.0,
    "status": "online"
  }'
```

## Run Optimisation

```bash
curl -X POST http://localhost:8000/api/v1/optimization/run \
  -H "Content-Type: application/json" \
  -d '{
    "load_forecast_kw": [60, 58, 55, 52, 50, 48, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 30, 31, 33, 36, 40, 45, 50, 55, 60, 65, 68, 70, 72, 74, 75, 76, 77, 78, 79, 80, 80, 79, 78, 76, 74, 72, 70, 68, 66, 64, 62, 60, 58, 56, 55, 54, 53, 52, 51, 50, 50, 51, 53, 56, 60, 65, 70, 75, 78, 80, 82, 83, 84, 85, 84, 82, 80, 77, 74, 70, 66, 62, 58, 55, 52, 50, 48, 46, 45, 44, 43, 42, 41],
    "solar_forecast_kw": [0, 0, 0, 0, 0, 0, 0, 0, 2, 5, 10, 15, 20, 25, 30, 35, 38, 40, 42, 44, 45, 46, 47, 48, 48, 48, 47, 46, 45, 44, 42, 40, 38, 36, 34, 32, 30, 28, 25, 22, 18, 14, 10, 6, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 5, 10, 15, 20, 25, 30, 35, 38, 40, 42, 44, 45, 46, 47, 48, 48, 48, 47, 46, 45, 44, 42, 40, 38, 36, 34, 32, 30, 28, 25, 22, 18, 14, 10, 6, 3, 1],
    "battery_capacity_kwh": 200,
    "battery_max_charge_kw": 100,
    "battery_max_discharge_kw": 100
  }'
```

## Running Tests

```bash
make test
# Or directly:
pytest tests/ -v --cov=gridos
```

## Next Steps

Explore the full documentation in the `docs/` directory for architecture details, API reference, and deployment guides.

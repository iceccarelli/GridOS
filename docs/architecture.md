# GridOS Architecture

## Overview

GridOS is a **vendor-neutral, open-source middleware platform** for managing Distributed Energy Resources (DERs) through a unified, standards-based architecture. It bridges the gap between heterogeneous field devices and enterprise energy management systems.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GridOS Platform                          │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  REST API │  │WebSocket │  │  gRPC    │  │  Dashboard   │   │
│  │ (FastAPI) │  │ Manager  │  │ (future) │  │  (future)    │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │              │              │               │           │
│  ┌────┴──────────────┴──────────────┴───────────────┴──────┐   │
│  │                    Service Layer                         │   │
│  │  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌────────┐  │   │
│  │  │ Digital  │  │   ML     │  │Optimiser  │  │Security│  │   │
│  │  │  Twin    │  │ Engine   │  │(MILP)     │  │ (Auth) │  │   │
│  │  └────┬────┘  └────┬─────┘  └─────┬─────┘  └────────┘  │   │
│  └───────┼─────────────┼──────────────┼────────────────────┘   │
│          │             │              │                         │
│  ┌───────┴─────────────┴──────────────┴────────────────────┐   │
│  │                    Data Layer                            │   │
│  │  ┌──────────┐  ┌────────────┐  ┌───────────────────┐    │   │
│  │  │ InfluxDB │  │TimescaleDB │  │ Edge SQLite Cache │    │   │
│  │  └──────────┘  └────────────┘  └───────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Adapter Layer                           │   │
│  │  ┌────────┐ ┌──────┐ ┌──────┐ ┌─────────┐ ┌────────┐   │   │
│  │  │ Modbus │ │ MQTT │ │ DNP3 │ │IEC 61850│ │ OPC-UA │   │   │
│  │  └────┬───┘ └──┬───┘ └──┬───┘ └────┬────┘ └───┬────┘   │   │
│  └───────┼────────┼────────┼──────────┼──────────┼─────────┘   │
└──────────┼────────┼────────┼──────────┼──────────┼─────────────┘
           │        │        │          │          │
    ┌──────┴──┐ ┌───┴──┐ ┌──┴───┐ ┌────┴───┐ ┌───┴────┐
    │Inverters│ │ MQTT  │ │ RTU  │ │  IEDs  │ │  PLCs  │
    │ Meters  │ │Sensors│ │      │ │        │ │        │
    └─────────┘ └──────┘ └──────┘ └────────┘ └────────┘
```

## Component Details

### Adapter Layer

The adapter layer provides protocol-specific communication with field devices. Each adapter inherits from `BaseAdapter` and implements:

- `connect()` / `disconnect()` — lifecycle management
- `read_telemetry()` — poll device for current readings
- `write_command()` — send control commands to devices

Supported protocols: **Modbus TCP**, **MQTT**, **DNP3**, **IEC 61850**, **OPC-UA**.

### Data Layer

GridOS supports pluggable storage backends for time-series data:

- **InfluxDB 2.x** — optimised for high-throughput telemetry ingestion
- **TimescaleDB** — PostgreSQL extension for SQL-based analytics
- **SQLite (Edge)** — local store-and-forward cache for edge deployments

### Digital Twin Engine

The digital twin provides physics-based models for grid components:

- **Bus** — electrical nodes with voltage tracking
- **Line** — distribution line segments with impedance and loss calculation
- **Transformer** — two-winding transformers with tap ratio
- **Load** — constant-power and profile-based loads
- **PV** — single-diode-equivalent solar model
- **Battery** — first-order equivalent circuit with SoC tracking
- **EV Charger** — Level 2 / DC fast charger with smart charging

The engine uses a simplified **backward/forward sweep** power-flow solver for radial distribution networks.

### Machine Learning

- **LSTM Forecaster** — PyTorch-based stacked LSTM for load and solar forecasting
- **Isolation Forest** — scikit-learn-based anomaly detection for telemetry

### Optimisation

The MILP scheduler uses PuLP to solve the optimal battery dispatch problem:

- Minimises electricity import cost
- Respects battery power and energy constraints
- Prevents simultaneous charge/discharge
- Supports time-of-use pricing

### API Layer

FastAPI-based REST API with:

- Device management (CRUD)
- Telemetry ingestion and querying
- Control command dispatch
- Forecast generation
- Optimisation scheduling
- WebSocket live telemetry streaming

### Security

- API key authentication
- JWT bearer token support
- Role-based access control (RBAC)

## Deployment Options

| Deployment | Description |
|-----------|-------------|
| **Development** | `uvicorn` with `--reload` |
| **Docker** | Multi-container with Docker Compose |
| **Kubernetes** | Helm chart with auto-scaling |
| **Edge** | Lightweight SQLite-based with cloud sync |

## Data Flow

1. **Ingestion**: Adapters poll devices or receive MQTT messages
2. **Storage**: Telemetry is written to InfluxDB/TimescaleDB
3. **Broadcast**: WebSocket manager pushes live data to subscribers
4. **Analysis**: ML models detect anomalies and generate forecasts
5. **Optimisation**: MILP scheduler computes optimal dispatch
6. **Control**: Dispatcher sends setpoints to devices via adapters

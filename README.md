```markdown
# GridOS — Open Energy Operating System
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/gridos.svg)](https://pypi.org/project/gridos/)
[![PyPI downloads](https://img.shields.io/pypi/dm/gridos.svg)](https://pypi.org/project/gridos/)
[![Docker Image](https://img.shields.io/badge/docker-ghcr.io%2Ficeccarelli%2Fgridos-blue?logo=docker)](https://github.com/iceccarelli/GridOS/pkgs/container/gridos)
[![CI](https://github.com/iceccarelli/GridOS/actions/workflows/ci.yml/badge.svg)](https://github.com/iceccarelli/GridOS/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](https://fastapi.tiangolo.com/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**GridOS** aims to be a vendor-neutral, open-source middleware platform that unifies **Distributed Energy Resources (DERs)** — solar inverters, batteries, EV chargers, smart loads — behind a single, standards-based API. It provides real-time telemetry ingestion, digital-twin simulation, ML-driven forecasting, and optimal energy dispatch, enabling utilities, aggregators, and microgrid operators to accelerate the energy transition.

---

## Key Features
| Capability                  | Description |
|-----------------------------|-------------|
| **Multi-Protocol Adapters** | Modbus TCP/RTU, MQTT, DNP3, IEC 61850, OPC-UA — connect any DER out of the box. |
| **Common Information Model**| Pydantic models aligned with IEC 61968/61850 for interoperable data exchange. |
| **Time-Series Storage**     | Pluggable backends for InfluxDB 2.x and TimescaleDB with async I/O. |
| **Digital Twin Engine**     | Physics-based component models (bus, line, transformer, PV, battery, EV charger) with simplified power-flow simulation. |
| **ML Forecasting**          | LSTM-based load and solar forecasting plus Isolation Forest anomaly detection. |
| **MILP Optimization**       | Mixed-Integer Linear Programming scheduler for optimal battery dispatch and demand response. |
| **REST + WebSocket API**    | FastAPI-powered endpoints with live telemetry streaming via WebSockets. |
| **Edge Support**            | SQLite-based store-and-forward cache for intermittent connectivity. |
| **Cloud-Native Deployment** | Docker Compose, Kubernetes manifests, and GitHub Actions CI/CD included. |

---

## Architecture Overview

```mermaid
---
title: GridOS — Architecture Overview
---
flowchart TB
    %% Title (for visual impact in rendered Markdown)
    Title["<b>GridOS</b> — Open Energy Operating System<br/><span style='font-size:13px'>Vendor-neutral • Standards-based • Real-time DER Middleware</span><br/><i>Telemetry Ingestion • Digital Twin • ML Forecasting • MILP Optimization</i>"]

    %% Physical Layer (high-voltage engineering view)
    DERs["<b>🌍 Distributed Energy Resources (DERs)</b><br/>Solar Inverters • Battery Energy Storage Systems (BESS)<br/>EV Chargers • Smart Controllable Loads"]

    %% Layer 1: Communication (protocol adapters)
    subgraph L1 ["<b>1. Multi-Protocol Communication Layer</b><br/>🔌 Edge-ready adapters"]
        direction TB
        MOD["Modbus TCP/RTU"]
        MQTT["MQTT"]
        DNP["DNP3"]
        IEC["IEC 61850<br/>(MMS / GOOSE / SV)"]
        OPC["OPC-UA"]
    end

    %% Layer 2: Semantic normalization (CIM for interoperability)
    L2["<b>2. Semantic Normalization Layer</b><br/>📋 Common Information Model (CIM)<br/>Pydantic models • IEC 61968 + IEC 61850 compliant"]

    %% Layer 3: Core platform (the heart of the system)
    subgraph L3 ["<b>3. Core Intelligence Platform</b>"]
        direction TB

        subgraph Storage ["Time-Series Storage"]
            TS["InfluxDB 2.x • TimescaleDB<br/>+ SQLite Edge Store-and-Forward Cache"]
        end

        Twin["<b>Digital Twin Engine</b><br/>Physics-based component models<br/>Bus • Line • Transformer • PV • Battery • EV Charger<br/>Quasi-static Power-Flow Simulation"]

        subgraph Intelligence ["AI & Optimization Engine"]
            ML["Machine-Learning Forecasting<br/>LSTM (load & solar) + Isolation Forest anomaly detection"]
            Opt["<b>Mixed-Integer Linear Programming (MILP)</b><br/>Optimal battery dispatch & demand response (PuLP)"]
        end
    end

    %% Layer 4: API & real-time services
    L4["<b>4. API & Real-Time Services Layer</b><br/>🚀 FastAPI + WebSocket<br/>REST endpoints + Live Telemetry Streaming<br/>Security: API Keys + JWT authentication"]

    %% Users & applications (end-to-end value)
    subgraph Users ["<b>5. End Users & Applications</b>"]
        direction TB
        VPP["Virtual Power Plants & Aggregators"]
        Micro["Microgrid Controllers & Operators"]
        Util["Utilities & Distribution System Operators (DSOs)"]
        Dash["Grafana Dashboards + Custom Analytics UIs"]
    end

    %% Cross-cutting concerns (deployment, edge, security)
    Edge["Edge Computing Mode<br/>Store-and-Forward for intermittent connectivity"]
    Security["Security Layer<br/>API Keys + JWT"]
    Deploy["Cloud-Native Deployment<br/>Docker • Kubernetes • GitHub Actions CI/CD • PyPI Package"]

    %% Data & control flows (the professional integration path)
    DERs --> L1
    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 --> Users

    %% Bidirectional control loop (critical for power engineers)
    Users -.->|"Optimal Setpoints & Dispatch Commands"| L4

    %% Cross-cutting links
    L3 --> Edge
    L4 --> Security
    L4 --> Deploy

    %% Professional styling (clean academic/industrial look)
    classDef title fill:#1e40af,color:#fff,stroke:#1e40af,stroke-width:4px,font-size:18px
    classDef physical fill:#fef3c7,stroke:#d97706,stroke-width:3px,rx:15,ry:15
    classDef layer fill:#e0f2fe,stroke:#1e40af,stroke-width:3px,rx:18,ry:18
    classDef core fill:#f3e8ff,stroke:#6b21a8,stroke-width:3px,rx:15,ry:15
    classDef users fill:#ede9fe,stroke:#6d28d9,stroke-width:2px,rx:12,ry:12

    class Title title
    class DERs physical
    class L1,L2,L4 layer
    class L3,Storage,Twin,Intelligence,TS,ML,Opt core
    class Users users
```

---

## System Data Flow & Closed-Loop Control

```mermaid
flowchart LR
    A[Telemetry Ingestion<br/>Multi-Protocol Adapters] --> B[CIM Normalization<br/>Pydantic Models]
    B --> C[Digital Twin State Update<br/>Physics-based Power Flow]
    C --> D[Forecasting & Analytics<br/>LSTM + Isolation Forest]
    D --> E[Optimization Solver<br/>MILP (PuLP)]
    E --> F[Optimal Dispatch Commands<br/>Battery / DER Control]
    F -.-> A
    style E fill:#4f46e5,color:#fff,stroke:#c4b5fd,stroke-width:3px
```

---

## Project Overview Mindmap

```mermaid
mindmap
  root((GridOS))
    Key Features
      Multi-Protocol Adapters
      CIM (Pydantic + IEC)
      Time-Series Storage
      Digital Twin + Power Flow
      ML Forecasting & Anomaly
      MILP Optimization
      FastAPI + WebSocket
      Edge Store-and-Forward
    Installation & Deployment
      PyPI + Extras
      Docker / docker-compose
      Kubernetes
      Edge Mode
    Project Structure
      src/gridos/models
      src/gridos/adapters
      src/gridos/digital_twin
      src/gridos/optimization
      src/gridos/api
      notebooks/
      k8s/ + tests/
    Target Audience
      Utilities & DSOs
      Aggregators & VPPs
      Microgrid Operators
      Academic Research
```

---

## Installation
### Option 1: Install from PyPI (Recommended)
```bash
pip install gridos
```
With optional dependencies:
```bash
# Machine learning (LSTM forecasting, anomaly detection)
pip install gridos[ml]
# Protocol adapters (Modbus, MQTT, OPC-UA)
pip install gridos[adapters]
# Storage backends (InfluxDB, TimescaleDB)
pip install gridos[storage]
# Everything
pip install gridos[ml,adapters,storage]
```

### Option 2: Run with Docker
```bash
docker pull ghcr.io/iceccarelli/gridos:latest
docker run -p 8000:8000 ghcr.io/iceccarelli/gridos:latest
```
The API is now available at `http://localhost:8000/docs`.

### Option 3: Run with Docker Compose (Full Stack)
```bash
git clone https://github.com/iceccarelli/GridOS.git
cd GridOS
docker-compose up -d
```
This starts GridOS alongside InfluxDB, TimescaleDB, and Grafana.

### Option 4: Install from Source
```bash
git clone https://github.com/iceccarelli/GridOS.git
cd GridOS
python -m venv .venv
source .venv/bin/activate
# Install with dev dependencies
pip install -e ".[dev]"
```

---

## Quick Start
### Configuration
```bash
# Copy the example environment file
cp .env.example .env
# Edit .env with your settings (storage URLs, broker addresses, etc.)
```

### Run the API Server
```bash
uvicorn gridos.main:app --host 0.0.0.0 --port 8000 --reload
```
The interactive API documentation is available at `http://localhost:8000/docs`.

---

## Project Structure
```
GridOS/
├── src/gridos/          # Core Python package
│   ├── models/          # Pydantic CIM models
│   ├── adapters/        # Protocol adapters (Modbus, MQTT, DNP3, …)
│   ├── storage/         # Time-series backends (InfluxDB, TimescaleDB)
│   ├── digital_twin/    # Simulation engine + ML modules
│   ├── optimization/    # MILP scheduler and dispatch
│   ├── api/             # FastAPI routes and WebSocket manager
│   ├── edge/            # Edge caching (SQLite store-and-forward)
│   ├── security/        # API key + JWT authentication
│   └── utils/           # Logging, metrics, and shared utilities
├── tests/               # Pytest test suite (70 tests)
├── notebooks/           # Jupyter demo notebooks
├── data/                # Sample datasets
├── docs/                # Architecture, API reference, developer guide
├── k8s/                 # Kubernetes manifests
├── scripts/             # Utility and demo scripts
└── requirements/        # Dependency files (base, ml, dev, prod)
```

---

## Running Tests
```bash
pytest tests/ -v --cov=gridos --cov-report=term-missing
```

---

## Notebooks
Explore the interactive Jupyter notebooks in `notebooks/`:
1. **Data Ingestion Demo** — Connect adapters and ingest telemetry.
2. **Digital Twin Simulation** — Build a grid model and run power-flow.
3. **Forecasting with ML** — Train an LSTM on solar generation data.
4. **Optimization Scheduler** — Solve optimal battery dispatch with MILP.
5. **API Client** — Interact with the REST API programmatically.

---

## Contributing
We welcome contributions from the Grid Digitization community. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started.

---

## Security
If you discover a security vulnerability, please follow the responsible disclosure process described in [SECURITY.md](SECURITY.md).

---

## License
GridOS is released under the [MIT License](LICENSE).

---

## Acknowledgements
GridOS builds on the shoulders of outstanding open-source projects including FastAPI, Pydantic, PuLP, scikit-learn, InfluxDB, TimescaleDB, and many others. We are grateful to the energy systems research community for the standards and models that inform this work.
```

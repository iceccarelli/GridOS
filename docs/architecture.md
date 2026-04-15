# GridOS Deployment Guide

This document describes the **supported deployment story for the reduced GridOS release**.

The recommended path is deliberately simple: run the API as a single Python service with **in-memory storage enabled by default**. Optional Docker support is provided for convenience, but the primary objective is a deployment path that is easy to reproduce and honest about what the repository supports today.

## Supported Deployment Modes

| Deployment mode | Status |
|---|---|
| Local development with `uvicorn` | Recommended |
| Single-container Docker deployment | Supported |
| Docker Compose with one API service | Supported |
| External time-series database integration | Optional |
| Kubernetes and large-scale orchestration | Not part of the current launch path |

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | Required |
| Virtual environment | Strongly recommended |
| Docker | Optional |

## Default Local Deployment

### 1. Clone and enter the repository

```bash
git clone https://github.com/iceccarelli/GridOS.git
cd GridOS
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install the project

```bash
pip install -e ".[dev]"
```

### 4. Create the environment file

```bash
cp .env.example .env
```

Keep `GRIDOS_USE_INMEMORY_STORAGE=true` unless you are intentionally testing an external backend.

### 5. Run the API

```bash
uvicorn gridos.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Verify the deployment

```bash
curl http://localhost:8000/health
```

Then open:

```text
http://localhost:8000/docs
```

## Docker Deployment

Build and run a single API container:

```bash
docker build -t gridos:local .
docker run --rm -p 8000:8000 --env-file .env gridos:local
```

Or use Docker Compose:

```bash
docker compose up --build
```

The compose file intentionally starts only the API service. It does not claim a full multi-service production stack.

## Configuration Philosophy

| Configuration area | Current recommendation |
|---|---|
| Storage | Start with in-memory mode |
| Auth | Keep it explicit and minimal |
| External databases | Add only when you need them |
| Protocol integrations | Treat them as optional and incomplete |
| Production hardening | Add after the local launch path is stable |

## Optional External Storage

GridOS can be pointed at **InfluxDB** or **TimescaleDB**, but those integrations are secondary. They should be treated as extensions to a working local deployment, not as part of the required first-run path.

To enable an external backend, first set:

```bash
GRIDOS_USE_INMEMORY_STORAGE=false
```

Then provide the matching backend configuration in `.env`.

## What This Guide Does Not Promise

This guide does not claim that the current repository provides a fully validated adapter ecosystem, digital twin engine, production observability platform, or orchestration stack. The present goal is a **small, reproducible deployment path that works end-to-end**.

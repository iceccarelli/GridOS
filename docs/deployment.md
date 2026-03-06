# GridOS Deployment Guide

## Prerequisites

- Python 3.10 or later
- Docker and Docker Compose (for containerised deployment)
- Kubernetes cluster (for production deployment)

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/GridOS.git
cd GridOS
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
# Or using requirements files:
pip install -r requirements/base.txt -r requirements/dev.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Run the API Server

```bash
uvicorn gridos.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Run Tests

```bash
pytest tests/ -v --cov=gridos
```

## Docker Deployment

### Build and Run

```bash
docker-compose up --build -d
```

This starts:
- **GridOS API** on port 8000
- **InfluxDB** on port 8086
- **TimescaleDB** on port 5432

### View Logs

```bash
docker-compose logs -f gridos-api
```

### Stop Services

```bash
docker-compose down
```

## Kubernetes Deployment

### 1. Build Docker Image

```bash
docker build -t gridos:latest .
```

### 2. Apply Kubernetes Manifests

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

### 3. Verify Deployment

```bash
kubectl get pods -n gridos
kubectl get svc -n gridos
```

## Edge Deployment

For resource-constrained edge devices:

### 1. Install Minimal Dependencies

```bash
pip install -r requirements/base.txt
```

### 2. Configure Edge Mode

```bash
export GRIDOS_ENV=production
export GRIDOS_STORAGE_BACKEND=timescaledb
export GRIDOS_EDGE_MODE=true
```

### 3. Run with Edge Sync

The edge deployment uses SQLite for local caching and periodically syncs to the cloud API:

```python
from gridos.edge.local_cache import LocalCache
from gridos.edge.sync import EdgeSyncer

cache = LocalCache(db_path="./edge_cache.db")
syncer = EdgeSyncer(
    cache=cache,
    api_base_url="https://gridos-cloud.example.com",
    sync_interval_seconds=60,
)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRIDOS_ENV` | `development` | Environment (development/staging/production) |
| `GRIDOS_LOG_LEVEL` | `INFO` | Logging level |
| `GRIDOS_STORAGE_BACKEND` | `influxdb` | Storage backend (influxdb/timescaledb) |
| `INFLUXDB_URL` | `http://localhost:8086` | InfluxDB connection URL |
| `INFLUXDB_TOKEN` | — | InfluxDB authentication token |
| `INFLUXDB_ORG` | `gridos` | InfluxDB organisation |
| `INFLUXDB_BUCKET` | `telemetry` | InfluxDB bucket name |
| `TIMESCALEDB_DSN` | `postgresql://...` | TimescaleDB connection string |
| `GRIDOS_CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `GRIDOS_ML_MODEL_DIR` | `./models_cache` | ML model storage directory |

## Health Checks

The API exposes a health endpoint at `/health`:

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "websocket_connections": 0
}
```

## Monitoring

GridOS supports Prometheus metrics when `prometheus_client` is installed:

```bash
pip install prometheus_client
```

Metrics are exposed at `/metrics` and include:
- `gridos_telemetry_ingested_total`
- `gridos_commands_dispatched_total`
- `gridos_active_devices`
- `gridos_websocket_connections`
- `gridos_storage_write_seconds`
- `gridos_optimization_runs_total`

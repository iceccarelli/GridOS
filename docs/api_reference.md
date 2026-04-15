# GridOS API Reference

The primary API reference for GridOS is the **live FastAPI documentation** exposed by the running application.

Once the server is started, open:

```text
http://localhost:8000/docs
```

This page should be treated as the most accurate source of truth because it reflects the currently installed code and request schemas.

## Base URL

```text
http://localhost:8000
```

## Current API Philosophy

The reduced launch version of GridOS is centered on a **small, dependable API surface**. The current public promise should focus on the endpoints that are part of the end-to-end working path.

| API Area | Current Position |
|---|---|
| Root and health endpoints | Core |
| Telemetry ingestion | Core |
| Basic query flows | Core |
| Forecast and scheduling endpoints | Supported only if validated in the running build |
| Advanced control workflows | Secondary |
| WebSocket workflows | Not part of the core promise |

## Core Endpoints

### System Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Basic service information |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API documentation |
| `GET` | `/redoc` | Alternative API documentation |

### Telemetry

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/telemetry/` | Ingest a telemetry reading |

A representative example request is shown below.

```json
{
  "device_id": "demo-device-1",
  "timestamp": "2026-01-01T12:00:00Z",
  "power_kw": 12.5,
  "reactive_power_kvar": 1.8,
  "voltage_v": 230.0,
  "current_a": 10.4,
  "frequency_hz": 50.0,
  "status": "online"
}
```

## Authentication Note

Authentication behavior should be documented conservatively and kept aligned with the current verified runtime. If multiple authentication paths exist in the codebase, only the path that is actively validated in the launch workflow should be described as supported in external-facing docs.

## Error Format

GridOS uses standard FastAPI-style error responses.

```json
{
  "detail": "A human-readable error message"
}
```

## Recommendation

For the lightweight release, keep this document intentionally short and rely on `/docs` as the authoritative interactive reference. That reduces documentation drift and prevents the README and docs from promising endpoints that are not yet stable enough to headline.

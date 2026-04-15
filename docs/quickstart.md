# GridOS Quick Start

This guide is the **fastest reliable path** to running GridOS locally.

GridOS is currently focused on a **small, local-first workflow**: start the API, open the docs, send telemetry, and use the platform as a foundation for digital-twin and scheduling experiments. The goal of this quick start is not to show every planned feature. The goal is to get you to a working system quickly and honestly.

## What This Quick Start Covers

| Step | Outcome |
|---|---|
| Install GridOS from source | Local development setup is ready |
| Start the API | Core backend runs |
| Open `/docs` | API is discoverable |
| Send one telemetry payload | Main data path is working |
| Verify health | Runtime is alive |

## 1. Clone the Repository

```bash
git clone https://github.com/iceccarelli/GridOS.git
cd GridOS
```

## 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## 3. Install the Project

```bash
pip install -e ".[dev]"
```

If you are working on a minimal local setup, start with the default installation first and only add optional integrations after the base runtime is working.

## 4. Create a Local Configuration File

```bash
cp .env.example .env
```

Use the default local settings first. Do not add external database or protocol configuration unless you actually need it.

## 5. Start the API

```bash
uvicorn gridos.main:app --host 0.0.0.0 --port 8000 --reload
```

Once the server starts, open:

```text
http://localhost:8000/docs
```

## 6. Check the Health Endpoint

```bash
curl http://localhost:8000/health
```

A successful response confirms that the local runtime is alive.

## 7. Send a Telemetry Payload

Use the interactive API docs at `/docs`, or send a request directly.

```bash
curl -X POST http://localhost:8000/api/v1/telemetry/ \
  -H "Content-Type: application/json" \
  -d '{
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

The exact payload should always follow the schema shown in the running API documentation.

## 8. Next Steps

Once the core path is working, the most useful next steps are:

| Next Step | Why it matters |
|---|---|
| Explore `/docs` | Understand the currently supported API surface |
| Review `docs/architecture.md` | Understand the reduced-scope system design |
| Review `docs/models.md` | Understand the main data structures |
| Run selected demos or notebooks | Explore the digital-twin and scheduling direction |

## What This Guide Deliberately Does Not Promise Yet

This quick start does not assume that advanced protocol adapters, external databases, WebSocket workflows, or larger deployment modes are part of the default first-run path. Those areas may still exist in the repository, but the current launch path is intentionally smaller so the base system is easier to trust and easier to run.

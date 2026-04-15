# GridOS Deployment Guide

This guide describes the **supported deployment path for the current lightweight version of GridOS**.

At this stage, the recommended deployment model is a **local-first or single-service development deployment**. The priority is to keep the platform understandable, reproducible, and easy to run without requiring a large infrastructure setup.

## Supported Deployment Approach

| Deployment Mode | Status |
|---|---|
| Local development with `uvicorn` | **Recommended** |
| Single-container Docker workflow | **Optional, only if validated in your environment** |
| Multi-service Docker Compose stack | **Secondary / evolving** |
| Kubernetes | **Not part of the current core launch path** |

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | Required |
| Virtual environment | Strongly recommended |
| Docker | Optional |

## Local Development Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/iceccarelli/GridOS.git
cd GridOS
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 4. Create the Environment File

```bash
cp .env.example .env
```

Keep the configuration as local and minimal as possible for your first run.

### 5. Run the API

```bash
uvicorn gridos.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Verify the Deployment

```bash
curl http://localhost:8000/health
```

Then open:

```text
http://localhost:8000/docs
```

## Configuration Philosophy

The current recommended configuration is **local-first**. External services should only be introduced when the core application path is already working.

| Configuration Area | Current Recommendation |
|---|---|
| Storage | Prefer the default local-compatible path first |
| Auth | Keep configuration explicit and simple |
| External databases | Add only when needed |
| Protocol integrations | Treat as optional or experimental |
| Production hardening | Add after the local path is stable |

## Environment Variables

The exact variables may evolve, but the goal of the `.env` file is to keep the initial deployment small and understandable. For the lightweight release, the most important principle is that the default local runtime should not depend on a large external stack.

## Docker Notes

Docker can still be useful, but it should be treated as a convenience layer rather than the primary supported path unless it has been revalidated.

If you use Docker, keep the first target simple:

| Docker Goal | Recommendation |
|---|---|
| Single service API container | Good near-term target |
| Full multi-service stack | Only promote after revalidation |
| External TSDB dependencies | Optional |

## Edge and Offline-Friendly Operation

GridOS is being shaped around local storage and cache-friendly workflows. That means edge-style usage should emphasize resilience and simple local behavior before more complex synchronization topologies are introduced.

## What This Guide Does Not Cover Yet

This guide does not present Kubernetes, full production autoscaling, or a mature observability stack as part of the current core launch path. Those areas may be revisited later, but they should not be treated as part of the main supported deployment story until the smaller base system is fully stable.

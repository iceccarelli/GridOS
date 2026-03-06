"""
Telemetry API routes.

Endpoints for ingesting and querying DER telemetry data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from gridos.api.dependencies import get_storage
from gridos.api.websocket_manager import ws_manager
from gridos.models.common import DERTelemetry, TelemetryBatch
from gridos.storage.base import StorageBackend

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post(
    "/",
    response_model=dict[str, str],
    status_code=201,
    summary="Ingest a single telemetry reading",
)
async def ingest_telemetry(
    telemetry: DERTelemetry,
    storage: StorageBackend = Depends(get_storage),  # noqa: B008
) -> dict[str, str]:
    """Ingest a single telemetry reading and broadcast via WebSocket."""
    try:
        await storage.write_point(telemetry)
    except Exception as exc:
        logger.error("Storage write error: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to write telemetry"
        ) from exc

    # Broadcast to WebSocket subscribers
    await ws_manager.send_to_device_subscribers(
        telemetry.device_id,
        telemetry.model_dump(mode="json"),
    )

    return {"status": "ingested", "device_id": telemetry.device_id}


@router.post(
    "/batch",
    response_model=dict[str, Any],
    status_code=201,
    summary="Ingest a batch of telemetry readings",
)
async def ingest_batch(
    batch: TelemetryBatch,
    storage: StorageBackend = Depends(get_storage),  # noqa: B008
) -> dict[str, Any]:
    """Ingest multiple telemetry readings in a single request."""
    try:
        await storage.write_points(batch.readings)
    except Exception as exc:
        logger.error("Storage batch write error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to write batch") from exc

    return {"status": "ingested", "count": len(batch.readings)}


@router.get(
    "/{device_id}",
    response_model=list[dict[str, Any]],
    summary="Query telemetry for a device",
)
async def query_telemetry(
    device_id: str,
    start: datetime | None = Query(default=None, description="Start time (ISO 8601)"),  # noqa: B008
    end: datetime | None = Query(default=None, description="End time (ISO 8601)"),  # noqa: B008
    limit: int = Query(default=1000, ge=1, le=50_000),
    storage: StorageBackend = Depends(get_storage),  # noqa: B008
) -> list[dict[str, Any]]:
    """Query historical telemetry for a specific device."""
    if end is None:
        end = datetime.utcnow()
    if start is None:
        start = end - timedelta(hours=24)

    try:
        readings = await storage.query_range(device_id, start, end, limit)
    except Exception as exc:
        logger.error("Storage query error: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to query telemetry"
        ) from exc

    return [r.model_dump(mode="json") for r in readings]


@router.get(
    "/{device_id}/latest",
    response_model=dict[str, Any] | None,
    summary="Get the latest telemetry for a device",
)
async def get_latest_telemetry(
    device_id: str,
    storage: StorageBackend = Depends(get_storage),  # noqa: B008
) -> dict[str, Any] | None:
    """Return the most recent telemetry reading for a device."""
    try:
        reading = await storage.get_latest(device_id)
    except Exception as exc:
        logger.error("Storage get_latest error: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to fetch latest telemetry"
        ) from exc

    if reading is None:
        raise HTTPException(status_code=404, detail="No telemetry found")

    return reading.model_dump(mode="json")

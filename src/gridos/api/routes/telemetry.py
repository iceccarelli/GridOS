"""
Telemetry API routes.

This reduced launch version focuses on the API paths that must work end to end:
single ingest, batch ingest, historical query, and latest-value lookup. The
route is intentionally small and aligned with the in-memory-first runtime path.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from gridos.api.dependencies import get_storage
from gridos.api.websocket_manager import ws_manager
from gridos.models.common import DERTelemetry, TelemetryBatch
from gridos.storage.base import StorageBackend

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


async def _broadcast_telemetry(telemetry: DERTelemetry) -> None:
    """Best-effort live broadcast for telemetry subscribers."""
    try:
        await ws_manager.publish_telemetry(telemetry)
    except Exception as exc:
        logger.warning("Telemetry broadcast failed for %s: %s", telemetry.device_id, exc)


async def _broadcast_batch(readings: list[DERTelemetry]) -> None:
    """Best-effort broadcast for batch telemetry writes."""
    for telemetry in readings:
        await _broadcast_telemetry(telemetry)


@router.post(
    "/",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single telemetry reading",
)
async def ingest_telemetry(
    telemetry: DERTelemetry,
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """Persist a single telemetry reading and notify subscribers."""
    try:
        await storage.write_point(telemetry)
    except Exception as exc:
        logger.exception("Failed to write telemetry for %s", telemetry.device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to write telemetry.",
        ) from exc

    await _broadcast_telemetry(telemetry)

    return {
        "status": "ingested",
        "device_id": telemetry.device_id,
        "timestamp": telemetry.timestamp.isoformat(),
    }


@router.post(
    "/batch",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of telemetry readings",
)
async def ingest_batch(
    batch: TelemetryBatch,
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """Persist multiple telemetry readings in one request."""
    try:
        await storage.write_points(batch.readings)
    except Exception as exc:
        logger.exception("Failed to write telemetry batch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to write telemetry batch.",
        ) from exc

    await _broadcast_batch(batch.readings)

    device_ids = sorted({reading.device_id for reading in batch.readings})
    return {
        "status": "ingested",
        "count": len(batch.readings),
        "device_ids": device_ids,
    }


@router.get(
    "/{device_id}",
    response_model=list[dict[str, Any]],
    summary="Query telemetry for a device",
)
async def query_telemetry(
    device_id: str,
    start: datetime | None = Query(default=None, description="Start time in ISO 8601 format."),
    end: datetime | None = Query(default=None, description="End time in ISO 8601 format."),
    limit: int = Query(default=1000, ge=1, le=50_000, description="Maximum number of rows to return."),
    storage: StorageBackend = Depends(get_storage),
) -> list[dict[str, Any]]:
    """Return telemetry history for a device within a time window."""
    window_end = end or datetime.now(timezone.utc)
    window_start = start or (window_end - timedelta(hours=24))

    if window_start > window_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The start time must be earlier than or equal to the end time.",
        )

    try:
        readings = await storage.query_range(device_id, window_start, window_end, limit)
    except Exception as exc:
        logger.exception("Failed to query telemetry for %s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query telemetry.",
        ) from exc

    return [reading.model_dump(mode="json") for reading in readings]


@router.get(
    "/{device_id}/latest",
    response_model=dict[str, Any],
    summary="Get the latest telemetry for a device",
)
async def get_latest_telemetry(
    device_id: str,
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """Return the most recent telemetry reading for a device."""
    try:
        reading = await storage.get_latest(device_id)
    except Exception as exc:
        logger.exception("Failed to fetch latest telemetry for %s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch latest telemetry.",
        ) from exc

    if reading is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry found for device '{device_id}'.",
        )

    return reading.model_dump(mode="json")

"""Device management API routes for the reduced GridOS launch path."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from gridos.api.dependencies import get_device_registry, register_device
from gridos.models.common import DeviceRegistration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get(
    "/",
    response_model=list[dict[str, Any]],
    summary="List registered devices",
)
async def list_devices() -> list[dict[str, Any]]:
    """Return all registered devices from the in-memory registry."""
    registry = get_device_registry()
    return [registry[device_id] for device_id in sorted(registry.keys())]


@router.get(
    "/{device_id}",
    response_model=dict[str, Any],
    summary="Get device details",
)
async def get_device(device_id: str) -> dict[str, Any]:
    """Return the stored metadata for one registered device."""
    registry = get_device_registry()
    device = registry.get(device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found.",
        )

    return device


@router.post(
    "/register",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Register a device",
)
async def register_new_device(registration: DeviceRegistration) -> dict[str, Any]:
    """Register one device for the supported local-first launch flow."""
    device = registration.device
    registry = get_device_registry()

    if device.device_id in registry:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device '{device.device_id}' is already registered.",
        )

    record = {
        **device.model_dump(mode="json"),
        "adapter_config": registration.adapter_config,
    }
    register_device(device.device_id, record)
    logger.info("Device registered: %s", device.device_id)

    return {
        "status": "registered",
        "device_id": device.device_id,
        "device": record,
    }


@router.delete(
    "/{device_id}",
    response_model=dict[str, str],
    summary="Remove a device",
)
async def unregister_device(device_id: str) -> dict[str, str]:
    """Remove a device from the local in-memory registry."""
    registry = get_device_registry()

    if device_id not in registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found.",
        )

    del registry[device_id]
    logger.info("Device removed: %s", device_id)
    return {"status": "unregistered", "device_id": device_id}

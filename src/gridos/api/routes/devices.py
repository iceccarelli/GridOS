"""
Device management API routes.

Endpoints for listing, registering, and querying DER devices.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from gridos.api.dependencies import get_device_registry, register_device
from gridos.models.common import DeviceRegistration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get(
    "/",
    response_model=list[dict[str, Any]],
    summary="List all registered devices",
)
async def list_devices() -> list[dict[str, Any]]:
    """Return a list of all registered DER devices."""
    registry = get_device_registry()
    return list(registry.values())


@router.get(
    "/{device_id}",
    response_model=dict[str, Any],
    summary="Get device details",
)
async def get_device(device_id: str) -> dict[str, Any]:
    """Return details for a specific device."""
    registry = get_device_registry()
    if device_id not in registry:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return registry[device_id]


@router.post(
    "/register",
    response_model=dict[str, str],
    status_code=201,
    summary="Register a new device",
)
async def register_new_device(registration: DeviceRegistration) -> dict[str, str]:
    """Register a new DER device in the platform."""
    device = registration.device
    registry = get_device_registry()

    if device.device_id in registry:
        raise HTTPException(
            status_code=409,
            detail=f"Device {device.device_id} is already registered",
        )

    register_device(
        device.device_id,
        {
            **device.model_dump(),
            "adapter_config": registration.adapter_config,
        },
    )
    logger.info("Device registered via API: %s", device.device_id)
    return {"status": "registered", "device_id": device.device_id}


@router.delete(
    "/{device_id}",
    response_model=dict[str, str],
    summary="Unregister a device",
)
async def unregister_device(device_id: str) -> dict[str, str]:
    """Remove a device from the registry."""
    registry = get_device_registry()
    if device_id not in registry:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    del registry[device_id]
    logger.info("Device unregistered via API: %s", device_id)
    return {"status": "unregistered", "device_id": device_id}

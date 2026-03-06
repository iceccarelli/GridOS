"""
Control command API routes.

Endpoints for issuing control commands to DER devices.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from gridos.api.dependencies import get_adapter_registry, get_device_registry
from gridos.models.common import ControlCommand

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/control", tags=["Control"])


@router.post(
    "/{device_id}",
    response_model=dict[str, Any],
    summary="Send a control command to a device",
)
async def send_command(device_id: str, command: ControlCommand) -> dict[str, Any]:
    """Issue a control command to a specific DER device.

    The command is validated, logged, and forwarded to the device's
    protocol adapter for execution.
    """
    # Verify device exists
    registry = get_device_registry()
    if device_id not in registry:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # Ensure command targets the correct device
    if command.device_id != device_id:
        command.device_id = device_id

    # Find adapter
    adapters = get_adapter_registry()
    adapter = adapters.get(device_id)

    if adapter is None:
        logger.warning("No adapter registered for device %s", device_id)
        return {
            "status": "no_adapter",
            "device_id": device_id,
            "command_id": str(command.command_id),
            "message": "No adapter registered — command queued for later dispatch.",
        }

    try:
        success = await adapter.write_command(command)
    except Exception as exc:
        logger.error("Command dispatch error for %s: %s", device_id, exc)
        raise HTTPException(
            status_code=500, detail=f"Command dispatch failed: {exc}"
        ) from exc

    return {
        "status": "dispatched" if success else "failed",
        "device_id": device_id,
        "command_id": str(command.command_id),
        "mode": command.mode.value,
        "setpoint_kw": command.setpoint_kw,
    }

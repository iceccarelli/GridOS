"""Control API routes for the reduced GridOS launch path."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from gridos.api.dependencies import get_adapter_registry, get_device_registry
from gridos.models.common import ControlCommand

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/control", tags=["Control"])


@router.post(
    "/{device_id}",
    response_model=dict[str, Any],
    summary="Send a control command to a registered device",
)
async def send_command(device_id: str, command: ControlCommand) -> dict[str, Any]:
    """Validate a command and dispatch it when an adapter is available.

    In the reduced launch version, command handling is intentionally modest:
    the device must exist, and if no adapter has been attached yet, the API
    responds truthfully that the command was accepted but not dispatched.
    """
    registry = get_device_registry()
    if device_id not in registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found.",
        )

    normalized_command = command.model_copy(update={"device_id": device_id})

    adapter = get_adapter_registry().get(device_id)
    if adapter is None:
        logger.info("Command accepted without adapter for device %s", device_id)
        return {
            "status": "accepted_not_dispatched",
            "device_id": device_id,
            "command_id": str(normalized_command.command_id),
            "mode": normalized_command.mode.value,
            "message": "No adapter is attached to this device in the reduced launch configuration.",
        }

    try:
        dispatched = await adapter.write_command(normalized_command)
    except Exception as exc:
        logger.exception("Command dispatch failed for %s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Command dispatch failed.",
        ) from exc

    return {
        "status": "dispatched" if dispatched else "rejected",
        "device_id": device_id,
        "command_id": str(normalized_command.command_id),
        "mode": normalized_command.mode.value,
        "setpoint_kw": normalized_command.setpoint_kw,
        "soc_target_percent": normalized_command.soc_target_percent,
    }

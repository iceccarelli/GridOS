"""Experimental forecast routes kept outside the default launch surface.

This module is intentionally not mounted by ``gridos.main`` in the reduced
launch version. It is retained only as an explicit placeholder for future work.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get("/status", response_model=dict[str, Any], summary="Forecast feature status")
async def forecast_status() -> dict[str, Any]:
    """Return the current state of the forecast subsystem."""
    return {
        "feature": "forecast",
        "status": "experimental_not_enabled",
        "available_by_default": False,
        "reason": (
            "Forecasting is not part of the supported end-to-end launch path yet. "
            "The previous implementation depended on synthetic demo data rather than "
            "the core telemetry pipeline."
        ),
    }


@router.get("/{device_id}", response_model=dict[str, Any], summary="Forecast endpoint placeholder")
async def get_forecast(
    device_id: str,
    horizon: int = Query(default=96, ge=1, le=672),
) -> dict[str, Any]:
    """Return a truthful error until a real telemetry-backed forecast exists."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            f"Forecasting is not enabled for device '{device_id}' in the reduced launch "
            f"version. Requested horizon={horizon}."
        ),
    )

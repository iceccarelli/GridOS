"""Experimental optimization routes kept outside the default launch surface.

This module is intentionally not mounted by ``gridos.main`` in the reduced
launch version. It remains only as an explicit placeholder for future work.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/optimization", tags=["Optimization"])


class OptimizationRequest(BaseModel):
    """Minimal request schema retained for future reactivation."""

    load_forecast_kw: list[float] = Field(..., min_length=1)
    solar_forecast_kw: list[float] = Field(..., min_length=1)


@router.get("/status", response_model=dict[str, Any], summary="Optimization feature status")
async def optimization_status() -> dict[str, Any]:
    """Return the current state of the optimization subsystem."""
    return {
        "feature": "optimization",
        "status": "advanced_manual_only",
        "available_by_default": False,
        "reason": (
            "Optimization is not part of the supported end-to-end launch path yet. "
            "The core release is focused on device registration, telemetry, and basic control."
        ),
    }


@router.post("/run", response_model=dict[str, Any], summary="Optimization endpoint placeholder")
async def run_optimization(request: OptimizationRequest) -> dict[str, Any]:
    """Return a truthful error until optimization is fully supported again."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Optimization is not enabled in the reduced launch version. "
            f"Received {len(request.load_forecast_kw)} load points and "
            f"{len(request.solar_forecast_kw)} solar points."
        ),
    )

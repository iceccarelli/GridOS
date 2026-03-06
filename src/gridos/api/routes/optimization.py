"""
Optimisation API routes.

Endpoints for running the MILP scheduler and retrieving dispatch schedules.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from gridos.config import settings
from gridos.optimization.scheduler import Scheduler, SchedulerConfig, ScheduleResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/optimization", tags=["Optimization"])

# Module-level cache for the latest schedule
_latest_schedule: ScheduleResult | None = None


class OptimizationRequest(BaseModel):
    """Request body for running the optimiser."""

    load_forecast_kw: list[float] = Field(
        ..., min_length=1, description="Forecasted load per time step (kW)."
    )
    solar_forecast_kw: list[float] = Field(
        ..., min_length=1, description="Forecasted solar per time step (kW)."
    )
    battery_capacity_kwh: float = Field(default=100.0, gt=0)
    battery_max_charge_kw: float = Field(default=50.0, gt=0)
    battery_max_discharge_kw: float = Field(default=50.0, gt=0)
    battery_efficiency: float = Field(default=0.92, gt=0, le=1)
    battery_soc_initial: float = Field(default=0.5, ge=0, le=1)
    import_prices: list[float] | None = Field(
        default=None, description="Per-step import prices ($/kWh)."
    )
    export_prices: list[float] | None = Field(
        default=None, description="Per-step export prices ($/kWh)."
    )


@router.post(
    "/run",
    response_model=dict[str, Any],
    summary="Run the optimisation scheduler",
)
async def run_optimization(request: OptimizationRequest) -> dict[str, Any]:
    """Solve the optimal dispatch problem and return the schedule."""
    global _latest_schedule

    n = len(request.load_forecast_kw)
    if len(request.solar_forecast_kw) < n:
        raise HTTPException(
            status_code=400,
            detail="solar_forecast_kw must have at least as many elements as load_forecast_kw",
        )

    config = SchedulerConfig(
        time_horizon_hours=int(n * settings.opt_time_step_minutes / 60),
        time_step_minutes=settings.opt_time_step_minutes,
        battery_capacity_kwh=request.battery_capacity_kwh,
        battery_max_charge_kw=request.battery_max_charge_kw,
        battery_max_discharge_kw=request.battery_max_discharge_kw,
        battery_efficiency=request.battery_efficiency,
        battery_soc_initial=request.battery_soc_initial,
    )

    scheduler = Scheduler(config)

    try:
        result = scheduler.solve(
            load_forecast_kw=np.array(request.load_forecast_kw),
            solar_forecast_kw=np.array(request.solar_forecast_kw),
            import_prices=(
                np.array(request.import_prices) if request.import_prices else None
            ),
            export_prices=(
                np.array(request.export_prices) if request.export_prices else None
            ),
        )
        _latest_schedule = result
    except Exception as exc:
        logger.error("Optimisation error: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Optimisation failed: {exc}"
        ) from exc

    return {
        "status": result.status,
        "objective_value": result.objective_value,
        "solver_time_seconds": result.solver_time_seconds,
        "battery_power_kw": result.battery_power_kw,
        "battery_soc": result.battery_soc,
        "grid_import_kw": result.grid_import_kw,
        "grid_export_kw": result.grid_export_kw,
        "net_load_kw": result.net_load_kw,
    }


@router.get(
    "/schedule",
    response_model=dict[str, Any] | None,
    summary="Get the latest optimisation schedule",
)
async def get_schedule() -> dict[str, Any] | None:
    """Return the most recently computed schedule."""
    if _latest_schedule is None:
        raise HTTPException(
            status_code=404,
            detail="No schedule available — run /optimization/run first",
        )

    return {
        "status": _latest_schedule.status,
        "objective_value": _latest_schedule.objective_value,
        "battery_power_kw": _latest_schedule.battery_power_kw,
        "battery_soc": _latest_schedule.battery_soc,
        "grid_import_kw": _latest_schedule.grid_import_kw,
        "grid_export_kw": _latest_schedule.grid_export_kw,
    }

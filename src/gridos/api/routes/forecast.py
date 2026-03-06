"""
Forecasting API routes.

Endpoints for generating load and solar forecasts using the ML modules.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from gridos.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get(
    "/{device_id}",
    response_model=dict[str, Any],
    summary="Generate a forecast for a device",
)
async def get_forecast(
    device_id: str,
    horizon: int = Query(
        default=96,
        ge=1,
        le=672,
        description="Number of time steps to forecast",
    ),
) -> dict[str, Any]:
    """Generate a power forecast for the specified device.

    Uses the trained LSTM model if available, otherwise falls back to
    a persistence forecast.
    """
    try:
        from gridos.digital_twin.ml.forecaster import LSTMForecaster

        forecaster = LSTMForecaster(
            lookback=96,
            horizon=horizon,
            model_dir=str(settings.ml_model_dir),
        )

        # Attempt to load a pre-trained model
        try:
            forecaster.load()
        except FileNotFoundError:
            logger.info(
                "No trained model found for %s — using persistence fallback",
                device_id,
            )

        # Generate a synthetic recent history for demo purposes
        # In production, this would be fetched from the storage backend
        recent = np.random.uniform(10, 100, size=96).astype(np.float32)
        forecast_values = forecaster.predict(recent)

        return {
            "device_id": device_id,
            "horizon": horizon,
            "time_step_minutes": settings.opt_time_step_minutes,
            "forecast_kw": forecast_values.tolist(),
            "model": "lstm"
            if forecaster._torch_available and forecaster._model
            else "persistence",
        }

    except Exception as exc:
        logger.error("Forecast error for %s: %s", device_id, exc)
        raise HTTPException(
            status_code=500, detail=f"Forecast generation failed: {exc}"
        ) from exc

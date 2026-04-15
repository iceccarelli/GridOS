"""GridOS FastAPI application entry point for the reduced launch path.

The supported default surface is intentionally small and truthful:
root metadata, health checks, interactive documentation, device registration,
telemetry ingestion and query, control command acceptance, and optional
WebSocket telemetry streaming.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from gridos import __version__
from gridos.api.dependencies import close_storage
from gridos.api.routes import control, devices, telemetry
from gridos.api.websocket_manager import ws_manager
from gridos.config import settings

logger = logging.getLogger("gridos")


SUPPORTED_ROUTE_GROUPS = {
    "devices": "/api/v1/devices",
    "telemetry": "/api/v1/telemetry",
    "control": "/api/v1/control",
    "docs": "/docs",
    "health": "/health",
    "websocket": "/ws/telemetry",
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Configure logging and close shared resources on shutdown."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info(
        "GridOS v%s starting (env=%s, storage=%s)",
        __version__,
        settings.env.value,
        settings.storage_backend.value,
    )
    yield
    await close_storage()
    logger.info("GridOS shutdown complete")


app = FastAPI(
    title="GridOS",
    description=(
        "Lightweight API for device registration, telemetry ingestion, and "
        "basic control workflows in a local-first GridOS deployment."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices.router, prefix="/api/v1")
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(control.router, prefix="/api/v1")


@app.websocket("/ws/telemetry")
async def websocket_telemetry(
    websocket: WebSocket,
    device_ids: str | None = None,
) -> None:
    """Optional WebSocket endpoint for live telemetry streaming."""
    ids: list[str] | None = None
    if device_ids:
        ids = [device_id.strip() for device_id in device_ids.split(",") if device_id.strip()]

    await ws_manager.connect(websocket, device_ids=ids)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, object]:
    """Return service health and supported runtime surface."""
    return {
        "status": "healthy",
        "version": __version__,
        "environment": settings.env.value,
        "storage_backend": settings.storage_backend.value,
        "websocket_connections": ws_manager.active_connections,
        "supported_routes": SUPPORTED_ROUTE_GROUPS,
    }


@app.get("/", tags=["System"])
async def root() -> dict[str, object]:
    """Return public metadata for the reduced launch version."""
    return {
        "name": "GridOS",
        "version": __version__,
        "mode": "reduced_launch",
        "description": "Local-first DER telemetry and basic control API.",
        "supported_features": [
            "device registration",
            "telemetry ingestion",
            "telemetry history and latest lookup",
            "basic control command acceptance",
            "optional telemetry websocket",
        ],
        "unsupported_by_default": [
            "forecasting",
            "optimization",
            "protocol-specific adapter automation",
        ],
        "routes": SUPPORTED_ROUTE_GROUPS,
    }

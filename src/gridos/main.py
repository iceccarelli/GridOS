"""
GridOS FastAPI application entry point.

Creates the FastAPI app, includes all routers, configures CORS and
logging, and defines startup/shutdown lifecycle events.

Usage::

    uvicorn src.gridos.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from gridos import __version__
from gridos.api.dependencies import close_storage
from gridos.api.routes import control, devices, forecast, optimization, telemetry
from gridos.api.websocket_manager import ws_manager
from gridos.config import settings

logger = logging.getLogger("gridos")


# ── Lifecycle ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    # Startup
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info("GridOS v%s starting (env=%s)", __version__, settings.env.value)
    yield
    # Shutdown
    await close_storage()
    logger.info("GridOS shutdown complete")


# ── App Factory ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="GridOS — Open Energy Operating System",
    description=(
        "Vendor-neutral middleware for managing Distributed Energy Resources "
        "(DERs) through a unified, standards-based API."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/api/v1")
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(control.router, prefix="/api/v1")
app.include_router(forecast.router, prefix="/api/v1")
app.include_router(optimization.router, prefix="/api/v1")


# ── WebSocket Endpoint ──────────────────────────────────────────────────────


@app.websocket("/ws/telemetry")
async def websocket_telemetry(
    websocket: WebSocket,
    device_ids: str | None = None,
) -> None:
    """WebSocket endpoint for live telemetry streaming.

    Connect to ``ws://host:port/ws/telemetry?device_ids=dev1,dev2``
    to subscribe to specific devices, or omit the parameter to receive
    all telemetry.
    """
    ids: list[str] | None = None
    if device_ids:
        ids = [d.strip() for d in device_ids.split(",") if d.strip()]

    await ws_manager.connect(websocket, device_ids=ids)
    try:
        while True:
            # Keep the connection alive; client can also send messages
            data = await websocket.receive_text()
            logger.debug("WebSocket received: %s", data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── Health Check ─────────────────────────────────────────────────────────────


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Return service health status."""
    return {
        "status": "healthy",
        "version": __version__,
        "environment": settings.env.value,
        "websocket_connections": ws_manager.active_connections,
    }


@app.get("/", tags=["System"])
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "GridOS",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }

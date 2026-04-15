"""
GridOS FastAPI application entry point.

This reduced launch version keeps the public runtime surface intentionally small:
root metadata, health checks, interactive API docs, telemetry ingestion, telemetry
queries, and an optional WebSocket endpoint.
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
from gridos.api.routes import telemetry
from gridos.api.websocket_manager import ws_manager
from gridos.config import settings

logger = logging.getLogger("gridos")


def _using_inmemory_storage() -> bool:
    return os.getenv("GRIDOS_USE_INMEMORY_STORAGE", "true").lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan hooks."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info(
        "GridOS v%s starting (env=%s, in_memory_storage=%s)",
        __version__,
        settings.env.value,
        _using_inmemory_storage(),
    )
    yield
    await close_storage()
    logger.info("GridOS shutdown complete")


app = FastAPI(
    title="GridOS",
    description=(
        "Lightweight API for DER telemetry ingestion and grid-oriented experimentation. "
        "The default launch path favors a small local setup over broad platform claims."
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

app.include_router(telemetry.router, prefix="/api/v1")


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
    """Return service health status."""
    return {
        "status": "healthy",
        "version": __version__,
        "environment": settings.env.value,
        "storage_mode": "inmemory" if _using_inmemory_storage() else settings.storage_backend.value,
        "websocket_connections": ws_manager.active_connections,
    }


@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "GridOS",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "telemetry": "/api/v1/telemetry",
    }

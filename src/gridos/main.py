"""GridOS FastAPI application entry point for the reduced launch path."""

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


def _storage_mode() -> str:
    """Return the effective storage mode advertised by the current runtime."""
    use_inmemory = os.getenv("GRIDOS_USE_INMEMORY_STORAGE", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return "inmemory" if use_inmemory else settings.storage_backend.value


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan with lightweight startup and shutdown hooks."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info("GridOS v%s starting (env=%s, storage=%s)", __version__, settings.env.value, _storage_mode())
    yield
    await close_storage()
    logger.info("GridOS shutdown complete")


app = FastAPI(
    title="GridOS",
    description=(
        "Lightweight FastAPI service for DER device registration, telemetry ingestion, "
        "telemetry queries, and basic control workflows."
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
    """Provide a lightweight WebSocket stream for live telemetry updates."""
    ids: list[str] | None = None
    if device_ids:
        ids = [device_id.strip() for device_id in device_ids.split(",") if device_id.strip()]

    await ws_manager.connect(websocket, device_ids=ids)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str | int]:
    """Return a small health payload for first-run verification."""
    return {
        "status": "healthy",
        "version": __version__,
        "environment": settings.env.value,
        "storage_backend": _storage_mode(),
        "websocket_connections": ws_manager.active_connections,
    }


@app.get("/", tags=["System"])
async def root() -> dict[str, str | dict[str, str]]:
    """Return the supported reduced-launch service surface."""
    return {
        "name": "GridOS",
        "version": __version__,
        "mode": "reduced_launch",
        "docs": "/docs",
        "health": "/health",
        "routes": {
            "devices": "/api/v1/devices",
            "telemetry": "/api/v1/telemetry",
            "control": "/api/v1/control",
            "docs": "/docs",
        },
    }

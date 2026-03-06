"""
FastAPI dependency injection for GridOS.

Provides singleton instances of storage backends, adapter registries,
and other shared resources that are injected into route handlers via
FastAPI's ``Depends`` mechanism.
"""

from __future__ import annotations

import logging
from typing import Any

from gridos.adapters.base import BaseAdapter
from gridos.config import Settings, settings
from gridos.storage.base import StorageBackend

logger = logging.getLogger(__name__)

# ── Singletons ───────────────────────────────────────────────────────────────

_storage_backend: StorageBackend | None = None
_adapter_registry: dict[str, BaseAdapter] = {}
_device_registry: dict[str, dict[str, Any]] = {}


# ── Storage ──────────────────────────────────────────────────────────────────


async def get_storage() -> StorageBackend:
    """Return the configured storage backend singleton.

    On first call, instantiates and connects the backend based on
    ``settings.storage_backend``.
    """
    global _storage_backend
    if _storage_backend is not None and _storage_backend.is_connected:
        return _storage_backend

    if settings.storage_backend.value == "influxdb":
        from gridos.storage.influxdb import InfluxDBBackend

        _storage_backend = InfluxDBBackend()
    else:
        from gridos.storage.timescaledb import TimescaleDBBackend

        _storage_backend = TimescaleDBBackend()

    try:
        await _storage_backend.connect()
    except Exception as exc:
        logger.error("Storage backend connection failed: %s", exc)
        raise

    return _storage_backend


async def close_storage() -> None:
    """Disconnect the storage backend (called on app shutdown)."""
    global _storage_backend
    if _storage_backend is not None:
        await _storage_backend.disconnect()
        _storage_backend = None


# ── Adapter Registry ─────────────────────────────────────────────────────────


def get_adapter_registry() -> dict[str, BaseAdapter]:
    """Return the adapter registry (device_id → adapter)."""
    return _adapter_registry


def register_adapter(device_id: str, adapter: BaseAdapter) -> None:
    """Register an adapter for a device."""
    _adapter_registry[device_id] = adapter
    logger.info("Adapter registered for device %s", device_id)


def unregister_adapter(device_id: str) -> None:
    """Remove an adapter from the registry."""
    _adapter_registry.pop(device_id, None)


# ── Device Registry ──────────────────────────────────────────────────────────


def get_device_registry() -> dict[str, dict[str, Any]]:
    """Return the in-memory device registry."""
    return _device_registry


def register_device(device_id: str, info: dict[str, Any]) -> None:
    """Register a device in the in-memory registry."""
    _device_registry[device_id] = info
    logger.info("Device registered: %s", device_id)


def get_settings() -> Settings:
    """Return the application settings."""
    return settings

"""
FastAPI dependency wiring for GridOS.

This reduced launch version introduces a small in-memory telemetry backend so the
repository can run end-to-end without requiring external infrastructure. InfluxDB
and TimescaleDB remain available when explicitly configured.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from gridos.adapters.base import BaseAdapter
from gridos.config import Settings, settings
from gridos.models.common import DERTelemetry
from gridos.storage.base import StorageBackend

logger = logging.getLogger(__name__)

_storage_backend: StorageBackend | None = None
_adapter_registry: dict[str, BaseAdapter] = {}
_device_registry: dict[str, dict[str, Any]] = {}


class InMemoryStorageBackend(StorageBackend):
    """Small in-memory storage backend for local development and demos."""

    def __init__(self) -> None:
        super().__init__()
        self._data: dict[str, list[DERTelemetry]] = defaultdict(list)

    @property
    def backend_name(self) -> str:
        return "inmemory"

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        self._data.clear()

    async def write_point(self, telemetry: DERTelemetry) -> None:
        self._data[telemetry.device_id].append(telemetry)
        self._data[telemetry.device_id].sort(key=lambda item: _normalized_ts(item.timestamp))

    async def write_points(self, telemetry_list: list[DERTelemetry]) -> None:
        for telemetry in telemetry_list:
            await self.write_point(telemetry)

    async def query_range(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[DERTelemetry]:
        normalized_start = _normalized_ts(start)
        normalized_end = _normalized_ts(end)
        results = [
            item
            for item in self._data.get(device_id, [])
            if normalized_start <= _normalized_ts(item.timestamp) <= normalized_end
        ]
        return results[:limit]

    async def get_latest(self, device_id: str) -> DERTelemetry | None:
        items = self._data.get(device_id, [])
        if not items:
            return None
        return max(items, key=lambda item: _normalized_ts(item.timestamp))


def _normalized_ts(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _use_inmemory_storage() -> bool:
    return os.getenv("GRIDOS_USE_INMEMORY_STORAGE", "true").lower() in {"1", "true", "yes", "on"}


async def get_storage() -> StorageBackend:
    """Return the configured storage backend singleton."""
    global _storage_backend
    if _storage_backend is not None and _storage_backend.is_connected:
        return _storage_backend

    if _use_inmemory_storage():
        _storage_backend = InMemoryStorageBackend()
    elif settings.storage_backend.value == "influxdb":
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
    """Disconnect the active storage backend."""
    global _storage_backend
    if _storage_backend is not None:
        await _storage_backend.disconnect()
        _storage_backend = None


def get_adapter_registry() -> dict[str, BaseAdapter]:
    """Return the adapter registry."""
    return _adapter_registry


def register_adapter(device_id: str, adapter: BaseAdapter) -> None:
    """Register an adapter for a device."""
    _adapter_registry[device_id] = adapter
    logger.info("Adapter registered for device %s", device_id)


def unregister_adapter(device_id: str) -> None:
    """Remove an adapter from the registry."""
    _adapter_registry.pop(device_id, None)


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

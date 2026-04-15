"""FastAPI dependency wiring for the reduced GridOS launch path.

The default runtime is deliberately local-first. An in-memory telemetry backend
and an in-memory device registry are always available without external
infrastructure. InfluxDB and TimescaleDB remain optional integrations that are
only activated when explicitly requested.
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
    """Small, dependency-free storage backend for development and launch use."""

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
        self._require_connection()
        bucket = self._data[telemetry.device_id]
        bucket.append(telemetry)
        bucket.sort(key=lambda item: _normalized_ts(item.timestamp))

    async def write_points(self, telemetry_list: list[DERTelemetry]) -> None:
        self._require_connection()
        for telemetry in telemetry_list:
            await self.write_point(telemetry)

    async def query_range(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[DERTelemetry]:
        self._require_connection()
        normalized_start = _normalized_ts(start)
        normalized_end = _normalized_ts(end)
        readings = [
            item
            for item in self._data.get(device_id, [])
            if normalized_start <= _normalized_ts(item.timestamp) <= normalized_end
        ]
        return readings[:limit]

    async def get_latest(self, device_id: str) -> DERTelemetry | None:
        self._require_connection()
        readings = self._data.get(device_id, [])
        if not readings:
            return None
        return max(readings, key=lambda item: _normalized_ts(item.timestamp))


def _normalized_ts(value: datetime) -> datetime:
    """Normalize timestamps so naive and UTC-aware values can be compared safely."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _use_inmemory_storage() -> bool:
    """Return whether the launch-safe in-memory backend should be used."""
    if _env_flag("GRIDOS_USE_INMEMORY_STORAGE", True):
        return True
    selected_backend = getattr(settings.storage_backend, "value", str(settings.storage_backend))
    return selected_backend not in {"influxdb", "timescaledb"}


def _selected_backend_name() -> str:
    return getattr(settings.storage_backend, "value", str(settings.storage_backend))


async def _build_external_backend() -> StorageBackend:
    """Instantiate the explicitly requested external storage backend."""
    backend_name = _selected_backend_name()

    if backend_name == "influxdb":
        from gridos.storage.influxdb import InfluxDBBackend

        return InfluxDBBackend(
            {
                "url": settings.influxdb_url,
                "token": settings.influxdb_token,
                "org": settings.influxdb_org,
                "bucket": settings.influxdb_bucket,
            }
        )

    if backend_name == "timescaledb":
        from gridos.storage.timescaledb import TimescaleDBBackend

        return TimescaleDBBackend({"dsn": settings.timescaledb_dsn})

    raise ValueError(
        f"Unsupported storage backend '{backend_name}'. Use inmemory, influxdb, or timescaledb."
    )


async def get_storage() -> StorageBackend:
    """Return the shared storage backend instance for the current process."""
    global _storage_backend

    if _storage_backend is not None and _storage_backend.is_connected:
        return _storage_backend

    backend: StorageBackend
    if _use_inmemory_storage():
        backend = InMemoryStorageBackend()
    else:
        backend = await _build_external_backend()

    await backend.connect()
    _storage_backend = backend
    logger.info("GridOS storage backend ready: %s", backend.backend_name)
    return backend


async def close_storage() -> None:
    """Disconnect and clear the shared storage backend instance."""
    global _storage_backend

    if _storage_backend is None:
        return

    await _storage_backend.disconnect()
    _storage_backend = None


def get_adapter_registry() -> dict[str, BaseAdapter]:
    """Return the adapter registry used by the control route."""
    return _adapter_registry


def register_adapter(device_id: str, adapter: BaseAdapter) -> None:
    """Attach an adapter instance to a registered device."""
    _adapter_registry[device_id] = adapter
    logger.info("Adapter registered for device %s", device_id)


def unregister_adapter(device_id: str) -> None:
    """Remove an adapter instance from the registry if one exists."""
    _adapter_registry.pop(device_id, None)


def get_device_registry() -> dict[str, dict[str, Any]]:
    """Return the simple in-memory device registry."""
    return _device_registry


def register_device(device_id: str, info: dict[str, Any]) -> None:
    """Store one device record in the in-memory registry."""
    _device_registry[device_id] = info
    logger.info("Device registered: %s", device_id)


def unregister_device(device_id: str) -> None:
    """Remove a device and any attached adapter from the local registries."""
    _device_registry.pop(device_id, None)
    unregister_adapter(device_id)


def reset_registries() -> None:
    """Clear in-memory registries, mainly for tests and local resets."""
    _device_registry.clear()
    _adapter_registry.clear()


def get_settings() -> Settings:
    """Return the application settings singleton."""
    return settings

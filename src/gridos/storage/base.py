"""Stable storage contract for the reduced GridOS launch path.

The launch-ready repository supports one default backend implementation and may
optionally use external backends. All storage providers implement this small
async contract so the API surface can remain consistent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from gridos.models.common import DERTelemetry


class StorageBackend(ABC):
    """Small async interface for telemetry persistence backends."""

    def __init__(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Return whether the backend has completed its connection step."""
        return self._connected

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return a short human-readable backend identifier."""

    @abstractmethod
    async def connect(self) -> None:
        """Prepare the backend for reads and writes."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close any open resources held by the backend."""

    @abstractmethod
    async def write_point(self, telemetry: DERTelemetry) -> None:
        """Persist a single telemetry snapshot."""

    @abstractmethod
    async def write_points(self, telemetry_list: list[DERTelemetry]) -> None:
        """Persist multiple telemetry snapshots."""

    @abstractmethod
    async def query_range(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[DERTelemetry]:
        """Return telemetry for one device within the requested time window."""

    @abstractmethod
    async def get_latest(self, device_id: str) -> DERTelemetry | None:
        """Return the latest telemetry snapshot for one device, if any."""

    def _require_connection(self) -> None:
        """Raise a clear error when backend operations are attempted too early."""
        if not self._connected:
            raise RuntimeError(f"{self.backend_name} backend is not connected")

    async def __aenter__(self) -> "StorageBackend":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

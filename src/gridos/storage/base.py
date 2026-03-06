"""
Abstract base class for GridOS time-series storage backends.

Every concrete backend (InfluxDB, TimescaleDB, …) must inherit from
:class:`StorageBackend` and implement the async methods for writing,
querying, and retrieving telemetry data.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from gridos.models.common import DERTelemetry

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Unified async interface for time-series telemetry storage.

    Parameters
    ----------
    config:
        Backend-specific configuration dictionary.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}
        self._connected: bool = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def backend_name(self) -> str:
        """Human-readable backend name (override in subclasses)."""
        return "unknown"

    # ── Lifecycle ────────────────────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> None:
        """Establish a connection to the storage backend."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the connection."""

    # ── Write ────────────────────────────────────────────────────────────

    @abstractmethod
    async def write_point(self, telemetry: DERTelemetry) -> None:
        """Write a single telemetry point.

        Parameters
        ----------
        telemetry:
            The telemetry reading to persist.
        """

    @abstractmethod
    async def write_points(self, telemetry_list: list[DERTelemetry]) -> None:
        """Write a batch of telemetry points.

        Parameters
        ----------
        telemetry_list:
            List of telemetry readings to persist.
        """

    # ── Read ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def query_range(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[DERTelemetry]:
        """Query telemetry for a device within a time range.

        Parameters
        ----------
        device_id:
            Target device identifier.
        start:
            Start of the query window (inclusive).
        end:
            End of the query window (inclusive).
        limit:
            Maximum number of records to return.

        Returns
        -------
        list[DERTelemetry]
            Telemetry readings ordered by timestamp ascending.
        """

    @abstractmethod
    async def get_latest(self, device_id: str) -> DERTelemetry | None:
        """Retrieve the most recent telemetry for a device.

        Parameters
        ----------
        device_id:
            Target device identifier.

        Returns
        -------
        DERTelemetry or None
            The latest reading, or ``None`` if no data exists.
        """

    # ── Context Manager ──────────────────────────────────────────────────

    async def __aenter__(self) -> StorageBackend:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()

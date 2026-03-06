"""
Abstract base class for all GridOS protocol adapters.

Every concrete adapter (Modbus, MQTT, DNP3, …) must inherit from
:class:`BaseAdapter` and implement the four async lifecycle methods:
``connect``, ``disconnect``, ``read_telemetry``, and ``write_command``.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from gridos.models.common import ControlCommand, DERTelemetry

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """Unified async interface for DER communication protocols.

    Parameters
    ----------
    device_id:
        Identifier of the device this adapter instance manages.
    config:
        Protocol-specific configuration dictionary.
    """

    def __init__(self, device_id: str, config: dict[str, Any] | None = None) -> None:
        self.device_id = device_id
        self.config: dict[str, Any] = config or {}
        self._connected: bool = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        """Return ``True`` if the adapter has an active connection."""
        return self._connected

    @property
    def protocol_name(self) -> str:
        """Human-readable protocol name (override in subclasses)."""
        return "unknown"

    # ── Abstract Methods ─────────────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> None:
        """Establish a connection to the device.

        Raises
        ------
        ConnectionError
            If the connection cannot be established.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the connection."""

    @abstractmethod
    async def read_telemetry(self) -> DERTelemetry:
        """Read the latest telemetry from the device.

        Returns
        -------
        DERTelemetry
            A validated telemetry snapshot.

        Raises
        ------
        IOError
            If the read operation fails.
        """

    @abstractmethod
    async def write_command(self, command: ControlCommand) -> bool:
        """Send a control command to the device.

        Parameters
        ----------
        command:
            The validated control command to execute.

        Returns
        -------
        bool
            ``True`` if the command was acknowledged by the device.

        Raises
        ------
        IOError
            If the write operation fails.
        """

    # ── Context Manager ──────────────────────────────────────────────────

    async def __aenter__(self) -> BaseAdapter:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()

    # ── Helpers ──────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return (
            f"<{self.__class__.__name__} device_id={self.device_id!r} "
            f"protocol={self.protocol_name!r} status={status}>"
        )

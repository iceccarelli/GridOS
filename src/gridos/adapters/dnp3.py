"""
DNP3 protocol adapter for GridOS (stub).

DNP3 (Distributed Network Protocol 3) is widely used in SCADA systems for
utility-scale DER communication.  This module provides the adapter skeleton;
a full implementation requires a DNP3 master library such as ``opendnp3`` or
``pydnp3``.

TODO:
    - Integrate with ``opendnp3`` C++ bindings or ``pydnp3``.
    - Implement integrity polls and event-driven reads.
    - Support DNP3 Secure Authentication (SA).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from gridos.adapters.base import BaseAdapter
from gridos.models.common import ControlCommand, DERStatus, DERTelemetry

logger = logging.getLogger(__name__)


class DNP3Adapter(BaseAdapter):
    """DNP3 master adapter (stub implementation).

    Parameters
    ----------
    device_id:
        Unique device identifier.
    config:
        Expected keys: ``outstation_host``, ``outstation_port`` (default 20000),
        ``master_address`` (default 1), ``outstation_address`` (default 10).
    """

    def __init__(self, device_id: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(device_id, config)
        self._outstation_host: str = self.config.get("outstation_host", "localhost")
        self._outstation_port: int = int(self.config.get("outstation_port", 20000))
        self._master_address: int = int(self.config.get("master_address", 1))
        self._outstation_address: int = int(self.config.get("outstation_address", 10))

    @property
    def protocol_name(self) -> str:
        return "dnp3"

    async def connect(self) -> None:
        """Establish a DNP3 master session.

        Raises
        ------
        NotImplementedError
            Full DNP3 support is not yet implemented.
        """
        self.logger.warning(
            "DNP3 adapter connect() called — stub implementation. "
            "Install opendnp3 and implement the full master stack."
        )
        # Mark as connected so that the adapter can be used in test harnesses
        # with simulated data.
        self._connected = True

    async def disconnect(self) -> None:
        """Close the DNP3 session."""
        self._connected = False
        self.logger.info("DNP3 adapter disconnected (stub)")

    async def read_telemetry(self) -> DERTelemetry:
        """Perform an integrity poll and return telemetry.

        Returns a placeholder telemetry object until the full DNP3 master
        stack is integrated.
        """
        self.logger.debug("DNP3 read_telemetry() — returning placeholder data")
        return DERTelemetry(
            device_id=self.device_id,
            timestamp=datetime.utcnow(),
            power_kw=0.0,
            reactive_power_kvar=0.0,
            status=DERStatus.UNKNOWN,
            metadata={"note": "DNP3 stub — replace with real implementation"},
        )

    async def write_command(self, command: ControlCommand) -> bool:
        """Send a CROB or analog output to the outstation.

        Returns ``False`` until the full DNP3 master stack is integrated.
        """
        self.logger.warning(
            "DNP3 write_command() called — stub implementation. "
            "Command %s was NOT dispatched.",
            command.command_id,
        )
        return False

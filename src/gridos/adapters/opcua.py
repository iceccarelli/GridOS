"""
OPC-UA protocol adapter for GridOS.

Uses the ``asyncua`` library to connect to OPC-UA servers commonly found
in industrial energy equipment (inverters, PLCs, RTUs).  Node IDs for
telemetry variables are configurable via the adapter config dictionary.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from gridos.adapters.base import BaseAdapter
from gridos.models.common import ControlCommand, DERStatus, DERTelemetry

logger = logging.getLogger(__name__)

# Default OPC-UA node ID mapping — override via adapter config
DEFAULT_NODE_MAP: dict[str, str] = {
    "power_kw": "ns=2;s=Device.ActivePower",
    "reactive_power_kvar": "ns=2;s=Device.ReactivePower",
    "voltage_v": "ns=2;s=Device.Voltage",
    "current_a": "ns=2;s=Device.Current",
    "frequency_hz": "ns=2;s=Device.Frequency",
    "soc_percent": "ns=2;s=Device.SOC",
    "temperature_c": "ns=2;s=Device.Temperature",
}


class OPCUAAdapter(BaseAdapter):
    """Async OPC-UA client adapter.

    Parameters
    ----------
    device_id:
        Unique device identifier.
    config:
        Must contain ``endpoint_url`` (e.g. ``opc.tcp://localhost:4840``).
        Optional: ``node_map`` (dict mapping field names to OPC-UA node IDs),
        ``security_policy``, ``certificate_path``.
    """

    def __init__(self, device_id: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(device_id, config)
        self._endpoint_url: str = self.config.get(
            "endpoint_url", "opc.tcp://localhost:4840"
        )
        self._node_map: dict[str, str] = self.config.get("node_map", DEFAULT_NODE_MAP)
        self._client: Any = None

    @property
    def protocol_name(self) -> str:
        return "opcua"

    async def connect(self) -> None:
        """Establish an OPC-UA session."""
        try:
            from asyncua import Client as OPCUAClient

            self._client = OPCUAClient(url=self._endpoint_url, timeout=10)
            await self._client.connect()
            self._connected = True
            self.logger.info("OPC-UA connected to %s", self._endpoint_url)
        except ImportError as err:
            raise ImportError(
                "asyncua is required for the OPC-UA adapter. "
                "Install it with: pip install asyncua"
            ) from err
        except Exception as exc:
            self._connected = False
            self.logger.error("OPC-UA connection error: %s", exc)
            raise ConnectionError(str(exc)) from exc

    async def disconnect(self) -> None:
        """Close the OPC-UA session."""
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception as exc:
                self.logger.warning("OPC-UA disconnect warning: %s", exc)
            finally:
                self._connected = False
                self.logger.info("OPC-UA disconnected")

    async def read_telemetry(self) -> DERTelemetry:
        """Read OPC-UA nodes and return a ``DERTelemetry`` snapshot."""
        if not self._connected or self._client is None:
            raise OSError("OPC-UA adapter is not connected")

        values: dict[str, float | None] = {}
        for field_name, node_id in self._node_map.items():
            try:
                node = self._client.get_node(node_id)
                value = await node.read_value()
                values[field_name] = float(value) if value is not None else None
            except Exception as exc:
                self.logger.warning(
                    "OPC-UA read error for %s (%s): %s", field_name, node_id, exc
                )
                values[field_name] = None

        return DERTelemetry(
            device_id=self.device_id,
            timestamp=datetime.utcnow(),
            power_kw=values.get("power_kw") or 0.0,
            reactive_power_kvar=values.get("reactive_power_kvar") or 0.0,
            voltage_v=values.get("voltage_v"),
            current_a=values.get("current_a"),
            frequency_hz=values.get("frequency_hz"),
            soc_percent=values.get("soc_percent"),
            temperature_c=values.get("temperature_c"),
            status=DERStatus.ONLINE,
        )

    async def write_command(self, command: ControlCommand) -> bool:
        """Write a setpoint to the device via OPC-UA."""
        if not self._connected or self._client is None:
            raise OSError("OPC-UA adapter is not connected")

        try:
            setpoint_node_id = self.config.get(
                "setpoint_node_id", "ns=2;s=Device.PowerSetpoint"
            )
            node = self._client.get_node(setpoint_node_id)
            if command.setpoint_kw is not None:
                await node.write_value(float(command.setpoint_kw))
                self.logger.info(
                    "OPC-UA command sent: setpoint_kw=%.2f to %s",
                    command.setpoint_kw,
                    setpoint_node_id,
                )
                return True
            self.logger.warning("No setpoint_kw in command; nothing written")
            return False
        except Exception as exc:
            self.logger.error("OPC-UA write error: %s", exc)
            return False

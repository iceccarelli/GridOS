"""
Modbus TCP/RTU protocol adapter for GridOS.

Uses ``pymodbus`` (v3.6+) with its native async transport to read holding
registers and write coils / registers on DER devices.  Register mappings
are configurable per device via the ``config`` dictionary.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from gridos.adapters.base import BaseAdapter
from gridos.models.common import ControlCommand, DERStatus, DERTelemetry

logger = logging.getLogger(__name__)

# Default Modbus register map — override via adapter config
DEFAULT_REGISTER_MAP: dict[str, dict[str, Any]] = {
    "power_kw": {"address": 0, "count": 2, "scale": 0.1, "unit": "kW"},
    "reactive_power_kvar": {"address": 2, "count": 2, "scale": 0.1, "unit": "kVAR"},
    "voltage_v": {"address": 4, "count": 2, "scale": 0.1, "unit": "V"},
    "current_a": {"address": 6, "count": 2, "scale": 0.01, "unit": "A"},
    "frequency_hz": {"address": 8, "count": 1, "scale": 0.01, "unit": "Hz"},
    "soc_percent": {"address": 9, "count": 1, "scale": 0.1, "unit": "%"},
    "temperature_c": {"address": 10, "count": 1, "scale": 0.1, "unit": "°C"},
}


def _decode_registers(registers: list[int], count: int, scale: float) -> float:
    """Decode one or two 16-bit registers into a scaled float."""
    if count == 2 and len(registers) >= 2:
        raw = (registers[0] << 16) | registers[1]
    elif registers:
        raw = registers[0]
    else:
        raw = 0
    return raw * scale


class ModbusAdapter(BaseAdapter):
    """Async Modbus TCP adapter.

    Parameters
    ----------
    device_id:
        Unique device identifier.
    config:
        Must contain ``host`` and ``port``.  Optionally ``unit_id``
        (default 1) and ``register_map`` (overrides defaults).
    """

    def __init__(self, device_id: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(device_id, config)
        self._host: str = self.config.get("host", "localhost")
        self._port: int = int(self.config.get("port", 502))
        self._unit_id: int = int(self.config.get("unit_id", 1))
        self._register_map: dict[str, dict[str, Any]] = self.config.get(
            "register_map", DEFAULT_REGISTER_MAP
        )
        self._client: Any = None

    @property
    def protocol_name(self) -> str:
        return "modbus_tcp"

    async def connect(self) -> None:
        """Establish an async Modbus TCP connection."""
        try:
            from pymodbus.client import AsyncModbusTcpClient

            self._client = AsyncModbusTcpClient(
                host=self._host,
                port=self._port,
                timeout=5,
            )
            connected = await self._client.connect()
            if not connected:
                raise ConnectionError(
                    f"Modbus TCP connection to {self._host}:{self._port} failed"
                )
            self._connected = True
            self.logger.info(
                "Modbus connected",
                extra={
                    "device_id": self.device_id,
                    "host": self._host,
                    "port": self._port,
                },
            )
        except ImportError as err:
            raise ImportError(
                "pymodbus is required for the Modbus adapter. "
                "Install it with: pip install pymodbus"
            ) from err
        except Exception as exc:
            self._connected = False
            self.logger.error("Modbus connection error: %s", exc)
            raise ConnectionError(str(exc)) from exc

    async def disconnect(self) -> None:
        """Close the Modbus TCP connection."""
        if self._client is not None:
            self._client.close()
            self._connected = False
            self.logger.info("Modbus disconnected", extra={"device_id": self.device_id})

    async def read_telemetry(self) -> DERTelemetry:
        """Read registers and return a ``DERTelemetry`` snapshot."""
        if not self._connected or self._client is None:
            raise OSError("Modbus adapter is not connected")

        values: dict[str, float] = {}
        for field_name, mapping in self._register_map.items():
            try:
                result = await self._client.read_holding_registers(
                    address=mapping["address"],
                    count=mapping["count"],
                    slave=self._unit_id,
                )
                if result.isError():
                    self.logger.warning(
                        "Modbus read error for %s: %s", field_name, result
                    )
                    values[field_name] = 0.0
                else:
                    values[field_name] = _decode_registers(
                        result.registers, mapping["count"], mapping["scale"]
                    )
            except Exception as exc:
                self.logger.warning("Modbus read exception for %s: %s", field_name, exc)
                values[field_name] = 0.0

        return DERTelemetry(
            device_id=self.device_id,
            timestamp=datetime.utcnow(),
            power_kw=values.get("power_kw", 0.0),
            reactive_power_kvar=values.get("reactive_power_kvar", 0.0),
            voltage_v=values.get("voltage_v"),
            current_a=values.get("current_a"),
            frequency_hz=values.get("frequency_hz"),
            soc_percent=values.get("soc_percent"),
            temperature_c=values.get("temperature_c"),
            status=DERStatus.ONLINE,
        )

    async def write_command(self, command: ControlCommand) -> bool:
        """Write a power setpoint to the device via Modbus registers."""
        if not self._connected or self._client is None:
            raise OSError("Modbus adapter is not connected")

        try:
            if command.setpoint_kw is not None:
                # Write setpoint to register 100 (configurable)
                target_register = int(self.config.get("setpoint_register", 100))
                raw_value = int(command.setpoint_kw / 0.1)  # scale factor
                result = await self._client.write_register(
                    address=target_register,
                    value=raw_value,
                    slave=self._unit_id,
                )
                if result.isError():
                    self.logger.error("Modbus write error: %s", result)
                    return False
                self.logger.info(
                    "Modbus command sent: setpoint_kw=%.2f to register %d",
                    command.setpoint_kw,
                    target_register,
                )
                return True
            self.logger.warning("No setpoint_kw in command; nothing written")
            return False
        except Exception as exc:
            self.logger.error("Modbus write exception: %s", exc)
            return False

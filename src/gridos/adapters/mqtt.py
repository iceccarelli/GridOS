"""
MQTT protocol adapter for GridOS.

Subscribes to device telemetry topics and publishes control commands using
``paho-mqtt`` with an asyncio wrapper.  Messages are expected in JSON format
matching the :class:`DERTelemetry` schema.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from gridos.adapters.base import BaseAdapter
from gridos.models.common import ControlCommand, DERStatus, DERTelemetry

logger = logging.getLogger(__name__)


class MQTTAdapter(BaseAdapter):
    """Async MQTT adapter using ``paho-mqtt``.

    Parameters
    ----------
    device_id:
        Unique device identifier.
    config:
        Must contain ``broker_host``.  Optional keys: ``broker_port``
        (default 1883), ``username``, ``password``, ``topic_prefix``
        (default ``gridos/``), ``qos`` (default 1).
    """

    def __init__(self, device_id: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(device_id, config)
        self._broker_host: str = self.config.get("broker_host", "localhost")
        self._broker_port: int = int(self.config.get("broker_port", 1883))
        self._username: str = self.config.get("username", "")
        self._password: str = self.config.get("password", "")
        self._topic_prefix: str = self.config.get("topic_prefix", "gridos/")
        self._qos: int = int(self.config.get("qos", 1))
        self._client: Any = None
        self._latest_telemetry: DERTelemetry | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._on_telemetry_callback: Callable[[DERTelemetry], None] | None = None

    @property
    def protocol_name(self) -> str:
        return "mqtt"

    @property
    def telemetry_topic(self) -> str:
        """MQTT topic for this device's telemetry."""
        return f"{self._topic_prefix}telemetry/{self.device_id}"

    @property
    def command_topic(self) -> str:
        """MQTT topic for this device's commands."""
        return f"{self._topic_prefix}command/{self.device_id}"

    def set_telemetry_callback(self, callback: Callable[[DERTelemetry], None]) -> None:
        """Register a callback invoked on every new telemetry message."""
        self._on_telemetry_callback = callback

    async def connect(self) -> None:
        """Connect to the MQTT broker and subscribe to the telemetry topic."""
        try:
            import paho.mqtt.client as mqtt

            self._loop = asyncio.get_running_loop()
            self._client = mqtt.Client(
                client_id=f"gridos-{self.device_id}",
                protocol=mqtt.MQTTv5,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            )

            if self._username:
                self._client.username_pw_set(self._username, self._password)

            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message

            self._client.connect_async(
                self._broker_host, self._broker_port, keepalive=60
            )
            self._client.loop_start()
            self._connected = True
            self.logger.info(
                "MQTT connecting to %s:%d", self._broker_host, self._broker_port
            )
        except ImportError as err:
            raise ImportError(
                "paho-mqtt is required for the MQTT adapter. "
                "Install it with: pip install paho-mqtt"
            ) from err
        except Exception as exc:
            self._connected = False
            self.logger.error("MQTT connection error: %s", exc)
            raise ConnectionError(str(exc)) from exc

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            self.logger.info("MQTT disconnected", extra={"device_id": self.device_id})

    # ── Paho callbacks (run in the network thread) ───────────────────────

    def _on_connect(
        self, client: Any, userdata: Any, flags: Any, rc: Any, properties: Any = None
    ) -> None:
        """Subscribe to the device telemetry topic on successful connect."""
        client.subscribe(self.telemetry_topic, qos=self._qos)
        self.logger.info("MQTT subscribed to %s", self.telemetry_topic)

    def _on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        """Parse incoming JSON telemetry and store it."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            telemetry = DERTelemetry(
                device_id=self.device_id,
                timestamp=datetime.fromisoformat(
                    payload.get("timestamp", datetime.utcnow().isoformat())
                ),
                power_kw=float(payload.get("power_kw", 0.0)),
                reactive_power_kvar=float(payload.get("reactive_power_kvar", 0.0)),
                voltage_v=payload.get("voltage_v"),
                current_a=payload.get("current_a"),
                frequency_hz=payload.get("frequency_hz"),
                soc_percent=payload.get("soc_percent"),
                temperature_c=payload.get("temperature_c"),
                status=DERStatus(payload.get("status", "online")),
            )
            self._latest_telemetry = telemetry

            if self._on_telemetry_callback is not None:
                self._on_telemetry_callback(telemetry)

        except Exception as exc:
            self.logger.warning("Failed to parse MQTT message: %s", exc)

    # ── Public API ───────────────────────────────────────────────────────

    async def read_telemetry(self) -> DERTelemetry:
        """Return the most recently received telemetry.

        If no message has been received yet, returns a zero-valued snapshot.
        """
        if self._latest_telemetry is not None:
            return self._latest_telemetry

        self.logger.debug("No MQTT telemetry received yet for %s", self.device_id)
        return DERTelemetry(
            device_id=self.device_id,
            timestamp=datetime.utcnow(),
            power_kw=0.0,
            status=DERStatus.UNKNOWN,
        )

    async def write_command(self, command: ControlCommand) -> bool:
        """Publish a control command to the device's command topic."""
        if self._client is None:
            raise OSError("MQTT adapter is not connected")

        try:
            payload = command.model_dump_json()
            info = self._client.publish(self.command_topic, payload, qos=self._qos)
            info.wait_for_publish(timeout=5)
            self.logger.info("MQTT command published to %s", self.command_topic)
            return True
        except Exception as exc:
            self.logger.error("MQTT publish error: %s", exc)
            return False

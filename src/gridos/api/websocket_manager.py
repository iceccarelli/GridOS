"""
WebSocket connection manager for GridOS.

The reduced launch path keeps WebSocket support intentionally small. Clients can
subscribe to one or more device IDs, or connect without filters to receive all
published telemetry events.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from gridos.models.common import DERTelemetry

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manage live telemetry subscribers for the lightweight launch path."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._subscriptions: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(
        self,
        websocket: WebSocket,
        device_ids: list[str] | None = None,
    ) -> None:
        """Accept a WebSocket connection and optionally subscribe it to devices."""
        await websocket.accept()
        self._connections.add(websocket)

        if device_ids:
            for device_id in {device_id.strip() for device_id in device_ids if device_id.strip()}:
                self._subscriptions[device_id].add(websocket)

        logger.info(
            "WebSocket connected: total=%d, subscribed_devices=%s",
            len(self._connections),
            sorted({device_id for device_id, sockets in self._subscriptions.items() if websocket in sockets}) or "all",
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from all tracking structures."""
        self._connections.discard(websocket)

        empty_keys: list[str] = []
        for device_id, sockets in self._subscriptions.items():
            sockets.discard(websocket)
            if not sockets:
                empty_keys.append(device_id)

        for device_id in empty_keys:
            del self._subscriptions[device_id]

        logger.info("WebSocket disconnected: total=%d", len(self._connections))

    async def publish_telemetry(self, telemetry: DERTelemetry) -> None:
        """Publish a telemetry event to matching subscribers and broadcast clients."""
        payload = {
            "type": "telemetry",
            "device_id": telemetry.device_id,
            "data": telemetry.model_dump(mode="json"),
        }
        await self._send_payload(payload, device_id=telemetry.device_id)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all active WebSocket clients."""
        await self._send_payload(message)

    async def send_to_device_subscribers(self, device_id: str, message: dict[str, Any]) -> None:
        """Backwards-compatible helper for device-targeted messages."""
        await self._send_payload(message, device_id=device_id)

    async def _send_payload(self, payload: dict[str, Any], device_id: str | None = None) -> None:
        message = json.dumps(payload, default=str)
        disconnected: list[WebSocket] = []

        if device_id is None:
            targets = set(self._connections)
        else:
            explicitly_subscribed = set(self._subscriptions.get(device_id, set()))
            any_subscription = set().union(*self._subscriptions.values()) if self._subscriptions else set()
            broadcast_clients = self._connections - any_subscription
            targets = explicitly_subscribed | broadcast_clients

        for websocket in targets:
            try:
                await websocket.send_text(message)
            except Exception as exc:
                logger.warning("WebSocket send failed: %s", exc)
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)

    @property
    def active_connections(self) -> int:
        """Return the number of active WebSocket connections."""
        return len(self._connections)


ws_manager = WebSocketManager()

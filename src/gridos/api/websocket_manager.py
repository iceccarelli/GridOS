"""
WebSocket connection manager for GridOS.

Manages WebSocket connections for live telemetry streaming.  Clients
can subscribe to specific device IDs or receive all telemetry.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts telemetry.

    Supports per-device subscriptions and broadcast-to-all.
    """

    def __init__(self) -> None:
        # All active connections
        self._connections: list[WebSocket] = []
        # device_id → set of subscribed connections
        self._subscriptions: dict[str, set[WebSocket]] = {}

    async def connect(
        self, websocket: WebSocket, device_ids: list[str] | None = None
    ) -> None:
        """Accept a WebSocket connection and register subscriptions.

        Parameters
        ----------
        websocket:
            The WebSocket connection to accept.
        device_ids:
            Optional list of device IDs to subscribe to.  If ``None``,
            the client receives all telemetry.
        """
        await websocket.accept()
        self._connections.append(websocket)

        if device_ids:
            for did in device_ids:
                if did not in self._subscriptions:
                    self._subscriptions[did] = set()
                self._subscriptions[did].add(websocket)

        logger.info(
            "WebSocket connected (total=%d, subscriptions=%s)",
            len(self._connections),
            device_ids or "all",
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self._connections:
            self._connections.remove(websocket)

        for _did, subs in self._subscriptions.items():
            subs.discard(websocket)

        logger.info("WebSocket disconnected (total=%d)", len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        payload = json.dumps(message, default=str)
        disconnected: list[WebSocket] = []

        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    async def send_to_device_subscribers(
        self, device_id: str, message: dict[str, Any]
    ) -> None:
        """Send a message to clients subscribed to a specific device.

        Also sends to clients with no subscriptions (broadcast clients).
        """
        payload = json.dumps(message, default=str)
        disconnected: list[WebSocket] = []

        # Subscribers for this device
        targets = self._subscriptions.get(device_id, set())

        # Also include clients with no specific subscriptions
        subscribed_ws = set()
        for subs in self._subscriptions.values():
            subscribed_ws.update(subs)
        broadcast_clients = set(self._connections) - subscribed_ws

        all_targets = targets | broadcast_clients

        for ws in all_targets:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    @property
    def active_connections(self) -> int:
        """Number of active WebSocket connections."""
        return len(self._connections)


# Singleton instance
ws_manager = WebSocketManager()

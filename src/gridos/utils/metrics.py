"""
Metrics collection utilities for GridOS.

Provides lightweight counters and gauges for monitoring key platform
metrics.  When Prometheus client is available, uses native Prometheus
metrics; otherwise falls back to in-memory counters.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Union

logger = logging.getLogger(__name__)

_PROMETHEUS_AVAILABLE = False

try:
    from prometheus_client import Counter, Gauge, Histogram  # noqa: F401

    _PROMETHEUS_AVAILABLE = True
except ImportError:
    pass


# ── In-Memory Fallback ──────────────────────────────────────────────────────


class _InMemoryCounter:
    """Simple in-memory counter for when Prometheus is not available."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self._values: dict[str, float] = defaultdict(float)

    def labels(self, **kwargs: str) -> _InMemoryCounter:
        # Return self for chaining — labels are ignored in fallback
        return self

    def inc(self, amount: float = 1.0) -> None:
        self._values["default"] += amount

    def observe(self, amount: float) -> None:
        """Histogram-compatible observe method."""
        self._values["default"] += amount

    @property
    def value(self) -> float:
        return self._values["default"]


class _InMemoryGauge:
    """Simple in-memory gauge."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self._value: float = 0.0

    def labels(self, **kwargs: str) -> _InMemoryGauge:
        return self

    def set(self, value: float) -> None:
        self._value = value

    def inc(self, amount: float = 1.0) -> None:
        self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        self._value -= amount

    @property
    def value(self) -> float:
        return self._value


# ── Type Aliases ────────────────────────────────────────────────────────────

CounterLike = Union["Counter", _InMemoryCounter]
GaugeLike = Union["Gauge", _InMemoryGauge]
HistogramLike = Union["Histogram", _InMemoryCounter]


# ── Metrics Registry ────────────────────────────────────────────────────────


class MetricsRegistry:
    """Central metrics registry for GridOS.

    Automatically uses Prometheus client if available, otherwise
    falls back to in-memory counters.
    """

    telemetry_ingested: CounterLike
    commands_dispatched: CounterLike
    active_devices: GaugeLike
    websocket_connections: GaugeLike
    storage_write_duration: HistogramLike
    optimization_runs: CounterLike
    forecast_requests: CounterLike

    def __init__(self) -> None:
        self._use_prometheus = _PROMETHEUS_AVAILABLE

        if self._use_prometheus:
            self.telemetry_ingested = Counter(
                "gridos_telemetry_ingested_total",
                "Total telemetry readings ingested",
                ["device_id"],
            )
            self.commands_dispatched = Counter(
                "gridos_commands_dispatched_total",
                "Total control commands dispatched",
                ["device_id", "status"],
            )
            self.active_devices = Gauge(
                "gridos_active_devices",
                "Number of active DER devices",
            )
            self.websocket_connections = Gauge(
                "gridos_websocket_connections",
                "Number of active WebSocket connections",
            )
            self.storage_write_duration = Histogram(
                "gridos_storage_write_seconds",
                "Storage write latency in seconds",
                ["backend"],
            )
            self.optimization_runs = Counter(
                "gridos_optimization_runs_total",
                "Total optimisation runs",
                ["status"],
            )
            self.forecast_requests = Counter(
                "gridos_forecast_requests_total",
                "Total forecast requests",
                ["model_type"],
            )
            logger.info("Prometheus metrics initialised")
        else:
            self.telemetry_ingested = _InMemoryCounter(
                "telemetry_ingested", "Total telemetry readings"
            )
            self.commands_dispatched = _InMemoryCounter(
                "commands_dispatched", "Total commands"
            )
            self.active_devices = _InMemoryGauge("active_devices", "Active devices")
            self.websocket_connections = _InMemoryGauge(
                "websocket_connections", "WebSocket connections"
            )
            self.storage_write_duration = _InMemoryCounter(
                "storage_write_duration", "Storage write latency"
            )
            self.optimization_runs = _InMemoryCounter(
                "optimization_runs", "Optimisation runs"
            )
            self.forecast_requests = _InMemoryCounter(
                "forecast_requests", "Forecast requests"
            )
            logger.info("In-memory metrics initialised (Prometheus not available)")

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of current metric values (for health endpoints)."""
        if self._use_prometheus:
            return {"backend": "prometheus", "note": "Use /metrics endpoint"}
        return {
            "backend": "in_memory",
            "active_devices": getattr(self.active_devices, "value", 0),
            "websocket_connections": getattr(self.websocket_connections, "value", 0),
        }


# Singleton
metrics = MetricsRegistry()

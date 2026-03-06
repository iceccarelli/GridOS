"""
GridOS time-series storage backends.

Provides pluggable storage interfaces for persisting and querying DER
telemetry data.  Supported backends include InfluxDB 2.x and TimescaleDB.
"""

from gridos.storage.base import StorageBackend

__all__ = ["StorageBackend"]

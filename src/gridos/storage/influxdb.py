"""
InfluxDB 2.x storage backend for GridOS.

Uses the ``influxdb-client`` async API to write and query DER telemetry
data.  Configuration is read from environment variables or passed via
the ``config`` dictionary.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from gridos.models.common import DERStatus, DERTelemetry
from gridos.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class InfluxDBBackend(StorageBackend):
    """Async InfluxDB 2.x storage backend.

    Parameters
    ----------
    config:
        Optional overrides.  Falls back to environment variables:
        ``INFLUXDB_URL``, ``INFLUXDB_TOKEN``, ``INFLUXDB_ORG``,
        ``INFLUXDB_BUCKET``.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._url: str = self.config.get(
            "url", os.getenv("INFLUXDB_URL", "http://localhost:8086")
        )
        self._token: str = self.config.get("token", os.getenv("INFLUXDB_TOKEN", ""))
        self._org: str = self.config.get("org", os.getenv("INFLUXDB_ORG", "gridos"))
        self._bucket: str = self.config.get(
            "bucket", os.getenv("INFLUXDB_BUCKET", "telemetry")
        )
        self._client: Any = None
        self._write_api: Any = None
        self._query_api: Any = None

    @property
    def backend_name(self) -> str:
        return "influxdb"

    async def connect(self) -> None:
        """Create the InfluxDB async client."""
        try:
            from influxdb_client import InfluxDBClient
            from influxdb_client.client.write_api import ASYNCHRONOUS

            self._client = InfluxDBClient(
                url=self._url,
                token=self._token,
                org=self._org,
            )
            self._write_api = self._client.write_api(write_options=ASYNCHRONOUS)
            self._query_api = self._client.query_api()
            self._connected = True
            self.logger.info("InfluxDB connected to %s", self._url)
        except ImportError as err:
            raise ImportError(
                "influxdb-client is required. Install with: pip install influxdb-client[async]"
            ) from err
        except Exception as exc:
            self._connected = False
            self.logger.error("InfluxDB connection error: %s", exc)
            raise

    async def disconnect(self) -> None:
        """Close the InfluxDB client."""
        if self._client is not None:
            self._client.close()
            self._connected = False
            self.logger.info("InfluxDB disconnected")

    # ── Write ────────────────────────────────────────────────────────────

    def _telemetry_to_point(self, t: DERTelemetry) -> Any:
        """Convert a ``DERTelemetry`` to an InfluxDB ``Point``."""
        from influxdb_client import Point

        p = (
            Point("der_telemetry")
            .tag("device_id", t.device_id)
            .tag("status", t.status.value)
            .field("power_kw", t.power_kw)
            .field("reactive_power_kvar", t.reactive_power_kvar)
            .time(t.timestamp)
        )
        if t.voltage_v is not None:
            p = p.field("voltage_v", t.voltage_v)
        if t.current_a is not None:
            p = p.field("current_a", t.current_a)
        if t.frequency_hz is not None:
            p = p.field("frequency_hz", t.frequency_hz)
        if t.power_factor is not None:
            p = p.field("power_factor", t.power_factor)
        if t.energy_kwh is not None:
            p = p.field("energy_kwh", t.energy_kwh)
        if t.soc_percent is not None:
            p = p.field("soc_percent", t.soc_percent)
        if t.temperature_c is not None:
            p = p.field("temperature_c", t.temperature_c)
        if t.irradiance_w_m2 is not None:
            p = p.field("irradiance_w_m2", t.irradiance_w_m2)
        return p

    async def write_point(self, telemetry: DERTelemetry) -> None:
        if self._write_api is None:
            raise OSError("InfluxDB is not connected")
        point = self._telemetry_to_point(telemetry)
        self._write_api.write(bucket=self._bucket, record=point)
        self.logger.debug("InfluxDB wrote point for %s", telemetry.device_id)

    async def write_points(self, telemetry_list: list[DERTelemetry]) -> None:
        if self._write_api is None:
            raise OSError("InfluxDB is not connected")
        points = [self._telemetry_to_point(t) for t in telemetry_list]
        self._write_api.write(bucket=self._bucket, record=points)
        self.logger.debug("InfluxDB wrote %d points", len(points))

    # ── Read ─────────────────────────────────────────────────────────────

    async def query_range(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[DERTelemetry]:
        if self._query_api is None:
            raise OSError("InfluxDB is not connected")

        flux = (
            f'from(bucket: "{self._bucket}")'
            f"  |> range(start: {start.isoformat()}Z, stop: {end.isoformat()}Z)"
            f'  |> filter(fn: (r) => r["_measurement"] == "der_telemetry")'
            f'  |> filter(fn: (r) => r["device_id"] == "{device_id}")'
            f'  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'
            f'  |> sort(columns: ["_time"])'
            f"  |> limit(n: {limit})"
        )

        tables = self._query_api.query(flux, org=self._org)
        results: list[DERTelemetry] = []
        for table in tables:
            for record in table.records:
                vals = record.values
                results.append(
                    DERTelemetry(
                        device_id=device_id,
                        timestamp=vals.get("_time", datetime.utcnow()),
                        power_kw=vals.get("power_kw", 0.0),
                        reactive_power_kvar=vals.get("reactive_power_kvar", 0.0),
                        voltage_v=vals.get("voltage_v"),
                        current_a=vals.get("current_a"),
                        frequency_hz=vals.get("frequency_hz"),
                        soc_percent=vals.get("soc_percent"),
                        temperature_c=vals.get("temperature_c"),
                        status=DERStatus(vals.get("status", "online")),
                    )
                )
        return results

    async def get_latest(self, device_id: str) -> DERTelemetry | None:
        if self._query_api is None:
            raise OSError("InfluxDB is not connected")

        flux = (
            f'from(bucket: "{self._bucket}")'
            f"  |> range(start: -1h)"
            f'  |> filter(fn: (r) => r["_measurement"] == "der_telemetry")'
            f'  |> filter(fn: (r) => r["device_id"] == "{device_id}")'
            f'  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'
            f'  |> sort(columns: ["_time"], desc: true)'
            f"  |> limit(n: 1)"
        )

        tables = self._query_api.query(flux, org=self._org)
        for table in tables:
            for record in table.records:
                vals = record.values
                return DERTelemetry(
                    device_id=device_id,
                    timestamp=vals.get("_time", datetime.utcnow()),
                    power_kw=vals.get("power_kw", 0.0),
                    reactive_power_kvar=vals.get("reactive_power_kvar", 0.0),
                    voltage_v=vals.get("voltage_v"),
                    current_a=vals.get("current_a"),
                    frequency_hz=vals.get("frequency_hz"),
                    soc_percent=vals.get("soc_percent"),
                    temperature_c=vals.get("temperature_c"),
                    status=DERStatus(vals.get("status", "online")),
                )
        return None

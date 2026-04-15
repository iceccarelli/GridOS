"""Optional InfluxDB backend for GridOS.

This backend is not part of the default launch path. The repository runs
end-to-end with the in-memory backend alone. Use this module only when an
external InfluxDB 2.x service is available and the required client dependency
has been installed.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from gridos.models.common import DERStatus, DERTelemetry
from gridos.storage.base import StorageBackend


class InfluxDBBackend(StorageBackend):
    """Optional telemetry backend backed by InfluxDB 2.x."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.config = config or {}
        self._url = self.config.get("url", "http://localhost:8086")
        self._token = self.config.get("token", "")
        self._org = self.config.get("org", "gridos")
        self._bucket = self.config.get("bucket", "telemetry")
        self._client: Any = None
        self._write_api: Any = None
        self._query_api: Any = None

    @property
    def backend_name(self) -> str:
        return "influxdb"

    async def connect(self) -> None:
        try:
            from influxdb_client import InfluxDBClient
        except ImportError as exc:
            raise RuntimeError(
                "Optional InfluxDB support requires the 'influxdb-client' package. "
                "Use the default in-memory backend for a zero-dependency launch."
            ) from exc

        if not self._token:
            raise RuntimeError("InfluxDB token is required when using the optional InfluxDB backend")

        self._client = InfluxDBClient(url=self._url, token=self._token, org=self._org)
        self._write_api = self._client.write_api()
        self._query_api = self._client.query_api()
        self._connected = True

    async def disconnect(self) -> None:
        if self._client is not None:
            await asyncio.to_thread(self._client.close)
        self._client = None
        self._write_api = None
        self._query_api = None
        self._connected = False

    async def write_point(self, telemetry: DERTelemetry) -> None:
        self._require_connection()
        point = await asyncio.to_thread(self._telemetry_to_point, telemetry)
        await asyncio.to_thread(self._write_api.write, self._bucket, self._org, point)

    async def write_points(self, telemetry_list: list[DERTelemetry]) -> None:
        self._require_connection()
        points = await asyncio.to_thread(
            lambda: [self._telemetry_to_point(item) for item in telemetry_list]
        )
        await asyncio.to_thread(self._write_api.write, self._bucket, self._org, points)

    async def query_range(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[DERTelemetry]:
        self._require_connection()
        flux = self._build_range_query(device_id=device_id, start=start, end=end, limit=limit)
        tables = await asyncio.to_thread(self._query_api.query, flux, self._org)
        return self._tables_to_telemetry(device_id=device_id, tables=tables)

    async def get_latest(self, device_id: str) -> DERTelemetry | None:
        self._require_connection()
        flux = self._build_latest_query(device_id=device_id)
        tables = await asyncio.to_thread(self._query_api.query, flux, self._org)
        results = self._tables_to_telemetry(device_id=device_id, tables=tables)
        return results[0] if results else None

    def _telemetry_to_point(self, telemetry: DERTelemetry) -> Any:
        from influxdb_client import Point

        point = (
            Point("der_telemetry")
            .tag("device_id", telemetry.device_id)
            .tag("status", telemetry.status.value)
            .field("power_kw", telemetry.power_kw)
            .field("reactive_power_kvar", telemetry.reactive_power_kvar)
            .time(telemetry.timestamp)
        )

        optional_fields = {
            "voltage_v": telemetry.voltage_v,
            "current_a": telemetry.current_a,
            "frequency_hz": telemetry.frequency_hz,
            "power_factor": telemetry.power_factor,
            "energy_kwh": telemetry.energy_kwh,
            "soc_percent": telemetry.soc_percent,
            "temperature_c": telemetry.temperature_c,
            "irradiance_w_m2": telemetry.irradiance_w_m2,
        }
        for field_name, value in optional_fields.items():
            if value is not None:
                point = point.field(field_name, value)
        return point

    def _build_range_query(self, device_id: str, start: datetime, end: datetime, limit: int) -> str:
        start_value = _to_utc_iso(start)
        end_value = _to_utc_iso(end)
        return (
            f'from(bucket: "{self._bucket}") '
            f'|> range(start: time(v: "{start_value}"), stop: time(v: "{end_value}")) '
            f'|> filter(fn: (r) => r["_measurement"] == "der_telemetry") '
            f'|> filter(fn: (r) => r["device_id"] == "{device_id}") '
            '|> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value") '
            '|> sort(columns:["_time"], desc: false) '
            f'|> limit(n: {limit})'
        )

    def _build_latest_query(self, device_id: str) -> str:
        return (
            f'from(bucket: "{self._bucket}") '
            '|> range(start: -30d) '
            f'|> filter(fn: (r) => r["_measurement"] == "der_telemetry") '
            f'|> filter(fn: (r) => r["device_id"] == "{device_id}") '
            '|> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value") '
            '|> sort(columns:["_time"], desc: true) '
            '|> limit(n: 1)'
        )

    def _tables_to_telemetry(self, device_id: str, tables: Any) -> list[DERTelemetry]:
        results: list[DERTelemetry] = []
        for table in tables:
            for record in getattr(table, "records", []):
                values = getattr(record, "values", {})
                timestamp = values.get("_time") or datetime.now(timezone.utc)
                results.append(
                    DERTelemetry(
                        device_id=device_id,
                        timestamp=timestamp,
                        power_kw=float(values.get("power_kw", 0.0)),
                        reactive_power_kvar=float(values.get("reactive_power_kvar", 0.0)),
                        voltage_v=_optional_float(values.get("voltage_v")),
                        current_a=_optional_float(values.get("current_a")),
                        frequency_hz=_optional_float(values.get("frequency_hz")),
                        power_factor=_optional_float(values.get("power_factor")),
                        energy_kwh=_optional_float(values.get("energy_kwh")),
                        soc_percent=_optional_float(values.get("soc_percent")),
                        temperature_c=_optional_float(values.get("temperature_c")),
                        irradiance_w_m2=_optional_float(values.get("irradiance_w_m2")),
                        status=DERStatus(values.get("status", "online")),
                    )
                )
        return results


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")

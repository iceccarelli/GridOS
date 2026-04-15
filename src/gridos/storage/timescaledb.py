"""Optional TimescaleDB backend for GridOS.

This backend is intentionally secondary to the launch-ready in-memory backend.
Use it only when a PostgreSQL or TimescaleDB service is available and you want
telemetry persistence beyond the default local-first runtime.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gridos.models.common import DERStatus, DERTelemetry
from gridos.storage.base import StorageBackend

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS der_telemetry (
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT NOT NULL,
    power_kw DOUBLE PRECISION NOT NULL,
    reactive_power_kvar DOUBLE PRECISION NOT NULL DEFAULT 0,
    voltage_v DOUBLE PRECISION,
    current_a DOUBLE PRECISION,
    frequency_hz DOUBLE PRECISION,
    power_factor DOUBLE PRECISION,
    energy_kwh DOUBLE PRECISION,
    soc_percent DOUBLE PRECISION,
    temperature_c DOUBLE PRECISION,
    irradiance_w_m2 DOUBLE PRECISION,
    status TEXT NOT NULL DEFAULT 'online'
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_der_telemetry_device_time
ON der_telemetry (device_id, time DESC);
"""

CREATE_HYPERTABLE_SQL = """
SELECT create_hypertable('der_telemetry', 'time', if_not_exists => TRUE);
"""

INSERT_SQL = """
INSERT INTO der_telemetry (
    time,
    device_id,
    power_kw,
    reactive_power_kvar,
    voltage_v,
    current_a,
    frequency_hz,
    power_factor,
    energy_kwh,
    soc_percent,
    temperature_c,
    irradiance_w_m2,
    status
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
);
"""

QUERY_RANGE_SQL = """
SELECT
    time,
    device_id,
    power_kw,
    reactive_power_kvar,
    voltage_v,
    current_a,
    frequency_hz,
    power_factor,
    energy_kwh,
    soc_percent,
    temperature_c,
    irradiance_w_m2,
    status
FROM der_telemetry
WHERE device_id = $1
  AND time >= $2
  AND time <= $3
ORDER BY time ASC
LIMIT $4;
"""

QUERY_LATEST_SQL = """
SELECT
    time,
    device_id,
    power_kw,
    reactive_power_kvar,
    voltage_v,
    current_a,
    frequency_hz,
    power_factor,
    energy_kwh,
    soc_percent,
    temperature_c,
    irradiance_w_m2,
    status
FROM der_telemetry
WHERE device_id = $1
ORDER BY time DESC
LIMIT 1;
"""


class TimescaleDBBackend(StorageBackend):
    """Optional telemetry backend backed by PostgreSQL or TimescaleDB."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.config = config or {}
        self._dsn = self.config.get("dsn", "postgresql://gridos:gridos@localhost:5432/gridos")
        self._pool: Any = None

    @property
    def backend_name(self) -> str:
        return "timescaledb"

    async def connect(self) -> None:
        try:
            import asyncpg
        except ImportError as exc:
            raise RuntimeError(
                "Optional TimescaleDB support requires the 'asyncpg' package. "
                "Use the default in-memory backend for a zero-dependency launch."
            ) from exc

        self._pool = await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=5)
        async with self._pool.acquire() as connection:
            await connection.execute(CREATE_TABLE_SQL)
            await connection.execute(CREATE_INDEX_SQL)
            try:
                await connection.execute(CREATE_HYPERTABLE_SQL)
            except Exception:
                # A plain PostgreSQL database is still acceptable for this optional path.
                pass
        self._connected = True

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
        self._pool = None
        self._connected = False

    async def write_point(self, telemetry: DERTelemetry) -> None:
        self._require_connection()
        async with self._pool.acquire() as connection:
            await connection.execute(INSERT_SQL, *self._telemetry_to_row(telemetry))

    async def write_points(self, telemetry_list: list[DERTelemetry]) -> None:
        self._require_connection()
        rows = [self._telemetry_to_row(item) for item in telemetry_list]
        async with self._pool.acquire() as connection:
            await connection.executemany(INSERT_SQL, rows)

    async def query_range(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[DERTelemetry]:
        self._require_connection()
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                QUERY_RANGE_SQL,
                device_id,
                _normalize_timestamp(start),
                _normalize_timestamp(end),
                limit,
            )
        return [self._row_to_telemetry(row) for row in rows]

    async def get_latest(self, device_id: str) -> DERTelemetry | None:
        self._require_connection()
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(QUERY_LATEST_SQL, device_id)
        if row is None:
            return None
        return self._row_to_telemetry(row)

    def _telemetry_to_row(self, telemetry: DERTelemetry) -> tuple[Any, ...]:
        return (
            _normalize_timestamp(telemetry.timestamp),
            telemetry.device_id,
            telemetry.power_kw,
            telemetry.reactive_power_kvar,
            telemetry.voltage_v,
            telemetry.current_a,
            telemetry.frequency_hz,
            telemetry.power_factor,
            telemetry.energy_kwh,
            telemetry.soc_percent,
            telemetry.temperature_c,
            telemetry.irradiance_w_m2,
            telemetry.status.value,
        )

    def _row_to_telemetry(self, row: Any) -> DERTelemetry:
        return DERTelemetry(
            device_id=row["device_id"],
            timestamp=row["time"],
            power_kw=row["power_kw"],
            reactive_power_kvar=row["reactive_power_kvar"],
            voltage_v=row["voltage_v"],
            current_a=row["current_a"],
            frequency_hz=row["frequency_hz"],
            power_factor=row["power_factor"],
            energy_kwh=row["energy_kwh"],
            soc_percent=row["soc_percent"],
            temperature_c=row["temperature_c"],
            irradiance_w_m2=row["irradiance_w_m2"],
            status=DERStatus(row["status"]),
        )


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

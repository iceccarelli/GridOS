"""
TimescaleDB storage backend for GridOS.

Uses ``asyncpg`` for high-performance async PostgreSQL access with
TimescaleDB hypertables.  The schema is auto-created on first connect
if the target table does not exist.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from gridos.models.common import DERStatus, DERTelemetry
from gridos.storage.base import StorageBackend

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS der_telemetry (
    time              TIMESTAMPTZ      NOT NULL,
    device_id         TEXT             NOT NULL,
    power_kw          DOUBLE PRECISION NOT NULL DEFAULT 0,
    reactive_power_kvar DOUBLE PRECISION NOT NULL DEFAULT 0,
    voltage_v         DOUBLE PRECISION,
    current_a         DOUBLE PRECISION,
    frequency_hz      DOUBLE PRECISION,
    power_factor      DOUBLE PRECISION,
    energy_kwh        DOUBLE PRECISION,
    soc_percent       DOUBLE PRECISION,
    temperature_c     DOUBLE PRECISION,
    irradiance_w_m2   DOUBLE PRECISION,
    status            TEXT             NOT NULL DEFAULT 'online'
);
"""

CREATE_HYPERTABLE_SQL = """
SELECT create_hypertable('der_telemetry', 'time', if_not_exists => TRUE);
"""

INSERT_SQL = """
INSERT INTO der_telemetry (
    time, device_id, power_kw, reactive_power_kvar,
    voltage_v, current_a, frequency_hz, power_factor,
    energy_kwh, soc_percent, temperature_c, irradiance_w_m2, status
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13);
"""

QUERY_RANGE_SQL = """
SELECT time, device_id, power_kw, reactive_power_kvar,
       voltage_v, current_a, frequency_hz, power_factor,
       energy_kwh, soc_percent, temperature_c, irradiance_w_m2, status
FROM der_telemetry
WHERE device_id = $1 AND time >= $2 AND time <= $3
ORDER BY time ASC
LIMIT $4;
"""

QUERY_LATEST_SQL = """
SELECT time, device_id, power_kw, reactive_power_kvar,
       voltage_v, current_a, frequency_hz, power_factor,
       energy_kwh, soc_percent, temperature_c, irradiance_w_m2, status
FROM der_telemetry
WHERE device_id = $1
ORDER BY time DESC
LIMIT 1;
"""


class TimescaleDBBackend(StorageBackend):
    """Async TimescaleDB storage backend.

    Parameters
    ----------
    config:
        Optional overrides.  Falls back to the ``TIMESCALEDB_DSN``
        environment variable.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._dsn: str = self.config.get(
            "dsn",
            os.getenv(
                "TIMESCALEDB_DSN", "postgresql://gridos:gridos@localhost:5432/gridos"
            ),
        )
        self._pool: Any = None

    @property
    def backend_name(self) -> str:
        return "timescaledb"

    async def connect(self) -> None:
        """Create a connection pool and ensure the schema exists."""
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(
                dsn=self._dsn, min_size=2, max_size=10
            )
            async with self._pool.acquire() as conn:
                await conn.execute(CREATE_TABLE_SQL)
                try:
                    await conn.execute(CREATE_HYPERTABLE_SQL)
                except Exception:
                    # Hypertable may already exist or TimescaleDB extension
                    # might not be installed (plain PostgreSQL fallback).
                    self.logger.warning(
                        "Could not create hypertable — TimescaleDB extension may "
                        "not be installed.  Falling back to plain PostgreSQL table."
                    )
            self._connected = True
            self.logger.info("TimescaleDB connected")
        except ImportError as err:
            raise ImportError(
                "asyncpg is required. Install with: pip install asyncpg"
            ) from err
        except Exception as exc:
            self._connected = False
            self.logger.error("TimescaleDB connection error: %s", exc)
            raise

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._connected = False
            self.logger.info("TimescaleDB disconnected")

    # ── Write ────────────────────────────────────────────────────────────

    async def write_point(self, telemetry: DERTelemetry) -> None:
        if self._pool is None:
            raise OSError("TimescaleDB is not connected")
        async with self._pool.acquire() as conn:
            await conn.execute(
                INSERT_SQL,
                telemetry.timestamp,
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

    async def write_points(self, telemetry_list: list[DERTelemetry]) -> None:
        if self._pool is None:
            raise OSError("TimescaleDB is not connected")
        rows = [
            (
                t.timestamp,
                t.device_id,
                t.power_kw,
                t.reactive_power_kvar,
                t.voltage_v,
                t.current_a,
                t.frequency_hz,
                t.power_factor,
                t.energy_kwh,
                t.soc_percent,
                t.temperature_c,
                t.irradiance_w_m2,
                t.status.value,
            )
            for t in telemetry_list
        ]
        async with self._pool.acquire() as conn:
            await conn.executemany(INSERT_SQL, rows)
        self.logger.debug("TimescaleDB wrote %d points", len(rows))

    # ── Read ─────────────────────────────────────────────────────────────

    def _row_to_telemetry(self, row: Any) -> DERTelemetry:
        """Convert a database row to a ``DERTelemetry`` instance."""
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

    async def query_range(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[DERTelemetry]:
        if self._pool is None:
            raise OSError("TimescaleDB is not connected")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(QUERY_RANGE_SQL, device_id, start, end, limit)
        return [self._row_to_telemetry(r) for r in rows]

    async def get_latest(self, device_id: str) -> DERTelemetry | None:
        if self._pool is None:
            raise OSError("TimescaleDB is not connected")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(QUERY_LATEST_SQL, device_id)
        if row is None:
            return None
        return self._row_to_telemetry(row)

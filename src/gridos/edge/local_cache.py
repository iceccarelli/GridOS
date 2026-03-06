"""
SQLite-based local cache for GridOS edge devices.

Provides store-and-forward functionality for telemetry data when the
cloud connection is unavailable.  Cached readings are synced to the
central storage backend when connectivity is restored.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from gridos.models.common import DERTelemetry

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS telemetry_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    payload     TEXT    NOT NULL,
    synced      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_telemetry_synced ON telemetry_cache(synced);
"""


class LocalCache:
    """SQLite store-and-forward cache for edge deployments.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.
    max_cache_size:
        Maximum number of unsynced records to retain.
    """

    def __init__(
        self,
        db_path: str = "./edge_cache.db",
        max_cache_size: int = 100_000,
    ) -> None:
        self.db_path = Path(db_path)
        self.max_cache_size = max_cache_size
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        """Open the SQLite database and ensure the schema exists."""
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(CREATE_TABLE_SQL)
        self._conn.execute(CREATE_INDEX_SQL)
        self._conn.commit()
        logger.info("Edge cache opened: %s", self.db_path)

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.info("Edge cache closed")

    def _ensure_open(self) -> sqlite3.Connection:
        if self._conn is None:
            self.open()
        if self._conn is None:  # pragma: no cover
            raise RuntimeError("Failed to open edge cache database")
        return self._conn

    # ── Write ────────────────────────────────────────────────────────

    def store(self, telemetry: DERTelemetry) -> None:
        """Cache a telemetry reading locally.

        Parameters
        ----------
        telemetry:
            The telemetry reading to cache.
        """
        conn = self._ensure_open()
        payload = telemetry.model_dump_json()
        conn.execute(
            "INSERT INTO telemetry_cache (device_id, timestamp, payload) VALUES (?, ?, ?)",
            (telemetry.device_id, telemetry.timestamp.isoformat(), payload),
        )
        conn.commit()
        logger.debug("Cached telemetry for %s", telemetry.device_id)

        # Enforce max cache size
        self._prune()

    def store_batch(self, readings: list[DERTelemetry]) -> None:
        """Cache multiple telemetry readings."""
        conn = self._ensure_open()
        rows = [
            (t.device_id, t.timestamp.isoformat(), t.model_dump_json())
            for t in readings
        ]
        conn.executemany(
            "INSERT INTO telemetry_cache (device_id, timestamp, payload) VALUES (?, ?, ?)",
            rows,
        )
        conn.commit()
        logger.debug("Cached %d telemetry readings", len(rows))
        self._prune()

    # ── Read ─────────────────────────────────────────────────────────

    def get_unsynced(self, limit: int = 1000) -> list[DERTelemetry]:
        """Retrieve unsynced telemetry readings.

        Parameters
        ----------
        limit:
            Maximum number of records to return.

        Returns
        -------
        list[DERTelemetry]
            Unsynced telemetry readings ordered by timestamp.
        """
        conn = self._ensure_open()
        cursor = conn.execute(
            "SELECT id, payload FROM telemetry_cache WHERE synced = 0 "
            "ORDER BY timestamp ASC LIMIT ?",
            (limit,),
        )
        results: list[DERTelemetry] = []
        for row in cursor:
            try:
                data = json.loads(row["payload"])
                results.append(DERTelemetry(**data))
            except Exception as exc:
                logger.warning("Failed to parse cached record %d: %s", row["id"], exc)
        return results

    def get_unsynced_count(self) -> int:
        """Return the number of unsynced records."""
        conn = self._ensure_open()
        cursor = conn.execute(
            "SELECT COUNT(*) as cnt FROM telemetry_cache WHERE synced = 0"
        )
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    # ── Sync ─────────────────────────────────────────────────────────

    def mark_synced(
        self, device_id: str | None = None, before: datetime | None = None
    ) -> int:
        """Mark cached records as synced.

        Parameters
        ----------
        device_id:
            If provided, only mark records for this device.
        before:
            If provided, only mark records with timestamp before this.

        Returns
        -------
        int
            Number of records marked as synced.
        """
        conn = self._ensure_open()
        conditions = ["synced = 0"]
        params: list[Any] = []

        if device_id:
            conditions.append("device_id = ?")
            params.append(device_id)
        if before:
            conditions.append("timestamp <= ?")
            params.append(before.isoformat())

        where = " AND ".join(conditions)
        query = "UPDATE telemetry_cache SET synced = 1 WHERE " + where  # nosec B608
        cursor = conn.execute(query, params)
        conn.commit()
        count = cursor.rowcount
        logger.info("Marked %d records as synced", count)
        return count

    def purge_synced(self) -> int:
        """Delete all synced records from the cache.

        Returns
        -------
        int
            Number of records deleted.
        """
        conn = self._ensure_open()
        cursor = conn.execute("DELETE FROM telemetry_cache WHERE synced = 1")
        conn.commit()
        count = cursor.rowcount
        logger.info("Purged %d synced records", count)
        return count

    # ── Maintenance ──────────────────────────────────────────────────

    def _prune(self) -> None:
        """Remove oldest unsynced records if cache exceeds max size."""
        conn = self._ensure_open()
        count = self.get_unsynced_count()
        if count > self.max_cache_size:
            excess = count - self.max_cache_size
            conn.execute(
                "DELETE FROM telemetry_cache WHERE id IN "
                "(SELECT id FROM telemetry_cache WHERE synced = 0 "
                "ORDER BY timestamp ASC LIMIT ?)",
                (excess,),
            )
            conn.commit()
            logger.warning("Pruned %d oldest cached records (cache full)", excess)

    # ── Context Manager ──────────────────────────────────────────────

    def __enter__(self) -> LocalCache:
        self.open()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

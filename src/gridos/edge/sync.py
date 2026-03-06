"""
Edge-to-cloud synchronization for GridOS.

Periodically reads unsynced telemetry from the local SQLite cache and
pushes it to the central storage backend via the REST API.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from gridos.edge.local_cache import LocalCache

logger = logging.getLogger(__name__)


class EdgeSyncer:
    """Synchronises cached telemetry to the GridOS cloud API.

    Parameters
    ----------
    cache:
        The local SQLite cache instance.
    api_base_url:
        Base URL of the GridOS API (e.g. ``http://gridos-api:8000``).
    batch_size:
        Number of records to sync per batch.
    sync_interval_seconds:
        Seconds between sync attempts.
    api_key:
        Optional API key for authentication.
    """

    def __init__(
        self,
        cache: LocalCache,
        api_base_url: str = "http://localhost:8000",
        batch_size: int = 500,
        sync_interval_seconds: float = 60.0,
        api_key: str | None = None,
    ) -> None:
        self.cache = cache
        self.api_base_url = api_base_url.rstrip("/")
        self.batch_size = batch_size
        self.sync_interval_seconds = sync_interval_seconds
        self.api_key = api_key
        self._running = False

    async def sync_once(self) -> dict[str, Any]:
        """Perform a single sync cycle.

        Returns
        -------
        dict
            Summary with ``synced_count`` and ``errors``.
        """
        readings = self.cache.get_unsynced(limit=self.batch_size)
        if not readings:
            return {"synced_count": 0, "errors": 0}

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        synced = 0
        errors = 0

        async with aiohttp.ClientSession(headers=headers) as session:
            # Send as batch
            payload = {"readings": [r.model_dump(mode="json") for r in readings]}
            url = f"{self.api_base_url}/api/v1/telemetry/batch"
            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 201:
                        synced = len(readings)
                        self.cache.mark_synced()
                        logger.info("Synced %d readings to cloud", synced)
                    else:
                        body = await resp.text()
                        logger.error(
                            "Sync batch failed: HTTP %d — %s", resp.status, body
                        )
                        errors = len(readings)
            except Exception as exc:
                logger.error("Sync connection error: %s", exc)
                errors = len(readings)

        return {"synced_count": synced, "errors": errors}

    async def run(self) -> None:
        """Run the sync loop indefinitely."""
        self._running = True
        logger.info(
            "Edge syncer started (interval=%ds, batch=%d)",
            self.sync_interval_seconds,
            self.batch_size,
        )
        while self._running:
            try:
                result = await self.sync_once()
                if result["synced_count"] > 0:
                    logger.info("Sync result: %s", result)
            except Exception as exc:
                logger.error("Sync loop error: %s", exc)
            await asyncio.sleep(self.sync_interval_seconds)

    def stop(self) -> None:
        """Stop the sync loop."""
        self._running = False
        logger.info("Edge syncer stopped")

"""Storage tests for the reduced GridOS launch path."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from gridos.api.dependencies import InMemoryStorageBackend
from gridos.storage.base import StorageBackend


class TestBaseStorage:
    """Validate the abstract storage contract."""

    def test_cannot_instantiate_storage_backend(self) -> None:
        with pytest.raises(TypeError):
            StorageBackend()


class TestInMemoryStorageBackend:
    """Validate the default lightweight storage implementation."""

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self) -> None:
        backend = InMemoryStorageBackend()
        await backend.connect()
        assert backend.is_connected is True

        await backend.disconnect()
        assert backend.is_connected is False

    @pytest.mark.asyncio
    async def test_write_and_get_latest(self, sample_telemetry, sample_telemetry_batch) -> None:
        backend = InMemoryStorageBackend()
        await backend.connect()

        await backend.write_point(sample_telemetry)
        await backend.write_points(sample_telemetry_batch)
        latest = await backend.get_latest(sample_telemetry.device_id)

        assert latest is not None
        assert latest.device_id == sample_telemetry.device_id
        assert latest.power_kw == sample_telemetry_batch[-1].power_kw

    @pytest.mark.asyncio
    async def test_query_range_respects_window_and_limit(self, sample_telemetry_batch) -> None:
        backend = InMemoryStorageBackend()
        await backend.connect()
        await backend.write_points(sample_telemetry_batch)

        start = sample_telemetry_batch[0].timestamp - timedelta(minutes=1)
        end = sample_telemetry_batch[-1].timestamp + timedelta(minutes=1)
        results = await backend.query_range(
            sample_telemetry_batch[0].device_id,
            start,
            end,
            limit=1,
        )

        assert len(results) == 1
        assert results[0].device_id == sample_telemetry_batch[0].device_id

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_for_unknown_device(self) -> None:
        backend = InMemoryStorageBackend()
        await backend.connect()

        latest = await backend.get_latest("unknown-device")

        assert latest is None

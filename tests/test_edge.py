"""
Tests for the GridOS edge caching module.
"""

from __future__ import annotations

import pytest

from gridos.edge.local_cache import LocalCache


class TestLocalCache:
    """Tests for the SQLite local cache."""

    @pytest.fixture
    def cache(self, tmp_path):
        db_path = str(tmp_path / "test_cache.db")
        cache = LocalCache(db_path=db_path, max_cache_size=100)
        cache.open()
        yield cache
        cache.close()

    def test_store_and_retrieve(self, cache, sample_telemetry):
        cache.store(sample_telemetry)
        unsynced = cache.get_unsynced()
        assert len(unsynced) == 1
        assert unsynced[0].device_id == sample_telemetry.device_id

    def test_mark_synced(self, cache, sample_telemetry):
        cache.store(sample_telemetry)
        assert cache.get_unsynced_count() == 1
        cache.mark_synced()
        assert cache.get_unsynced_count() == 0

    def test_purge_synced(self, cache, sample_telemetry):
        cache.store(sample_telemetry)
        cache.mark_synced()
        deleted = cache.purge_synced()
        assert deleted == 1

    def test_batch_store(self, cache, sample_telemetry):
        cache.store_batch([sample_telemetry, sample_telemetry, sample_telemetry])
        assert cache.get_unsynced_count() == 3

    def test_context_manager(self, tmp_path, sample_telemetry):
        db_path = str(tmp_path / "ctx_cache.db")
        with LocalCache(db_path=db_path) as cache:
            cache.store(sample_telemetry)
            assert cache.get_unsynced_count() == 1

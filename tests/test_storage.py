"""
Tests for GridOS storage backends.
"""

from __future__ import annotations

import pytest

from gridos.storage.base import StorageBackend


class TestBaseStorage:
    """Tests for the abstract storage backend."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            StorageBackend()


class TestStorageImports:
    """Verify all storage modules can be imported."""

    def test_import_influxdb(self):
        from gridos.storage.influxdb import InfluxDBBackend

        assert InfluxDBBackend is not None

    def test_import_timescaledb(self):
        from gridos.storage.timescaledb import TimescaleDBBackend

        assert TimescaleDBBackend is not None

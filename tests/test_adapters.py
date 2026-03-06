"""
Tests for GridOS protocol adapters.
"""

from __future__ import annotations

import pytest

from gridos.adapters.base import BaseAdapter


class TestBaseAdapter:
    """Tests for the abstract base adapter."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseAdapter(device_id="test")


class TestAdapterImports:
    """Verify all adapter modules can be imported."""

    def test_import_modbus(self):
        from gridos.adapters.modbus import ModbusAdapter

        assert ModbusAdapter is not None

    def test_import_mqtt(self):
        from gridos.adapters.mqtt import MQTTAdapter

        assert MQTTAdapter is not None

    def test_import_dnp3(self):
        from gridos.adapters.dnp3 import DNP3Adapter

        assert DNP3Adapter is not None

    def test_import_iec61850(self):
        from gridos.adapters.iec61850 import IEC61850Adapter

        assert IEC61850Adapter is not None

    def test_import_opcua(self):
        from gridos.adapters.opcua import OPCUAAdapter

        assert OPCUAAdapter is not None

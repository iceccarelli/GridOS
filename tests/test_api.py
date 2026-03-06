"""
Tests for the GridOS FastAPI application.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from gridos.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for system endpoints."""

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "GridOS"

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


class TestDeviceRoutes:
    """Tests for device management routes."""

    def test_list_devices_empty(self, client):
        resp = client.get("/api/v1/devices/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_register_and_get_device(self, client):
        payload = {
            "device": {
                "device_id": "test-dev-001",
                "name": "Test Device",
                "der_type": "solar_pv",
                "rated_power_kw": 10.0,
            },
            "adapter_config": {"protocol": "modbus", "host": "192.168.1.100"},
        }
        resp = client.post("/api/v1/devices/register", json=payload)
        assert resp.status_code == 201

        resp = client.get("/api/v1/devices/test-dev-001")
        assert resp.status_code == 200
        assert resp.json()["device_id"] == "test-dev-001"

    def test_get_nonexistent_device(self, client):
        resp = client.get("/api/v1/devices/nonexistent")
        assert resp.status_code == 404


class TestControlRoutes:
    """Tests for control command routes."""

    def test_send_command_no_device(self, client):
        payload = {
            "device_id": "nonexistent",
            "mode": "power_setpoint",
            "setpoint_kw": 10.0,
        }
        resp = client.post("/api/v1/control/nonexistent", json=payload)
        assert resp.status_code == 404


class TestOptimizationRoutes:
    """Tests for optimisation routes."""

    def test_get_schedule_empty(self, client):
        resp = client.get("/api/v1/optimization/schedule")
        assert resp.status_code == 404

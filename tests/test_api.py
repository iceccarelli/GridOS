"""API tests for the reduced GridOS launch path."""

from __future__ import annotations

from fastapi.testclient import TestClient

from gridos.main import app


class TestSystemEndpoints:
    """Validate the public service surface that must work on first run."""

    def test_root(self) -> None:
        with TestClient(app) as client:
            response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "GridOS"
        assert data["mode"] == "reduced_launch"
        assert data["routes"]["docs"] == "/docs"
        assert data["routes"]["telemetry"] == "/api/v1/telemetry"

    def test_health(self) -> None:
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["storage_backend"] in {"inmemory", "influxdb", "timescaledb"}

    def test_docs_available(self) -> None:
        with TestClient(app) as client:
            response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestDeviceRoutes:
    """Validate device registration and lookup for the supported launch flow."""

    def test_register_list_and_get_device(self) -> None:
        payload = {
            "device": {
                "device_id": "test-dev-001",
                "name": "Test Device",
                "der_type": "solar_pv",
                "rated_power_kw": 10.0,
            },
            "adapter_config": {},
        }

        with TestClient(app) as client:
            register_response = client.post("/api/v1/devices/register", json=payload)
            list_response = client.get("/api/v1/devices/")
            get_response = client.get("/api/v1/devices/test-dev-001")

        assert register_response.status_code == 201
        assert list_response.status_code == 200
        assert get_response.status_code == 200
        assert get_response.json()["device_id"] == "test-dev-001"
        assert len(list_response.json()) == 1

    def test_get_nonexistent_device(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/devices/missing-device")

        assert response.status_code == 404


class TestTelemetryRoutes:
    """Validate the supported telemetry ingestion and query workflow."""

    def test_ingest_single_telemetry(self, sample_telemetry) -> None:
        payload = sample_telemetry.model_dump(mode="json")

        with TestClient(app) as client:
            response = client.post("/api/v1/telemetry/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ingested"
        assert data["device_id"] == sample_telemetry.device_id

    def test_ingest_batch_and_query_history(self, sample_telemetry_batch) -> None:
        payload = {
            "readings": [reading.model_dump(mode="json") for reading in sample_telemetry_batch]
        }

        with TestClient(app) as client:
            ingest_response = client.post("/api/v1/telemetry/batch", json=payload)
            history_response = client.get(f"/api/v1/telemetry/{sample_telemetry_batch[0].device_id}")

        assert ingest_response.status_code == 201
        assert history_response.status_code == 200
        assert ingest_response.json()["count"] == 2
        history = history_response.json()
        assert len(history) == 2
        assert history[0]["device_id"] == sample_telemetry_batch[0].device_id
        assert history[-1]["power_kw"] == sample_telemetry_batch[-1].power_kw

    def test_get_latest_telemetry(self, sample_telemetry_batch) -> None:
        payload = {
            "readings": [reading.model_dump(mode="json") for reading in sample_telemetry_batch]
        }
        device_id = sample_telemetry_batch[0].device_id

        with TestClient(app) as client:
            client.post("/api/v1/telemetry/batch", json=payload)
            response = client.get(f"/api/v1/telemetry/{device_id}/latest")

        assert response.status_code == 200
        latest = response.json()
        assert latest["device_id"] == device_id
        assert latest["power_kw"] == sample_telemetry_batch[-1].power_kw

    def test_latest_telemetry_missing_device(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/telemetry/missing-device/latest")

        assert response.status_code == 404


class TestControlRoutes:
    """Validate the reduced control command behavior."""

    def test_send_command_requires_registered_device(self) -> None:
        payload = {
            "device_id": "missing-device",
            "mode": "power_setpoint",
            "setpoint_kw": 10.0,
        }

        with TestClient(app) as client:
            response = client.post("/api/v1/control/missing-device", json=payload)

        assert response.status_code == 404

    def test_send_command_returns_accepted_not_dispatched_without_adapter(self) -> None:
        registration = {
            "device": {
                "device_id": "test-battery-001",
                "name": "Test Battery",
                "der_type": "battery",
                "rated_power_kw": 25.0,
                "rated_energy_kwh": 50.0,
            },
            "adapter_config": {},
        }
        command = {
            "device_id": "test-battery-001",
            "mode": "power_setpoint",
            "setpoint_kw": 5.0,
        }

        with TestClient(app) as client:
            client.post("/api/v1/devices/register", json=registration)
            response = client.post("/api/v1/control/test-battery-001", json=command)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted_not_dispatched"
        assert data["device_id"] == "test-battery-001"

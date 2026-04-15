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
        assert data["docs"] == "/docs"
        assert data["telemetry"] == "/api/v1/telemetry"

    def test_health(self) -> None:
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["storage_mode"] in {"inmemory", "influxdb", "timescaledb"}

    def test_docs_available(self) -> None:
        with TestClient(app) as client:
            response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


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
        batch_payload = {
            "readings": [reading.model_dump(mode="json") for reading in sample_telemetry_batch]
        }

        with TestClient(app) as client:
            ingest_response = client.post("/api/v1/telemetry/batch", json=batch_payload)
            history_response = client.get(f"/api/v1/telemetry/{sample_telemetry_batch[0].device_id}")

        assert ingest_response.status_code == 201
        ingest_data = ingest_response.json()
        assert ingest_data["status"] == "ingested"
        assert ingest_data["count"] == 2

        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history) >= 2
        assert history[0]["device_id"] == sample_telemetry_batch[0].device_id

    def test_get_latest_telemetry(self, sample_telemetry_batch) -> None:
        batch_payload = {
            "readings": [reading.model_dump(mode="json") for reading in sample_telemetry_batch]
        }
        device_id = sample_telemetry_batch[0].device_id

        with TestClient(app) as client:
            client.post("/api/v1/telemetry/batch", json=batch_payload)
            response = client.get(f"/api/v1/telemetry/{device_id}/latest")

        assert response.status_code == 200
        latest = response.json()
        assert latest["device_id"] == device_id
        assert latest["power_kw"] == sample_telemetry_batch[-1].power_kw

    def test_latest_telemetry_missing_device(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/telemetry/missing-device/latest")

        assert response.status_code == 404

    def test_invalid_time_window_returns_400(self) -> None:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/telemetry/test-pv-001",
                params={
                    "start": "2026-01-02T00:00:00Z",
                    "end": "2026-01-01T00:00:00Z",
                },
            )

        assert response.status_code == 400

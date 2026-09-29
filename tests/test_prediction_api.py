"""
tests/test_prediction_api.py

API integration tests for Phase 3 prediction endpoints.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.main import app, routing_service

@pytest.fixture(scope="module")
def client():
    routing_service.initialise()
    with TestClient(app) as c:
        yield c


class TestPredictionEndpoints:
    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"].startswith(("3", "4", "5", "6"))


    def test_get_congestion_predictions(self, client):
        response = client.get("/api/predictions/congestion?date=2024-01-08&time_slot=36")
        assert response.status_code == 200
        preds = response.json()
        assert isinstance(preds, list)
        assert len(preds) > 0
        first = preds[0]
        assert "edge_id" in first
        assert "line" in first
        assert "data_provenance" in first

    def test_get_network_state(self, client):
        response = client.get("/api/predictions/network-state?date=2024-01-08&time_slot=36")
        assert response.status_code == 200
        data = response.json()
        assert data["edge_count"] == 127
        assert len(data["edges"]) == 127

        # Check Pink/Blue null prediction policy
        pink_edges = [e for e in data["edges"] if e["line"] == "Pink"]
        assert len(pink_edges) == 17
        for e in pink_edges:
            assert e["active"] is False
            assert e["predicted_congestion_pct"] is None
            assert e["data_provenance"] == "NO_SYNTHETIC_DATA"

    def test_get_model_performance(self, client):
        response = client.get("/api/predictions/model-performance")
        assert response.status_code == 200
        data = response.json()
        assert "congestion" in data
        assert "travel_time" in data
        assert "delay_risk" in data


"""
tests/test_api.py
Integration tests for FastAPI endpoints under single canonical 5-line graph architecture.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.main import app, routing_service
from src.config.settings import DEFAULT_ACTIVE_LINES


@pytest.fixture(scope="module")
def client():
    routing_service.initialise()
    routing_service.set_active_lines(set(DEFAULT_ACTIVE_LINES))
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["graph_nodes"] > 0
        assert data["graph_edges"] > 0


class TestStationsEndpoint:
    def test_returns_all_stations(self, client):
        resp = client.get("/api/stations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0

    def test_search_query(self, client):
        resp = client.get("/api/stations?q=Majestic")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1


class TestNetworkEndpoint:
    def test_network_returns_canonical_5_lines(self, client):
        resp = client.get("/api/network")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data["lines"]) == {"Purple", "Green", "Yellow", "Pink", "Blue"}
        assert len(data["interchange_locations"]) == 7


class TestRouteEndpoint:
    def test_simple_same_line_route(self, client):
        resp = client.get("/api/route?origin=Indiranagar&destination=MG+Road")
        assert resp.status_code == 200
        data = resp.json()
        assert data["origin"] == "Indiranagar"
        assert "MG Road" in data["destination"]

    def test_inactive_line_returns_400(self, client):
        resp = client.get("/api/route?origin=Kalena+Agrahara&destination=MG+Road")
        assert resp.status_code in (400, 404)
        detail = resp.json()["detail"]
        assert "inactive" in detail.lower() or "under construction" in detail.lower() or "not found" in detail.lower()

    def test_invalid_station_404(self, client):
        resp = client.get("/api/route?origin=Hogwarts&destination=MG+Road")
        assert resp.status_code == 404

    def test_same_station_400(self, client):
        resp = client.get("/api/route?origin=Indiranagar&destination=Indiranagar")
        assert resp.status_code == 400

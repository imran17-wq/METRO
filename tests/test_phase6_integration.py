"""
tests/test_phase6_integration.py

Phase 6 End-to-End Integration & Shared Disruption State Test Suite.
Verifies the complete demo workflow via real backend APIs:
baseline route → activate scenario → disrupted route & time delta → resilience metrics → deactivate scenario → state restoration.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.main import app, routing_service, scenario_engine, _ensure_network_state
from src.config.settings import DEFAULT_ACTIVE_LINES


@pytest.fixture(scope="module")
def setup_services():
    routing_service.initialise()
    routing_service.set_active_lines(set(DEFAULT_ACTIVE_LINES))
    state_svc = _ensure_network_state("2024-01-08", 36)
    return routing_service, state_svc


@pytest.fixture(scope="module")
def client():
    routing_service.initialise()
    with TestClient(app) as c:
        yield c


class TestPhase6Integration:
    def test_health_endpoint_phase_6(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["phase"].startswith("6")

    def test_end_to_end_demo_workflow(self, client):
        origin = "Whitefield (Kadugodi)"
        destination = "Silk Institute"


        # ── Step 1: Baseline Route Calculation ─────────────────────────────
        res1 = client.get("/api/routes/compare", params={"origin": origin, "destination": destination, "profile": "BALANCED"})
        assert res1.status_code == 200
        base_data = res1.json()
        rec_base = base_data["recommended"]
        base_time = rec_base["predicted_travel_time"] or rec_base["total_time_min"]
        assert base_time > 0

        # ── Step 2: Activate Disruption Scenario (Majestic Congestion) ────
        act_res = client.post("/api/simulation/scenarios/majestic_congestion/activate")
        assert act_res.status_code == 200
        assert act_res.json()["status"] == "ACTIVE"

        # Verify active simulation state
        state_res = client.get("/api/simulation/state")
        assert state_res.status_code == 200
        st_data = state_res.json()
        assert st_data["is_active"] is True
        assert st_data["active_scenario"]["id"] == "majestic_congestion"

        # ── Step 3: Recalculate Disrupted Route via Dynamic Router ─────────
        res2 = client.get("/api/routes/compare", params={"origin": origin, "destination": destination, "profile": "BALANCED"})
        assert res2.status_code == 200
        dis_data = res2.json()
        rec_dis = dis_data["recommended"]
        dis_time = rec_dis["predicted_travel_time"] or rec_dis["total_time_min"]

        # Travel time under Majestic congestion must be strictly greater than baseline
        assert dis_time > base_time
        time_delta = dis_time - base_time
        assert time_delta > 0.0

        # ── Step 4: Request Impact & Resilience Metrics ───────────────────
        imp_res = client.get("/api/simulation/impact", params={"origin": origin, "destination": destination, "scenario_id": "majestic_congestion"})
        assert imp_res.status_code == 200
        imp_data = imp_res.json()
        assert imp_data["unreachable"] is False
        assert imp_data["travel_time_change_min"] > 0

        resil_res = client.get("/api/simulation/resilience", params={"scenario_id": "majestic_congestion", "sample_size": 50})
        assert resil_res.status_code == 200
        resil_data = resil_res.json()
        assert 0 <= resil_data["resilience_score"] <= 100
        assert resil_data["sample_size"] == 50

        # ── Step 5: Deactivate Scenario & Verify Exact State Restoration ─
        deact_res = client.post("/api/simulation/scenarios/majestic_congestion/deactivate")
        assert deact_res.status_code == 200
        assert deact_res.json()["status"] == "DEACTIVATED"

        # State check
        state_res_after = client.get("/api/simulation/state")
        assert state_res_after.json()["is_active"] is False

        # Route check after restoration matches baseline time exactly
        res3 = client.get("/api/routes/compare", params={"origin": origin, "destination": destination, "profile": "BALANCED"})
        assert res3.status_code == 200
        restored_time = res3.json()["recommended"]["predicted_travel_time"] or res3.json()["recommended"]["total_time_min"]
        assert restored_time == base_time


    def test_inactive_pink_line_user_error_response(self, client):
        # Pink line station 'Kalena Agrahara' to 'MG Road'
        res = client.get("/api/routes/compare", params={"origin": "Kalena Agrahara", "destination": "MG Road"})
        assert res.status_code == 400
        err_detail = res.json()["detail"]
        assert "inactive" in err_detail.lower() or "pink" in err_detail.lower()

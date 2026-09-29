"""
tests/test_simulation.py

Comprehensive Phase 5 unit & integration tests for Namma Pulse Disruption
Simulation & Network Resilience.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph.metro_graph import build_metro_graph
from src.ml.network_state import NetworkStateBuilder
from src.routing.network_state_service import NetworkStateService
from src.routing.routing_service import RoutingService, InactiveLineError, NoRouteError
from src.simulation.disruption import Disruption, DisruptionType, Severity
from src.simulation.scenario import Scenario, SCENARIO_LIBRARY, get_scenario, list_scenarios
from src.simulation.scenario_engine import ScenarioEngine
from src.simulation.impact_analysis import ImpactAnalyzer
from src.simulation.resilience import ResilienceEvaluator, ResilienceMetrics
from src.config.settings import DEFAULT_ACTIVE_LINES
from src.api.main import app, routing_service, scenario_engine, _ensure_network_state


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


class TestScenarioLibrary:
    def test_scenario_library_contains_8_scenarios(self):
        scenarios = list_scenarios()
        assert len(scenarios) >= 8
        ids = [sc.id for sc in scenarios]
        assert "majestic_closure" in ids
        assert "rv_road_closure" in ids
        assert "purple_closure" in ids
        assert "blue_closure" in ids
        assert "majestic_congestion" in ids
        assert "silk_board_surge" in ids
        assert "kr_pura_track_closure" in ids
        assert "nagawara_delay" in ids

    def test_scenario_provenance_labels(self):
        sc = get_scenario("majestic_closure")
        assert sc is not None
        assert sc.provenance_label == "SIMULATED SCENARIO"


class TestTopologyImmutability:
    def test_activation_does_not_modify_canonical_graph_nodes_or_edges(self, setup_services):
        rot_svc, state_svc = setup_services
        G = rot_svc._graph
        nodes_before = G.number_of_nodes()
        edges_before = G.number_of_edges()

        engine = ScenarioEngine()
        engine.activate_scenario("majestic_closure", state_svc)

        assert G.number_of_nodes() == nodes_before
        assert G.number_of_edges() == edges_before

        engine.deactivate_scenario(state_svc)

        assert G.number_of_nodes() == nodes_before
        assert G.number_of_edges() == edges_before


class TestStateRestorationRecovery:
    def test_deactivation_restores_exact_base_state(self, setup_services):
        _, state_svc = setup_services
        engine = ScenarioEngine()

        base_edge_state = state_svc.get_edge_state("PL_E01")
        assert base_edge_state is not None
        base_active = base_edge_state.get("active")
        base_tt = base_edge_state.get("predicted_travel_time_min")

        engine.activate_scenario("majestic_closure", state_svc)
        disrupted_edge_state = state_svc.get_edge_state("PL_E01")
        assert disrupted_edge_state is not None

        engine.deactivate_scenario(state_svc)
        restored_edge_state = state_svc.get_edge_state("PL_E01")
        assert restored_edge_state is not None
        assert restored_edge_state.get("active") == base_active
        assert restored_edge_state.get("predicted_travel_time_min") == base_tt


class TestDisruptionTypes:
    def test_station_closure(self, setup_services):
        rot_svc, state_svc = setup_services
        engine = ScenarioEngine()
        engine.activate_scenario("majestic_closure", state_svc)

        # Majestic node PL22 should be inactive in overlay
        st_state = state_svc.get_edge_state("PL_E21")  # Central College to Majestic
        assert st_state is not None
        assert st_state["active"] is False

        engine.deactivate_scenario(state_svc)

    def test_line_closure_rerouting(self, setup_services):
        rot_svc, state_svc = setup_services
        engine = ScenarioEngine()
        engine.activate_scenario("purple_closure", state_svc)

        p_edge = state_svc.get_edge_state("PL_E01")
        assert p_edge is not None
        assert p_edge["active"] is False

        engine.deactivate_scenario(state_svc)

    def test_interchange_closure_keeps_through_tracks(self, setup_services):
        rot_svc, state_svc = setup_services
        engine = ScenarioEngine()
        engine.activate_scenario("rv_road_closure", state_svc)

        # Transfer edge should be closed
        xfer_state = state_svc.get_edge_state("XFER_GL24_YL01")
        if xfer_state:
            assert xfer_state["active"] is False

        # Through line track segment (GL23 to GL24) on Green line should remain active
        through_edge = state_svc.get_edge_state("GL_E23")
        assert through_edge is not None
        assert through_edge["active"] is True

        engine.deactivate_scenario(state_svc)

    def test_severe_delay(self, setup_services):
        rot_svc, state_svc = setup_services
        engine = ScenarioEngine()

        base_tt = state_svc.get_edge_state("PL_E01").get("predicted_travel_time_min", 2.5) if state_svc.get_edge_state("PL_E01") else 2.5

        engine.activate_scenario("kr_pura_track_closure", state_svc)
        delayed_state = state_svc.get_edge_state("PL_E11")
        if delayed_state:
            assert delayed_state["predicted_travel_time_min"] > base_tt

        engine.deactivate_scenario(state_svc)



class TestImpactAnalysis:
    def test_compare_route_impact(self, setup_services):
        rot_svc, state_svc = setup_services
        engine = ScenarioEngine()

        # Activate Majestic closure
        engine.activate_scenario("majestic_closure", state_svc)

        impact = ImpactAnalyzer.compare_route_impact(
            "Indiranagar", "MG Road", rot_svc, state_svc, profile="BALANCED"
        )
        assert impact["origin"] == "Indiranagar"
        assert impact["destination"] == "MG Road"
        assert impact["unreachable"] is False
        assert impact["baseline_time_min"] is not None

        engine.deactivate_scenario(state_svc)


class TestResilienceEvaluation:
    def test_deterministic_od_sampling(self, setup_services):
        rot_svc, _ = setup_services
        evaluator = ResilienceEvaluator(rot_svc)

        sample1 = evaluator.get_representative_od_sample(sample_size=50, seed=42)
        sample2 = evaluator.get_representative_od_sample(sample_size=50, seed=42)

        assert len(sample1) == 50
        assert sample1 == sample2

    def test_evaluate_resilience_metrics(self, setup_services):
        rot_svc, state_svc = setup_services
        engine = ScenarioEngine()
        sc = get_scenario("majestic_closure")
        assert sc is not None

        engine.activate_scenario("majestic_closure", state_svc)

        evaluator = ResilienceEvaluator(rot_svc)
        metrics = evaluator.evaluate_resilience(state_svc, sc, sample_size=50, seed=42)

        assert metrics.scenario_id == "majestic_closure"
        assert 0.0 <= metrics.route_availability_pct <= 100.0
        assert 0.0 <= metrics.resilience_score <= 100.0
        assert metrics.data_provenance["scenario"] == "SIMULATED_SCENARIO"

        engine.deactivate_scenario(state_svc)


class TestSimulationAPIEndpoints:
    def test_get_scenarios(self, client):
        res = client.get("/api/simulation/scenarios")
        assert res.status_code == 200
        scenarios = res.json()
        assert len(scenarios) >= 8

    def test_get_scenario_by_id(self, client):
        res = client.get("/api/simulation/scenarios/majestic_closure")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "majestic_closure"
        assert data["provenance_label"] == "SIMULATED SCENARIO"

    def test_activate_and_deactivate_scenario_endpoints(self, client):
        # Activate
        res_act = client.post("/api/simulation/scenarios/majestic_closure/activate")
        assert res_act.status_code == 200
        act_data = res_act.json()
        assert act_data["status"] == "ACTIVE"

        # Check simulation state
        res_state = client.get("/api/simulation/state")
        assert res_state.status_code == 200
        st_data = res_state.json()
        assert st_data["is_active"] is True

        # Deactivate
        res_deact = client.post("/api/simulation/scenarios/majestic_closure/deactivate")
        assert res_deact.status_code == 200
        deact_data = res_deact.json()
        assert deact_data["status"] == "DEACTIVATED"

        # Verify state restored
        res_state_after = client.get("/api/simulation/state")
        assert res_state_after.json()["is_active"] is False

    def test_get_route_impact_endpoint(self, client):
        res = client.get(
            "/api/simulation/impact",
            params={
                "origin": "Indiranagar",
                "destination": "MG Road",
                "scenario_id": "majestic_closure",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "baseline_route" in data
        assert data["data_provenance"]["scenario"] == "SIMULATED_SCENARIO"

    def test_get_resilience_metrics_endpoint(self, client):
        res = client.get(
            "/api/simulation/resilience",
            params={
                "scenario_id": "majestic_closure",
                "sample_size": 50,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "resilience_score" in data
        assert "route_availability_pct" in data
        assert data["sample_size"] == 50

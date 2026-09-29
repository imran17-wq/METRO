"""
tests/test_dynamic_routing.py

Comprehensive Phase 4 unit & integration tests for Namma Pulse Intelligent
Dynamic Rerouting.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph.metro_graph import build_metro_graph
from src.routing.edge_cost import DynamicCostCalculator, RouteEdgeCost
from src.routing.candidate_generator import CandidateRouteGenerator
from src.routing.route_scorer import RouteScorer, RouteScore
from src.routing.dominance import ParetoFilter, is_dominated
from src.routing.explanation_generator import RouteExplanationGenerator
from src.routing.network_state_service import NetworkStateService
from src.routing.routing_service import (
    RoutingService,
    InactiveLineError,
    NoRouteError,
)
from src.ml.network_state import NetworkStateBuilder
from src.config.settings import DEFAULT_ACTIVE_LINES
from src.config.routing_weights import ROUTE_PROFILES, CONGESTION_SCALE_MIN, DELAY_SCALE_MIN
from src.api.main import app


@pytest.fixture(scope="module")
def graph_and_stations():
    G = build_metro_graph()
    from src.graph import metro_graph as mg
    return G, dict(mg._stations)


@pytest.fixture(scope="module")
def net_builder(graph_and_stations):
    G, _ = graph_and_stations
    return NetworkStateBuilder(G)


@pytest.fixture(scope="function")
def routing_service_instance():
    svc = RoutingService()
    svc.initialise()
    svc.set_active_lines(set(DEFAULT_ACTIVE_LINES))
    yield svc
    svc.set_active_lines(set(DEFAULT_ACTIVE_LINES))


@pytest.fixture(scope="function")
def state_service(net_builder):
    svc = NetworkStateService(net_builder)
    # Explicit date and time_slot for deterministic test execution
    svc.refresh("2024-01-08", 36)
    return svc


class TestDynamicEdgeCost:
    def test_dynamic_cost_calculation(self):
        state_index = {
            "PL_E01": {
                "edge_id": "PL_E01",
                "active": True,
                "predicted_travel_time_min": 3.0,
                "predicted_congestion_pct": 50.0,
                "delay_risk_prob": 0.1,
                "data_provenance": "SYNTHETIC MODEL OUTPUT",
            }
        }
        calc = DynamicCostCalculator(state_index)
        edge_data = {"edge_id": "PL_E01", "line": "Purple", "scheduled_time_min": 2.5}
        cost = calc.compute("PL01", "PL02", edge_data)

        assert cost.travel_time == 3.0
        assert cost.congestion_penalty == pytest.approx(0.5 * CONGESTION_SCALE_MIN)
        assert cost.delay_penalty == pytest.approx(0.1 * DELAY_SCALE_MIN)
        assert cost.transfer_penalty == 0.0
        assert cost.prediction_source == "SYNTHETIC MODEL OUTPUT"

    def test_inactive_edge_returns_inf(self):
        state_index = {
            "PL_E01": {
                "edge_id": "PL_E01",
                "active": False,
            }
        }
        calc = DynamicCostCalculator(state_index)
        edge_data = {"edge_id": "PL_E01", "line": "Purple"}
        cost = calc.compute("PL01", "PL02", edge_data)
        assert cost.travel_time == float("inf")

    def test_fallback_costs_when_unindexed(self):
        calc = DynamicCostCalculator({})
        edge_data = {"edge_id": "UNINDEXED_E1", "line": "Purple", "scheduled_time_min": 2.5}
        cost = calc.compute("PL01", "PL02", edge_data)
        assert cost.travel_time == 2.5
        assert cost.prediction_source == "FALLBACK"


class TestCandidateGeneration:
    def test_k_shortest_candidates(self, graph_and_stations, state_service):
        G, stations = graph_and_stations
        calc = DynamicCostCalculator(state_service.edge_index)
        gen = CandidateRouteGenerator(G, stations)

        # Whitefield (Kadugodi) PL01 to Silk Institute GL32
        candidates = gen.generate_candidates(
            "PL01", "GL32", calc, active_lines=set(DEFAULT_ACTIVE_LINES), k=5
        )
        assert len(candidates) >= 1
        assert len(candidates) <= 5

    def test_inactive_line_yields_no_candidates(self, graph_and_stations, state_service):
        G, stations = graph_and_stations
        calc = DynamicCostCalculator(state_service.edge_index)
        gen = CandidateRouteGenerator(G, stations)

        # Pink line node PK01 (inactive by default)
        candidates = gen.generate_candidates(
            "PK01", "PL01", calc, active_lines=set(DEFAULT_ACTIVE_LINES), k=5
        )
        assert len(candidates) == 0


class TestRouteScoringAndProfiles:
    def test_scoring_applies_profile_weights(self, graph_and_stations, state_service):
        G, stations = graph_and_stations
        calc = DynamicCostCalculator(state_service.edge_index)
        scorer = RouteScorer(G, stations)
        gen = CandidateRouteGenerator(G, stations)

        candidates = gen.generate_candidates(
            "PL01", "GL32", calc, active_lines=set(DEFAULT_ACTIVE_LINES), k=3
        )
        assert len(candidates) > 0

        score_balanced = scorer.score_path(candidates[0], calc, profile="BALANCED")
        score_fastest = scorer.score_path(candidates[0], calc, profile="FASTEST")

        assert score_balanced is not None
        assert score_fastest is not None
        # FASTEST profile weighs travel_time heavier than BALANCED
        assert score_fastest.total_score != score_balanced.total_score

    def test_reliability_score_calculation(self, graph_and_stations, state_service):
        G, stations = graph_and_stations
        calc = DynamicCostCalculator(state_service.edge_index)
        scorer = RouteScorer(G, stations)
        path = ["PL18", "PL19", "PL20"]  # MG Road to Indiranagar segment

        score = scorer.score_path(path, calc, profile="BALANCED")
        assert score is not None
        assert 0.0 <= score.reliability_score <= 1.0
        assert score.reliability_score == pytest.approx(1.0 - score.delay_risk_prob, abs=1e-4)


class TestParetoDominance:
    def test_pareto_dominance_filtering(self):
        # Create a benchmark score
        benchmark = RouteScore(
            total_score=30.0,
            predicted_travel_time_min=25.0,
            predicted_congestion_pct=30.0,
            delay_risk_prob=0.05,
            reliability_score=0.95,
            transfer_count=1,
            transfer_penalty_min=3.0,
            prediction_source="SYNTHETIC MODEL OUTPUT",
            score_breakdown={},
            edge_costs=[],
        )

        # Inferior candidate: strictly worse in time & congestion
        inferior = RouteScore(
            total_score=40.0,
            predicted_travel_time_min=30.0,
            predicted_congestion_pct=45.0,
            delay_risk_prob=0.10,
            reliability_score=0.90,
            transfer_count=1,
            transfer_penalty_min=3.0,
            prediction_source="SYNTHETIC MODEL OUTPUT",
            score_breakdown={},
            edge_costs=[],
        )

        # Trade-off candidate: faster but more transfers
        tradeoff = RouteScore(
            total_score=28.0,
            predicted_travel_time_min=22.0,
            predicted_congestion_pct=35.0,
            delay_risk_prob=0.05,
            reliability_score=0.95,
            transfer_count=2,
            transfer_penalty_min=6.0,
            prediction_source="SYNTHETIC MODEL OUTPUT",
            score_breakdown={},
            edge_costs=[],
        )

        assert is_dominated(inferior, benchmark) is True
        assert is_dominated(tradeoff, benchmark) is False

        candidates = [
            (["node1", "node2"], benchmark),
            (["node1", "node3", "node2"], inferior),
            (["node1", "node4", "node2"], tradeoff),
        ]

        filtered = ParetoFilter.filter_dominated_candidates(candidates)
        filtered_paths = [p for p, _ in filtered]

        assert ["node1", "node2"] in filtered_paths
        assert ["node1", "node4", "node2"] in filtered_paths
        assert ["node1", "node3", "node2"] not in filtered_paths


class TestExplanationGenerator:
    def test_explanation_matches_metrics(self):
        rec = RouteScore(
            total_score=25.0,
            predicted_travel_time_min=20.0,
            predicted_congestion_pct=25.0,
            delay_risk_prob=0.02,
            reliability_score=0.98,
            transfer_count=0,
            transfer_penalty_min=0.0,
            prediction_source="SYNTHETIC MODEL OUTPUT",
            score_breakdown={},
            edge_costs=[],
        )
        alt = RouteScore(
            total_score=35.0,
            predicted_travel_time_min=24.5,
            predicted_congestion_pct=42.0,
            delay_risk_prob=0.10,
            reliability_score=0.90,
            transfer_count=1,
            transfer_penalty_min=3.0,
            prediction_source="SYNTHETIC MODEL OUTPUT",
            score_breakdown={},
            edge_costs=[],
        )

        explanation = RouteExplanationGenerator.generate_explanation(rec, [alt], profile="BALANCED")
        assert "faster" in explanation.lower() or "congestion" in explanation.lower() or "transfer" in explanation.lower()


class TestDynamicRoutingServiceIntegration:
    def test_dynamic_route_execution(self, routing_service_instance, state_service):
        result = routing_service_instance.dynamic_route(
            "Indiranagar", "MG Road", state_service, profile="BALANCED"
        )
        assert result.recommended is not None
        assert result.recommended.route_profile == "BALANCED"
        assert result.recommended.recommendation_reason is not None
        assert result.recommended.predicted_travel_time is not None
        assert result.network_state_timestamp != "N/A"

    def test_inactive_pink_line_blocked_in_dynamic_route(self, routing_service_instance, state_service):
        with pytest.raises((InactiveLineError, NoRouteError)):
            routing_service_instance.dynamic_route(
                "Kalena Agrahara", "MG Road", state_service, profile="BALANCED"
            )

    def test_activating_pink_line_allows_dynamic_traversal(self, routing_service_instance, state_service):
        routing_service_instance.activate_line("Pink")
        # Update active lines in state_service
        state_service.refresh("2024-01-08", 36, active_lines=routing_service_instance.get_active_lines())

        result = routing_service_instance.dynamic_route(
            "Kalena Agrahara", "MG Road", state_service, profile="BALANCED"
        )
        assert result.recommended is not None
        assert "Pink" in result.recommended.lines


class TestFastAPIEndpoints:
    def test_api_routes_compare_endpoint(self):
        client = TestClient(app)
        response = client.get(
            "/api/routes/compare",
            params={
                "origin": "Whitefield (Kadugodi)",
                "destination": "Silk Institute",
                "profile": "BALANCED",
                "date": "2024-01-08",
                "time_slot": 36,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "recommended" in data
        assert "alternatives" in data
        assert data["profile"] == "BALANCED"
        assert "data_provenance" in data
        assert data["recommended"]["recommendation_reason"] is not None
        assert data["recommended"]["score_breakdown"] is not None

    def test_api_route_with_profile_param(self):
        client = TestClient(app)
        response = client.get(
            "/api/route",
            params={
                "origin": "Indiranagar",
                "destination": "MG Road",
                "profile": "FASTEST",
                "date": "2024-01-08",
                "time_slot": 36,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["route_profile"] == "FASTEST"
        assert data["predicted_travel_time"] is not None

    def test_api_route_without_profile_preserves_backward_compat(self):
        client = TestClient(app)
        response = client.get(
            "/api/route",
            params={
                "origin": "Indiranagar",
                "destination": "MG Road",
                "algorithm": "dijkstra",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "dijkstra"
        assert data["route_profile"] is None

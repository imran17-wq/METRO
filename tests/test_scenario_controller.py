"""
test_scenario_controller.py — Comprehensive tests for Network Scenario Controller.

Validates mandatory corrections:
- Dynamic graph counts & graph immutability
- Backend-authoritative line activation (Pink/Blue train services, routing, demand)
- Scenario deactivation & exact state reset
- All-lines-off safety rejection with 400 error message
- Peak headway, custom scenario, multi-disruption
- FastAPI API endpoints integration
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, routing_service, scenario_engine, _ensure_operations_engine, _ensure_network_state
from src.graph.metro_graph import build_metro_graph, get_active_lines
from src.operations.operations_engine import OperationsEngine
from src.routing.routing_service import RoutingService, InactiveLineError
from src.simulation.scenario import get_scenario, list_scenarios, Scenario
from src.simulation.scenario_engine import ScenarioEngine


client = TestClient(app)


def setup_function():
    """Reset to baseline before each test."""
    routing_service.initialise()
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()
    scenario_engine.deactivate_scenario(state_svc, routing_service, ops_eng)


def test_graph_immutability():
    """Graph node & edge counts must remain identical before & after scenario activation."""
    G = routing_service._require_init()
    initial_nodes = G.number_of_nodes()
    initial_edges = G.number_of_edges()

    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    scenario_engine.activate_scenario("expanded_5_line", state_svc, routing_service, ops_eng)
    assert G.number_of_nodes() == initial_nodes
    assert G.number_of_edges() == initial_edges

    scenario_engine.deactivate_scenario(state_svc, routing_service, ops_eng)
    assert G.number_of_nodes() == initial_nodes
    assert G.number_of_edges() == initial_edges


def test_scenario_activation():
    """Activating expanded 5-line scenario updates active lines across all services."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    res = scenario_engine.activate_scenario("expanded_5_line", state_svc, routing_service, ops_eng)
    assert res["status"] == "ACTIVE"
    assert "Pink" in res["active_lines"]
    assert "Blue" in res["active_lines"]
    assert get_active_lines() == {"Purple", "Green", "Yellow", "Pink", "Blue"}


def test_pink_service_activation():
    """When Pink is activated, Pink trains exist in OperationsEngine."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    scenario_engine.activate_scenario("expanded_5_line", state_svc, routing_service, ops_eng)
    pink_trains = [t for t in ops_eng.trains if t.line == "Pink"]
    assert len(pink_trains) > 0, "Pink trains must exist when Expanded 5-Line is activated"


def test_blue_service_activation():
    """When Blue is activated, Blue trains exist in OperationsEngine."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    scenario_engine.activate_scenario("expanded_5_line", state_svc, routing_service, ops_eng)
    blue_trains = [t for t in ops_eng.trains if t.line == "Blue"]
    assert len(blue_trains) > 0, "Blue trains must exist when Expanded 5-Line is activated"


def test_routing_activation():
    """Pink and Blue routes become traversable when activated, and inactive when deactivated."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    # Inactive by default -> Pink route raises InactiveLineError
    with pytest.raises(InactiveLineError):
        routing_service.route("Kalena Agrahara", "Tavarekere")

    # Activate Expanded 5-Line -> Pink route succeeds
    scenario_engine.activate_scenario("expanded_5_line", state_svc, routing_service, ops_eng)
    route_res = routing_service.route("Kalena Agrahara", "Tavarekere")
    assert route_res is not None
    assert "Pink" in route_res.lines

    # Deactivate -> raises InactiveLineError again
    scenario_engine.deactivate_scenario(state_svc, routing_service, ops_eng)
    with pytest.raises(InactiveLineError):
        routing_service.route("Kalena Agrahara", "Tavarekere")


def test_scenario_demand():
    """Scenario demand multiplier increases predicted edge congestion."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    scenario_engine.activate_scenario("peak_expanded", state_svc, routing_service, ops_eng)
    edge_states = state_svc.edge_index
    active_edge = next(e for e in edge_states.values() if e["active"])
    assert active_edge["predicted_congestion_pct"] is not None
    assert active_edge["predicted_congestion_pct"] > 0


def test_peak_headway():
    """Peak expanded scenario reduces headway to 180s and increases total train count."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    # Normal 5-line (360s headway)
    scenario_engine.activate_scenario("expanded_5_line", state_svc, routing_service, ops_eng)
    normal_train_count = len(ops_eng.trains)

    # Peak 5-line (180s headway)
    scenario_engine.activate_scenario("peak_expanded", state_svc, routing_service, ops_eng)
    peak_train_count = len(ops_eng.trains)

    assert ops_eng.headway_sec == 180
    assert peak_train_count > normal_train_count


def test_custom_scenario():
    """Custom scenario activation with user-specified active lines and parameters."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    sc = Scenario(
        id="custom_test_sc",
        name="Custom 4-Line Scenario",
        type="CONGESTION_SURGE",
        target="Purple, Green, Yellow, Pink",
        severity="MEDIUM",
        duration_min=60,
        description="Custom scenario test",
        active_lines=["Purple", "Green", "Yellow", "Pink"],
        headway_sec=240,
        demand_multiplier=1.2,
    )

    res = scenario_engine.activate_scenario(sc, state_svc, routing_service, ops_eng)
    assert res["status"] == "ACTIVE"
    assert "Pink" in res["active_lines"]
    assert "Blue" not in res["active_lines"]
    assert ops_eng.headway_sec == 240


def test_multi_disruption():
    """Full multi-disruption scenario applies multiple disruptions concurrently."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    res = scenario_engine.activate_scenario("full_multi_disruption", state_svc, routing_service, ops_eng)
    assert res["status"] == "ACTIVE"
    assert len(scenario_engine.active_scenario.disruptions) == 3


def test_reset():
    """RESET restores CURRENT_OPERATIONS 3-line baseline state."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    # Activate peak scenario first
    scenario_engine.activate_scenario("peak_expanded", state_svc, routing_service, ops_eng)
    assert get_active_lines() == {"Purple", "Green", "Yellow", "Pink", "Blue"}

    # Reset
    res = scenario_engine.deactivate_scenario(state_svc, routing_service, ops_eng)
    assert res["status"] == "DEACTIVATED"
    assert get_active_lines() == {"Purple", "Green", "Yellow"}
    assert ops_eng.clock.current_time_sec == 28800  # 08:00:00 AM


def test_all_lines_off_rejection():
    """Backend must reject a scenario with zero active lines."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    empty_sc = Scenario(
        id="empty_sc",
        name="Empty Scenario",
        type="CONGESTION_SURGE",
        target="None",
        severity="CRITICAL",
        duration_min=10,
        description="All lines off scenario",
        active_lines=[],
    )

    with pytest.raises(ValueError) as excinfo:
        scenario_engine.activate_scenario(empty_sc, state_svc, routing_service, ops_eng)
    assert "At least one metro line must remain active in the simulation." in str(excinfo.value)


def test_frontend_integration_api_endpoints():
    """API endpoints integration for scenario activation, custom scenario, reset, and rejection."""
    # 1. Activate Expanded 5-Line via API
    resp = client.post("/api/simulation/scenarios/expanded_5_line/activate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACTIVE"
    assert "Pink" in data["active_lines"]

    # 2. Activate Custom Scenario via API
    custom_payload = {
        "name": "Custom Test Scenario",
        "active_lines": ["Purple", "Green", "Yellow", "Blue"],
        "headway_sec": 300,
        "demand_multiplier": 1.2,
    }
    resp = client.post("/api/simulation/scenarios/custom/activate", json=custom_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACTIVE"
    assert "Blue" in data["active_lines"]

    # 3. All-Lines-Off Rejection via API
    bad_payload = {
        "name": "Invalid Zero Lines Scenario",
        "active_lines": [],
    }
    resp = client.post("/api/simulation/scenarios/custom/activate", json=bad_payload)
    assert resp.status_code == 400
    err_data = resp.json()
    assert "At least one metro line must remain active in the simulation." in err_data["detail"]

    # 4. Atomic Reset via API
    resp = client.post("/api/simulation/reset")
    assert resp.status_code == 200
    reset_data = resp.json()
    assert reset_data["status"] == "RESET_COMPLETE"
    assert reset_data["active_lines"] == ["Purple", "Green", "Yellow"]

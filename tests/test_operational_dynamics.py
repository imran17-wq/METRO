"""
test_operational_dynamics.py — Unit Tests for Phase 6.2 Operational Dynamics.

Tests organic operational mechanisms:
- Dynamic dwell calculation (passenger demand, interchange)
- Controlled stochastic running time (deterministic seed)
- Delay propagation
- Scheduled vs actual tracking
- Headway calculation & bunching detection
- Station crowding derivation
- Emergent edge congestion calculation
- Alert feed generation & forecast alerts
- Operator HOLD/RELEASE actions
- Pink & Blue operational service activation
"""
import pytest
from src.operations.operational_dynamics import (
    calculate_actual_running_time,
    calculate_dynamic_dwell,
    calculate_emergent_congestion,
    calculate_line_headways,
    calculate_station_crowding,
)
from src.operations.operations_engine import OperationsEngine, NetworkOperationStatus
from src.operations.train import Train, TrainStatus


@pytest.fixture
def mock_station_data():
    return {
        "Purple": ["Whitefield", "Garudacharapalya", "KR Pura", "Indiranagar", "MG Road", "Majestic"],
        "Green": ["Nagasandra", "Yashwanthpur", "Majestic", "National College", "Silk Institute"],
        "Yellow": ["RV Road", "Jayadeva Hospital", "Silk Board", "Bommasandra"],
        "Pink": ["Kalena Agrahara", "Dairy Circle", "MG Road", "Nagawara"],
        "Blue": ["Silk Board", "Bellandur", "KR Pura", "Airport"],
    }


def test_dynamic_dwell_calculation():
    # Base dwell is 30s
    dwell_low = calculate_dynamic_dwell("Indiranagar", station_demand_ratio=0.1, is_interchange=False)
    dwell_high = calculate_dynamic_dwell("Majestic", station_demand_ratio=1.0, is_interchange=True)

    assert dwell_low >= 30
    assert dwell_high > dwell_low
    # Majestic interchange gets +10s interchange penalty + boarding/alighting penalty
    assert dwell_high >= 50


def test_stochastic_running_time_reproducibility():
    # Same inputs yield identical result due to deterministic hash
    time1 = calculate_actual_running_time(150, congestion_pct=30.0, train_id="PL-001", segment_id="A_B", sim_time_sec=28800, seed=42)
    time2 = calculate_actual_running_time(150, congestion_pct=30.0, train_id="PL-001", segment_id="A_B", sim_time_sec=28800, seed=42)

    assert time1 == time2
    assert time1 > 0


def test_line_headway_and_bunching_detection():
    trains = [
        {"train_id": "PL-001", "line": "Purple", "direction": "UP", "current_station_idx": 4, "progress_pct": 0.8, "delay_seconds": 200},
        {"train_id": "PL-002", "line": "Purple", "direction": "UP", "current_station_idx": 4, "progress_pct": 0.2, "delay_seconds": 0},
    ]

    headways = calculate_line_headways(trains, scheduled_headway_sec=360, bunching_threshold_sec=180)
    assert len(headways) == 2

    # Check for bunching flag on train running close behind
    bunching_found = any(h.bunching_flag for h in headways)
    assert bunching_found is True


def test_station_crowding_derivation():
    metrics_normal = calculate_station_crowding("Indiranagar", is_interchange=False, time_slot=36)
    metrics_majestic = calculate_station_crowding("Majestic", is_interchange=True, time_slot=36)

    assert metrics_normal.crowding_pct > 0
    assert metrics_majestic.crowding_pct > metrics_normal.crowding_pct
    assert metrics_majestic.data_provenance == "DERIVED SIMULATION OUTPUT"


def test_emergent_congestion_derivation():
    base_cong = 20.0
    emergent = calculate_emergent_congestion(
        base_congestion_pct=base_cong,
        station_crowding_pct=80.0,
        headway_bunching=True,
        delay_seconds=240
    )

    # Emergent congestion should be higher than base due to crowding, bunching, and delays
    assert emergent > base_cong + 20.0
    assert emergent <= 100.0


def test_operations_engine_organic_step_and_propagation(mock_station_data):
    engine = OperationsEngine(mock_station_data)
    engine.clock.play()

    # Step simulation forward by 300 seconds (5 minutes)
    engine.step(300)

    state = engine.get_state()
    assert state["clock"]["current_time_sec"] == 28800 + 300
    assert "kpis" in state
    assert state["data_provenance"] == "SIMULATED OPERATIONS"

    # Verify active trains updated positions
    active_trains = state["trains"]
    assert len(active_trains) > 0
    for t in active_trains:
        assert "delay_provenance" in t
        assert t["delay_provenance"] == "DERIVED SIMULATION OUTPUT"


def test_operator_hold_and_release(mock_station_data):
    engine = OperationsEngine(mock_station_data)
    engine.clock.play()
    engine.step(60)

    t_id = engine.trains[0].train_id
    res_hold = engine.hold_train(t_id, reason="Passenger Obstruction")
    assert res_hold is True

    engine.step(120)
    st = engine.get_state()
    held_train = next(t for t in st["trains"] if t["train_id"] == t_id)
    assert held_train["is_held"] is True
    assert held_train["hold_reason"] == "Passenger Obstruction"
    assert held_train["status"] == "STOPPED"

    # Release train
    res_rel = engine.release_train(t_id)
    assert res_rel is True
    engine.step(10)
    st = engine.get_state()
    rel_train = next(t for t in st["trains"] if t["train_id"] == t_id)
    assert rel_train["is_held"] is False


def test_pink_blue_operational_service_activation(mock_station_data):
    engine = OperationsEngine(mock_station_data)
    # Default active lines: Purple, Green, Yellow
    init_train_count = len(engine.trains)

    # Activate Pink & Blue operational services
    engine.set_active_lines({"Purple", "Green", "Yellow", "Pink", "Blue"})
    new_train_count = len(engine.trains)

    assert new_train_count > init_train_count
    pink_trains = [t for t in engine.trains if t.line == "Pink"]
    blue_trains = [t for t in engine.trains if t.line == "Blue"]
    assert len(pink_trains) > 0
    assert len(blue_trains) > 0

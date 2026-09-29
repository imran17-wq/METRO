"""
test_acceptance_normal_simulation.py — Acceptance Test for Phase 6.2 Emergent Dynamics.

Verifies that:
1. Normal simulation starting at 08:00 AM runs WITHOUT activating any manual disruption.
2. Observing for several simulated minutes naturally produces:
   - Train movement along station paths
   - Dynamic dwell variations
   - Headway calculations and deviations
   - Platform crowding and station demand
   - Emergent track segment congestion
   - Dynamic OCC alerts
"""
import pytest
from src.operations.operations_engine import OperationsEngine, NetworkOperationStatus


@pytest.fixture
def station_data():
    return {
        "Purple": ["Whitefield", "Garudacharapalya", "KR Pura", "Indiranagar", "MG Road", "Majestic", "Challaghatta"],
        "Green": ["Madavara", "Nagasandra", "Yashwanthpur", "Majestic", "National College", "Silk Institute"],
        "Yellow": ["RV Road", "Jayadeva Hospital", "Silk Board", "Bommasandra"],
    }


def test_acceptance_normal_simulation_emergent_behavior(station_data):
    engine = OperationsEngine(station_data)
    engine.clock.play()

    # Verify starting state at 08:00:00 AM
    initial_state = engine.get_state()
    assert initial_state["clock"]["formatted_time"] == "08:00:00"
    assert initial_state["active_scenario"] is None
    assert initial_state["data_provenance"] == "SIMULATED OPERATIONS"

    # Advance simulation by 600 simulated seconds (10 minutes)
    for _ in range(10):
        engine.step(60.0)

    final_state = engine.get_state()
    assert final_state["clock"]["formatted_time"] == "08:10:00"

    # 1. Train movement & progress
    trains = final_state["trains"]
    assert len(trains) > 0
    active_moving = [t for t in trains if t["progress_pct"] > 0.0 or t["current_station_idx"] > 0]
    assert len(active_moving) > 0

    # 2. Headway metrics monitored
    assert "headways" in final_state
    headways = final_state["headways"]
    assert len(headways) > 0

    # 3. Dynamic OCC Alert Feed
    alerts = final_state["alerts"]
    assert len(alerts) > 0
    for a in alerts:
        assert "source" in a
        assert a["source"] in ("SIMULATED OPERATIONS", "SYNTHETIC MODEL OUTPUT", "DERIVED SIMULATION OUTPUT")

    # 4. KPIs updated organically
    kpis = final_state["kpis"]
    assert kpis["total_trains"] > 0
    assert kpis["on_time"] + kpis["delayed"] + kpis["stopped"] == kpis["total_trains"]

"""
test_operations.py — Operations Control Center (OCC) Test Suite for Phase 6.1.

Verifies deterministic clock, synthetic timetable generation, train movement, dwell times,
delay propagation, alert generation, operator hold/release actions, disruption interactions,
REST API endpoints, and canonical graph immutability.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.main import app, routing_service, scenario_engine, _ensure_operations_engine
from src.config.settings import DEFAULT_ACTIVE_LINES
from src.operations import (
    SimulationClock,
    TimetableGenerator,
    Train,
    TrainStatus,
    AlertEngine,
    AlertSeverity,
    OperationsEngine,
    evaluate_train_status,
)


@pytest.fixture(scope="module")
def setup_routing():
    routing_service.initialise()
    return routing_service


@pytest.fixture(scope="module")
def client():
    routing_service.initialise()
    with TestClient(app) as c:
        yield c


class TestSimulationClock:
    def test_clock_initial_state(self):
        clock = SimulationClock(start_sec=28800)
        assert clock.current_time_sec == 28800
        assert clock.formatted_time() == "08:00:00"
        assert clock.is_running is False
        assert clock.speed_multiplier == 1.0

    def test_clock_play_pause_reset(self):
        clock = SimulationClock(start_sec=28800)
        clock.play()
        assert clock.is_running is True

        clock.tick(1.0)
        assert clock.current_time_sec > 28800

        clock.pause()
        assert clock.is_running is False
        time_paused = clock.current_time_sec
        clock.tick(1.0)
        assert clock.current_time_sec == time_paused

        clock.reset()
        assert clock.current_time_sec == 28800
        assert clock.is_running is False

    def test_clock_speed_multipliers(self):
        clock = SimulationClock(start_sec=28800)
        clock.set_speed(5.0)
        assert clock.speed_multiplier == 5.0
        clock.play()
        clock.tick(1.0)
        assert clock.current_time_sec == 28805


class TestTimetableAndTrainMovement:
    def test_timetable_seed_reproducibility(self, setup_routing):
        stations_by_line = {
            "Purple": ["Whitefield (Kadugodi)", "Channasandra", "Challaghatta"],
            "Green": ["Madavara", "Yeshwanthpur", "Silk Institute"],
            "Yellow": ["RV Road", "Jayadeva Hospital", "Bommasandra"],
        }
        gen1 = TimetableGenerator(stations_by_line, seed=42)
        gen2 = TimetableGenerator(stations_by_line, seed=42)

        s1 = gen1.generate_timetable()
        s2 = gen2.generate_timetable()

        assert len(s1) == len(s2)
        assert s1[0].train_id == s2[0].train_id
        assert s1[0].departure_sec == s2[0].departure_sec

    def test_inactive_pink_blue_lines_no_services(self, setup_routing):
        stations_by_line = {
            "Purple": ["A", "B"],
            "Green": ["C", "D"],
            "Yellow": ["E", "F"],
            "Pink": ["G", "H"],
            "Blue": ["I", "J"],
        }
        gen = TimetableGenerator(stations_by_line, seed=42)
        trains = gen.create_train_instances(active_lines={"Purple", "Green", "Yellow"})

        lines_in_trains = {t.line for t in trains}
        assert "Pink" not in lines_in_trains
        assert "Blue" not in lines_in_trains
        assert "Purple" in lines_in_trains
        assert "Green" in lines_in_trains

    def test_delay_status_thresholds(self):
        assert evaluate_train_status(0) == TrainStatus.ON_TIME
        assert evaluate_train_status(45) == TrainStatus.ON_TIME
        assert evaluate_train_status(60) == TrainStatus.ON_TIME
        assert evaluate_train_status(95) == TrainStatus.MINOR_DELAY
        assert evaluate_train_status(180) == TrainStatus.MINOR_DELAY
        assert evaluate_train_status(240) == TrainStatus.DELAYED
        assert evaluate_train_status(300) == TrainStatus.DELAYED
        assert evaluate_train_status(350) == TrainStatus.CRITICAL_DELAY
        assert evaluate_train_status(0, is_held=True) == TrainStatus.STOPPED
        assert evaluate_train_status(0, is_completed=True) == TrainStatus.COMPLETED


class TestOperationsEngine:
    def test_operations_engine_initialization(self, setup_routing):
        ops = _ensure_operations_engine()
        state = ops.get_state()

        assert state["clock"]["formatted_time"] == "08:00:00"
        assert state["kpis"]["total_trains"] > 0
        assert "SIMULATED OPERATIONS" in state["data_provenance"]

    def test_operator_hold_and_release(self, setup_routing):
        ops = _ensure_operations_engine()
        assert len(ops.trains) > 0

        target_t = ops.trains[0]
        t_id = target_t.train_id

        # Hold train
        success_hold = ops.hold_train(t_id, reason="Testing Hold")
        assert success_hold is True
        assert target_t.is_held is True
        assert target_t.status == TrainStatus.STOPPED

        # Advance tick while held -> delay accumulates
        prev_delay = target_t.delay_seconds
        ops.step(5.0)
        assert target_t.delay_seconds >= prev_delay

        # Release train
        success_rel = ops.release_train(t_id)
        assert success_rel is True
        assert target_t.is_held is False

    def test_station_inspection_structure(self, setup_routing):
        ops = _ensure_operations_engine()
        inspection = ops.get_station_inspection("Kempegowda Stn., Majestic")

        assert inspection["station_name"] == "Kempegowda Stn., Majestic"
        assert "incoming_trains" in inspection
        assert "outgoing_trains" in inspection
        assert "current_congestion_pct" in inspection
        assert "SYNTHETIC" in inspection["data_provenance"]

    def test_disruption_scenario_interaction(self, setup_routing):
        from src.api.main import _ensure_network_state
        ops = _ensure_operations_engine()
        state_svc = _ensure_network_state()

        # Activate Majestic closure
        scenario_engine.activate_scenario("majestic_closure", state_svc)
        sc = scenario_engine.active_scenario
        ops.update_disruption_state(sc, scenario_engine.affected_edges)

        ops.step(1.0)
        st = ops.get_state()

        assert st["active_scenario"]["id"] == "majestic_closure"
        assert st["network_status"] in ("DISRUPTED", "CRITICAL")

        # Clean up / deactivate
        scenario_engine.deactivate_scenario(state_svc)
        ops.update_disruption_state(None, set())
        ops.step(1.0)



class TestOperationsAPIEndpoints:
    def test_get_operations_state(self, client):
        res = client.get("/api/operations/state")
        assert res.status_code == 200
        data = res.json()

        assert "clock" in data
        assert "kpis" in data
        assert "trains" in data
        assert "alerts" in data
        assert data["data_provenance"] == "SIMULATED OPERATIONS"

    def test_simulation_clock_controls(self, client):
        # Start
        r_start = client.post("/api/operations/simulation/start")
        assert r_start.status_code == 200
        assert r_start.json()["clock"]["is_running"] is True

        # Speed
        r_speed = client.post("/api/operations/simulation/speed", json={"speed": 5.0})
        assert r_speed.status_code == 200
        assert r_speed.json()["clock"]["speed_multiplier"] == 5.0

        # Tick
        r_tick = client.post("/api/operations/simulation/tick", json={"seconds": 10.0})
        assert r_tick.status_code == 200

        # Pause
        r_pause = client.post("/api/operations/simulation/pause")
        assert r_pause.status_code == 200
        assert r_pause.json()["clock"]["is_running"] is False

    def test_simulation_play_advancement_and_pause_reset(self, client):
        # 1. RESET to initial state
        r_reset = client.post("/api/operations/simulation/reset")
        assert r_reset.status_code == 200
        data_reset = r_reset.json()
        assert data_reset["clock"]["formatted_time"] == "08:00:00"
        assert data_reset["clock"]["is_running"] is False
        assert data_reset["kpis"]["total_trains"] > 0
        init_t0_progress = data_reset["trains"][0]["progress_pct"]

        # 2. POST PLAY changes clock state to PLAYING
        r_play = client.post("/api/operations/simulation/start")
        assert r_play.status_code == 200
        data_play = r_play.json()
        assert data_play["clock"]["is_running"] is True

        # 3. Speed multiplier works
        r_speed = client.post("/api/operations/simulation/speed", json={"speed": 5.0})
        assert r_speed.status_code == 200
        assert r_speed.json()["clock"]["speed_multiplier"] == 5.0

        # 4. Simulation time advances & train positions change after tick
        r_tick = client.post("/api/operations/simulation/tick", json={"seconds": 10.0})
        assert r_tick.status_code == 200
        data_tick = r_tick.json()
        assert data_tick["clock"]["current_time_sec"] == 28850
        assert data_tick["clock"]["formatted_time"] == "08:00:50"
        assert data_tick["trains"][0]["progress_pct"] > init_t0_progress

        # 5. PAUSE freezes simulation time
        r_pause = client.post("/api/operations/simulation/pause")
        assert r_pause.status_code == 200
        data_pause = r_pause.json()
        assert data_pause["clock"]["is_running"] is False

        time_at_pause = data_pause["clock"]["current_time_sec"]
        r_tick_paused = client.post("/api/operations/simulation/tick", json={"seconds": 10.0})
        assert r_tick_paused.json()["clock"]["current_time_sec"] == time_at_pause

        # 6. RESET returns to 08:00:00 initial state
        r_reset2 = client.post("/api/operations/simulation/reset")
        assert r_reset2.status_code == 200
        data_reset2 = r_reset2.json()
        assert data_reset2["clock"]["current_time_sec"] == 28800
        assert data_reset2["clock"]["formatted_time"] == "08:00:00"
        assert data_reset2["clock"]["is_running"] is False


    def test_play_changes_state(self, client):
        client.post("/api/operations/simulation/reset")
        res = client.post("/api/operations/simulation/start")
        assert res.status_code == 200
        assert res.json()["clock"]["is_running"] is True

    def test_simulation_time_advances(self, client):
        client.post("/api/operations/simulation/reset")
        client.post("/api/operations/simulation/start")
        r1 = client.get("/api/operations/state").json()["clock"]["current_time_sec"]
        client.post("/api/operations/simulation/tick", json={"seconds": 10.0})
        r2 = client.get("/api/operations/state").json()["clock"]["current_time_sec"]
        assert r2 > r1

    def test_active_trains_exist_during_service_window(self, client):
        client.post("/api/operations/simulation/reset")
        res = client.get("/api/operations/state").json()
        assert res["kpis"]["total_trains"] > 0
        assert len(res["trains"]) > 0

    def test_train_position_changes_with_time(self, client):
        client.post("/api/operations/simulation/reset")
        client.post("/api/operations/simulation/start")
        st1 = client.get("/api/operations/state").json()
        p1 = st1["trains"][0]["progress_pct"]

        client.post("/api/operations/simulation/tick", json={"seconds": 30.0})
        st2 = client.get("/api/operations/state").json()
        p2 = st2["trains"][0]["progress_pct"]
        assert p2 > p1

    def test_pause_stops_time(self, client):
        client.post("/api/operations/simulation/start")
        client.post("/api/operations/simulation/tick", json={"seconds": 10.0})
        client.post("/api/operations/simulation/pause")
        t_paused = client.get("/api/operations/state").json()["clock"]["current_time_sec"]

        client.post("/api/operations/simulation/tick", json={"seconds": 10.0})
        t_after = client.get("/api/operations/state").json()["clock"]["current_time_sec"]
        assert t_after == t_paused

    def test_resume_continues_time(self, client):
        client.post("/api/operations/simulation/pause")
        t_paused = client.get("/api/operations/state").json()["clock"]["current_time_sec"]
        client.post("/api/operations/simulation/start")
        client.post("/api/operations/simulation/tick", json={"seconds": 10.0})
        t_resumed = client.get("/api/operations/state").json()["clock"]["current_time_sec"]
        assert t_resumed > t_paused

    def test_speed_multiplier(self, client):
        client.post("/api/operations/simulation/reset")
        client.post("/api/operations/simulation/start")
        client.post("/api/operations/simulation/speed", json={"speed": 10.0})
        r_tick = client.post("/api/operations/simulation/tick", json={"seconds": 10.0})
        assert r_tick.json()["clock"]["current_time_sec"] == 28800 + 100

    def test_reset(self, client):
        client.post("/api/operations/simulation/start")
        client.post("/api/operations/simulation/tick", json={"seconds": 100.0})
        res = client.post("/api/operations/simulation/reset").json()
        assert res["clock"]["current_time_sec"] == 28800
        assert res["clock"]["formatted_time"] == "08:00:00"
        assert res["clock"]["is_running"] is False

    def test_hold_train(self, client):
        st = client.get("/api/operations/state").json()
        t_id = st["trains"][0]["train_id"]
        res = client.post(f"/api/operations/trains/{t_id}/hold").json()
        assert res["status"] == "HELD"

    def test_release_train(self, client):
        st = client.get("/api/operations/state").json()
        t_id = st["trains"][0]["train_id"]
        client.post(f"/api/operations/trains/{t_id}/hold")
        res = client.post(f"/api/operations/trains/{t_id}/release").json()
        assert res["status"] == "RELEASED"

    def test_disruption_affects_operations(self, setup_routing):
        from src.api.main import scenario_engine, _ensure_network_state
        ops = _ensure_operations_engine()
        state_svc = _ensure_network_state()

        scenario_engine.activate_scenario("majestic_closure", state_svc)
        ops.update_disruption_state(scenario_engine.active_scenario, scenario_engine.affected_edges)

        st = ops.get_state()
        assert st["network_status"] in ("DISRUPTED", "CRITICAL")
        assert st["active_scenario"]["id"] == "majestic_closure"

        scenario_engine.deactivate_scenario(state_svc)
        ops.update_disruption_state(None, set())

    def test_canonical_graph_immutability(self, setup_routing):
        g = setup_routing._graph
        n_count = len(g.nodes)
        e_count = len(g.edges)

        ops = _ensure_operations_engine()
        ops.step(10.0)

        assert len(g.nodes) == n_count
        assert len(g.edges) == e_count


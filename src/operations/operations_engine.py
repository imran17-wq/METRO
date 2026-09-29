"""
operations_engine.py — Central Operations Control Center (OCC) Simulation Engine.

Coordinates SimulationClock, timetable generation, directional track sections (UP/DOWN),
safe train separation, train following, station platform occupancy, passenger queue accumulation,
dynamic dwell times, downstream delay propagation, headway monitoring, bunching lifecycle management,
emergent edge congestion, ML forecasts, operator hold/release actions, disruption interactions,
and dynamic OCC alerts feed.

Data Provenance Tags:
- SIMULATED OPERATIONS
- DERIVED SIMULATION OUTPUT
- SYNTHETIC
- SYNTHETIC MODEL OUTPUT
- SIMULATED SCENARIO
"""
from enum import Enum
from typing import Dict, List, Optional, Set

from src.config.settings import DEFAULT_ACTIVE_LINES
from src.operations.alerts import AlertEngine
from src.operations.operational_dynamics import (
    BunchingLifecycleManager,
    calculate_actual_running_time,
    calculate_dynamic_dwell,
    calculate_emergent_congestion,
    calculate_line_headways,
    calculate_passenger_accumulation,
    calculate_station_crowding,
)
from src.operations.simulation_clock import SimulationClock
from src.operations.station_platform import PlatformManager
from src.operations.timetable import TimetableGenerator
from src.operations.track_section import SectionManager
from src.operations.train import Train, TrainStatus, WaitReason, evaluate_train_status


class NetworkOperationStatus(str, Enum):
    NORMAL = "NORMAL"          # 🟢 NORMAL
    DEGRADED = "DEGRADED"      # 🟡 DEGRADED
    DISRUPTED = "DISRUPTED"    # 🟠 DISRUPTED
    CRITICAL = "CRITICAL"      # 🔴 CRITICAL


class OperationsEngine:
    """
    Master OCC Simulation Engine with section-based train following and platform management.
    """

    def __init__(self, station_data_by_line: Dict[str, List[str]], graph=None):
        self.station_data_by_line = station_data_by_line
        self.graph = graph

        self.clock = SimulationClock(start_sec=28800)  # 08:00:00 AM
        self.active_lines: Set[str] = set(DEFAULT_ACTIVE_LINES)
        self.headway_sec: int = 360

        self.timetable_gen = TimetableGenerator(station_data_by_line, seed=42)
        self.section_mgr = SectionManager(station_data_by_line)
        self.platform_mgr = PlatformManager(station_data_by_line)
        self.bunching_lifecycle_mgr = BunchingLifecycleManager()

        self.trains: List[Train] = []
        self.operator_held_trains: Set[str] = set()

        self.alert_engine = AlertEngine()
        self.network_status = NetworkOperationStatus.NORMAL

        # Emergent state stores
        self.emergent_congestion_map: Dict[str, float] = {}
        self.station_crowding_map: Dict[str, Dict] = {}
        self.headway_metrics_list: List[Dict] = []
        self.ml_forecast_alerts: List[Dict] = []

        # Active scenario overlay reference
        self.active_scenario = None
        self.affected_edges: Set[str] = set()

        self.initialize_simulation()

    def initialize_simulation(self, headway_sec: Optional[int] = None):
        """
        Populates timetable, instantiates trains, and builds track sections and platforms.
        """
        if headway_sec is not None:
            self.headway_sec = headway_sec

        self.section_mgr.build_sections(self.station_data_by_line)
        self.platform_mgr.build_platforms(self.station_data_by_line)

        self.trains = self.timetable_gen.create_train_instances(
            active_lines=self.active_lines,
            start_time_sec=28800,
            end_time_sec=34200,
            headway_sec=self.headway_sec,
        )
        self.operator_held_trains.clear()
        self.step(0)  # Evaluate initial 08:00:00 state

    def set_active_lines(self, lines: Set[str], headway_sec: Optional[int] = None):
        self.active_lines = set(lines)
        self.initialize_simulation(headway_sec=headway_sec)

    def update_disruption_state(self, active_scenario, affected_edges: Set[str]):
        """
        Applies active Phase 5 disruption scenario to OCC simulation state and track sections.
        """
        self.active_scenario = active_scenario
        self.affected_edges = set(affected_edges) if affected_edges else set()

        # Update track section blocks
        for sec in self.section_mgr.sections.values():
            sec.blocked = False
            sec.block_reason = None

        if self.active_scenario and self.affected_edges:
            for edge_str in self.affected_edges:
                for sec_id, sec in self.section_mgr.sections.items():
                    if sec.from_station.lower() in edge_str.lower() or sec.to_station.lower() in edge_str.lower():
                        sec.blocked = True
                        sec.block_reason = f"Disruption ({self.active_scenario.name})"

        self._evaluate_network_status()

    def hold_train(self, train_id: str, reason: str = "Operator Command") -> bool:
        for t in self.trains:
            if t.train_id == train_id:
                t.is_held = True
                t.hold_reason = reason
                t.wait_reason = WaitReason.OPERATOR_HOLD.value
                t.update_status()
                self.operator_held_trains.add(train_id)
                self._evaluate_network_status()
                return True
        return False

    def release_train(self, train_id: str) -> bool:
        for t in self.trains:
            if t.train_id == train_id:
                t.is_held = False
                t.hold_reason = None
                t.wait_reason = None
                t.update_status()
                self.operator_held_trains.discard(train_id)
                self._evaluate_network_status()
                return True
        return False

    def step(self, elapsed_seconds: Optional[float] = None):
        """
        Main simulation tick: advances clock, enforces train following, section occupancy,
        platform occupancy, passenger accumulation, dynamic dwell, delay propagation,
        headways, bunching lifecycles, crowding, emergent congestion, and OCC alerts.
        """
        sim_time = self.clock.tick(elapsed_seconds)
        step_elapsed = elapsed_seconds if (elapsed_seconds is not None and elapsed_seconds > 0) else 1.0

        # 1. Accumulate passengers on station platforms
        for line in self.active_lines:
            for st in self.station_data_by_line.get(line, []):
                for d in ("UP", "DOWN"):
                    self.platform_mgr.accumulate_passengers(st, line, d, elapsed_seconds=step_elapsed)

        # 2. Group active trains by line & direction and update leader/follower relationships
        self._update_leader_follower_pointers(sim_time)

        # 3. Process individual train movements with section and platform constraints
        for train in self.trains:
            self._update_single_train(train, sim_time)

        # 4. Monitor headways and detect train bunching
        active_train_dicts = [t.to_dict() for t in self.trains if sim_time_active(t, sim_time)]
        headway_objects = calculate_line_headways(
            active_train_dicts,
            scheduled_headway_sec=self.headway_sec,
            bunching_threshold_sec=self.headway_sec // 2,
        )
        self.headway_metrics_list = [h.to_dict() for h in headway_objects]

        # Update bunching flags on train objects
        hw_map = {h.train_id: h for h in headway_objects}
        bunching_keys = set()
        for t in self.trains:
            if t.train_id in hw_map:
                t.actual_headway_sec = hw_map[t.train_id].actual_headway_sec
                t.headway_deviation_sec = hw_map[t.train_id].headway_deviation_sec
                t.bunching_flag = hw_map[t.train_id].bunching_flag
                if t.bunching_flag:
                    bunching_keys.add(f"{t.line}_{t.direction}")

        # Update bunching alert lifecycle
        lifecycle_events = self.bunching_lifecycle_mgr.update_lifecycle(bunching_keys)

        # 5. Calculate station crowding
        self._update_station_crowding(sim_time)

        # 6. Calculate emergent edge congestion
        self._update_emergent_edge_congestion()

        # 7. Evaluate ML forecast alerts
        self._evaluate_ml_forecasts(sim_time)

        # 8. Evaluate overall network operation status & update prioritized alerts
        self._evaluate_network_status(lifecycle_events=lifecycle_events)

    def _update_leader_follower_pointers(self, sim_time: int):
        by_line_dir: Dict[str, List[Train]] = {}
        for t in self.trains:
            if sim_time_active(t, sim_time):
                key = f"{t.line}_{t.direction}"
                by_line_dir.setdefault(key, []).append(t)

        for key, dir_trains in by_line_dir.items():
            sorted_trains = sorted(
                dir_trains,
                key=lambda x: (x.current_station_idx, x.progress_pct),
                reverse=True  # Ahead train first
            )
            for i, t in enumerate(sorted_trains):
                if i > 0:
                    t.leader_train_id = sorted_trains[i - 1].train_id
                else:
                    t.leader_train_id = None

                if i + 1 < len(sorted_trains):
                    t.following_train_id = sorted_trains[i + 1].train_id
                else:
                    t.following_train_id = None

    def _update_single_train(self, train: Train, sim_time: int):
        # A. Train not yet departed scheduled start
        if sim_time < train.scheduled_departure_sec:
            train.progress_pct = 0.0
            train.current_station_idx = 0
            train.current_station = train.station_sequence[0]
            train.next_station = train.station_sequence[1] if len(train.station_sequence) > 1 else train.station_sequence[0]
            train.delay_seconds = 0
            train.status = TrainStatus.ON_TIME
            train.wait_reason = None
            return

        # B. Train already completed trip
        if train.current_station_idx >= len(train.station_sequence) - 1:
            train.is_completed = True
            train.progress_pct = 1.0
            train.current_station = train.station_sequence[-1]
            train.next_station = train.station_sequence[-1]
            train.current_segment = train.station_sequence[-1]
            train.status = TrainStatus.COMPLETED
            train.wait_reason = None
            if train.current_section_id:
                self.section_mgr.release_section(train.current_section_id, train.train_id)
            return

        curr_idx = train.current_station_idx
        curr_st = train.station_sequence[curr_idx]
        next_st = train.station_sequence[curr_idx + 1]

        curr_sec_id = f"{train.line.upper()}_{train.direction.upper()}_{curr_st.upper()}_{next_st.upper()}"
        next_sec_id = None
        if curr_idx + 2 < len(train.station_sequence):
            nn_st = train.station_sequence[curr_idx + 2]
            next_sec_id = f"{train.line.upper()}_{train.direction.upper()}_{next_st.upper()}_{nn_st.upper()}"

        train.current_section_id = curr_sec_id
        train.next_section_id = next_sec_id

        # Occupy current section
        self.section_mgr.occupy_section(curr_sec_id, train.train_id)

        # C. Check Operational Constraint / Wait Reason
        wait_reason = None

        # 1. Operator Hold
        if train.train_id in self.operator_held_trains:
            train.is_held = True
            if not train.hold_reason:
                train.hold_reason = "Operator Command"
            wait_reason = WaitReason.OPERATOR_HOLD.value

        # 2. Disruption Scenario Block
        elif self.active_scenario and self.affected_edges:
            for edge_str in self.affected_edges:
                if curr_st.lower() in edge_str.lower() or next_st.lower() in edge_str.lower():
                    wait_reason = WaitReason.DISRUPTION.value
                    train.hold_reason = f"Disruption ({self.active_scenario.name})"
                    break

        # 3. Leader Train Separation / Blocked Track Section
        if wait_reason is None and train.leader_train_id:
            leader_train = next((t for t in self.trains if t.train_id == train.leader_train_id), None)
            if leader_train and not leader_train.is_completed:
                # If leader train is in same section or immediately ahead in next section with low progress
                if leader_train.current_section_id == curr_sec_id:
                    wait_reason = WaitReason.INSUFFICIENT_SEPARATION.value
                elif next_sec_id and leader_train.current_section_id == next_sec_id and leader_train.progress_pct < 0.25:
                    wait_reason = WaitReason.INSUFFICIENT_SEPARATION.value

        # 4. Target Station Platform Occupancy
        if wait_reason is None and train.progress_pct >= 0.9:
            if not self.platform_mgr.can_enter_platform(next_st, train.line, train.direction, train.train_id):
                wait_reason = WaitReason.STATION_OCCUPIED.value

        # If constrained, hold physical position and accumulate delay
        if wait_reason is not None:
            train.wait_reason = wait_reason
            train.delay_seconds += 1
            train.update_status()
            return
        else:
            train.wait_reason = None
            if not train.is_held:
                train.hold_reason = None

        # D. Dynamic Organic Movement, Dwell & Running Time Calculation
        sched_arr = train.scheduled_arrivals_sec.get(next_st, train.scheduled_departure_sec + 150)
        sched_dep_prev = train.scheduled_departures_sec.get(curr_st, train.scheduled_departure_sec)
        base_segment_duration = max(60, sched_arr - sched_dep_prev)

        # Dynamic Dwell calculation using accumulated platform queue
        is_interchange = curr_st in ("Majestic", "RV Road", "KR Pura")
        pf = self.platform_mgr.get_platform(curr_st, train.line, train.direction)
        waiting_passengers = pf.waiting_passengers if pf else 30

        st_crowd_pct = self.station_crowding_map.get(curr_st, {}).get("crowding_pct", 30.0)
        demand_ratio = st_crowd_pct / 50.0

        actual_dwell = calculate_dynamic_dwell(
            station_name=curr_st,
            time_slot=(sim_time // 900),
            is_interchange=is_interchange,
            station_demand_ratio=demand_ratio,
            waiting_passengers=waiting_passengers,
            base_dwell_sec=30,
        )

        # Dynamic Controlled Stochastic Running Time
        segment_id = f"{curr_st}_{next_st}"
        current_edge_cong = self.emergent_congestion_map.get(segment_id, 20.0)
        actual_run_time = calculate_actual_running_time(
            base_segment_time_sec=base_segment_duration,
            congestion_pct=current_edge_cong,
            train_id=train.train_id,
            segment_id=segment_id,
            sim_time_sec=sim_time,
            seed=42,
        )

        dwell_delta = actual_dwell - 30
        effective_segment_duration = actual_run_time + dwell_delta

        # Effective start time with inherited downstream delay propagation
        effective_start_time = sched_dep_prev + train.delay_seconds
        elapsed_on_segment = sim_time - effective_start_time

        if elapsed_on_segment < 0:
            train.progress_pct = 0.0
        elif elapsed_on_segment >= effective_segment_duration:
            # Arrival at next station
            self.section_mgr.release_section(curr_sec_id, train.train_id)
            self.platform_mgr.occupy_platform(next_st, train.line, train.direction, train.train_id)
            self.platform_mgr.board_passengers(next_st, train.line, train.direction, max_board=120)

            train.current_station_idx += 1
            train.current_station = next_st

            if train.current_station_idx < len(train.station_sequence) - 1:
                train.next_station = train.station_sequence[train.current_station_idx + 1]
                train.current_segment = f"{train.current_station} -> {train.next_station}"
                train.progress_pct = 0.0
            else:
                train.next_station = next_st
                train.current_segment = next_st
                train.is_completed = True
                train.progress_pct = 1.0

            # Store actual arrival/departure & calculate arrival/departure delays
            train.actual_arrivals_sec[next_st] = sim_time
            sched_arr_time = train.scheduled_arrivals_sec.get(next_st, sim_time)

            train.arrival_delays_sec[next_st] = max(0, sim_time - sched_arr_time)
            train.delay_seconds = train.arrival_delays_sec[next_st]
            self.platform_mgr.release_platform(next_st, train.line, train.direction, train.train_id, sim_time_sec=sim_time)
        else:
            train.progress_pct = max(0.0, min(1.0, elapsed_on_segment / effective_segment_duration))
            train.current_segment = f"{curr_st} -> {next_st}"

        train.update_status()

    def _update_station_crowding(self, sim_time: int):
        time_slot = (sim_time // 900) % 96
        active_counts: Dict[str, int] = {}
        for t in self.trains:
            if sim_time_active(t, sim_time):
                active_counts[t.current_station] = active_counts.get(t.current_station, 0) + 1

        for line, stations in self.station_data_by_line.items():
            if line not in self.active_lines:
                continue
            for st in stations:
                is_interchange = st in ("Majestic", "RV Road", "KR Pura")
                act_cnt = active_counts.get(st, 1)

                pf_up = self.platform_mgr.get_platform(st, line, "UP")
                pf_dn = self.platform_mgr.get_platform(st, line, "DOWN")
                wait_p = (pf_up.waiting_passengers if pf_up else 0) + (pf_dn.waiting_passengers if pf_dn else 0)

                metrics = calculate_station_crowding(
                    station_name=st,
                    is_interchange=is_interchange,
                    active_trains_count=act_cnt,
                    waiting_passengers=wait_p,
                    time_slot=time_slot,
                )
                self.station_crowding_map[st] = metrics.to_dict()

    def _update_emergent_edge_congestion(self):
        for line, stations in self.station_data_by_line.items():
            if line not in self.active_lines:
                continue
            for i in range(len(stations) - 1):
                st_a, st_b = stations[i], stations[i + 1]
                seg_id = f"{st_a}_{st_b}"
                st_crowd = self.station_crowding_map.get(st_a, {}).get("crowding_pct", 30.0)

                seg_bunching = False
                max_delay = 0
                for t in self.trains:
                    if t.current_station == st_a and t.next_station == st_b:
                        if t.bunching_flag:
                            seg_bunching = True
                        if t.delay_seconds > max_delay:
                            max_delay = t.delay_seconds

                base_cong = 45.0 if self.active_scenario else 25.0
                emergent_cong = calculate_emergent_congestion(
                    base_congestion_pct=base_cong,
                    station_crowding_pct=st_crowd,
                    headway_bunching=seg_bunching,
                    delay_seconds=max_delay,
                )
                self.emergent_congestion_map[seg_id] = emergent_cong

    def _evaluate_ml_forecasts(self, sim_time: int):
        self.ml_forecast_alerts.clear()
        for st, c_dict in self.station_crowding_map.items():
            pct = c_dict.get("crowding_pct", 0.0)
            if pct >= 78.0:
                self.ml_forecast_alerts.append({
                    "target": st,
                    "horizon_min": 15,
                    "predicted_val": round(min(98.0, pct + 12.0), 1),
                })

    def _evaluate_network_status(self, lifecycle_events: Optional[List[Dict]] = None):
        sim_time = int(round(self.clock.current_time_sec))

        if self.active_scenario:
            self.network_status = NetworkOperationStatus.CRITICAL
            active_trains = [t for t in self.trains if sim_time_active(t, sim_time)]
            train_dicts = [t.to_dict() for t in active_trains if t.status != TrainStatus.COMPLETED]
            self.alert_engine.generate_alerts(
                formatted_time=self.clock.formatted_time(),
                active_scenario_name=self.active_scenario.name,
                trains=train_dicts,
                bunching_lifecycle_events=lifecycle_events,
                station_crowding_list=list(self.station_crowding_map.values()),
                forecast_alerts=self.ml_forecast_alerts,
            )
            return

        active_trains = [t for t in self.trains if sim_time_active(t, sim_time)]
        total = len(active_trains)

        if not total:
            self.network_status = NetworkOperationStatus.NORMAL
            return

        stopped_count = sum(1 for t in active_trains if t.is_held or t.wait_reason is not None or t.status in (TrainStatus.STOPPED, TrainStatus.HELD))
        delayed_count = sum(1 for t in active_trains if t.status in (TrainStatus.MINOR_DELAY, TrainStatus.DELAYED, TrainStatus.CRITICAL_DELAY))
        bunching_count = sum(1 for h in self.headway_metrics_list if h.get("bunching_flag"))

        if stopped_count > 2 or (delayed_count / total) > 0.4 or bunching_count >= 3:
            self.network_status = NetworkOperationStatus.CRITICAL
        elif (delayed_count / total) > 0.25 or stopped_count > 0 or bunching_count > 0:
            self.network_status = NetworkOperationStatus.DISRUPTED
        elif (delayed_count / total) > 0.1:
            self.network_status = NetworkOperationStatus.DEGRADED
        else:
            self.network_status = NetworkOperationStatus.NORMAL

        train_dicts = [t.to_dict() for t in active_trains if t.status != TrainStatus.COMPLETED]
        self.alert_engine.generate_alerts(
            formatted_time=self.clock.formatted_time(),
            active_scenario_name=None,
            trains=train_dicts,
            bunching_lifecycle_events=lifecycle_events,
            station_crowding_list=list(self.station_crowding_map.values()),
            forecast_alerts=self.ml_forecast_alerts,
        )

    def get_state(self) -> Dict:
        if self.clock.is_running:
            self.step()

        sim_time = int(round(self.clock.current_time_sec))
        active_trains = [t for t in self.trains if sim_time_active(t, sim_time)]
        train_dicts = [t.to_dict() for t in active_trains]

        total_trains = len(active_trains)
        on_time = sum(1 for t in active_trains if t.status == TrainStatus.ON_TIME)
        delayed = sum(1 for t in active_trains if t.status in (TrainStatus.MINOR_DELAY, TrainStatus.DELAYED, TrainStatus.CRITICAL_DELAY))
        stopped = sum(1 for t in active_trains if t.is_held or t.wait_reason is not None or t.status in (TrainStatus.STOPPED, TrainStatus.HELD))
        bunching_count = sum(1 for h in self.headway_metrics_list if h.get("bunching_flag"))

        status_badge_map = {
            NetworkOperationStatus.NORMAL: "🟢 NORMAL",
            NetworkOperationStatus.DEGRADED: "🟡 DEGRADED",
            NetworkOperationStatus.DISRUPTED: "🟠 DISRUPTED",
            NetworkOperationStatus.CRITICAL: "🔴 CRITICAL",
        }

        sections_list = [sec.to_dict() for sec in self.section_mgr.sections.values() if sec.occupied_by or sec.blocked]

        return {
            "clock": self.clock.to_dict(),
            "network_status": self.network_status.value,
            "network_status_badge": status_badge_map[self.network_status],
            "active_scenario": self.active_scenario.to_dict() if self.active_scenario else None,
            "kpis": {
                "total_trains": total_trains,
                "on_time": on_time,
                "delayed": delayed,
                "stopped": stopped,
                "bunching_trains": bunching_count,
                "active_incidents": 1 if self.active_scenario else 0,
                "high_congestion_areas": sum(1 for c in self.emergent_congestion_map.values() if c >= 70.0),
            },
            "trains": train_dicts,
            "sections": sections_list,
            "headways": self.headway_metrics_list,
            "alerts": [a.to_dict() for a in self.alert_engine.alerts],
            "data_provenance": "SIMULATED OPERATIONS",
        }

    def get_station_inspection(self, station_name: str) -> Dict:
        sim_time = int(round(self.clock.current_time_sec))
        incoming = []
        outgoing = []

        for t in self.trains:
            if not sim_time_active(t, sim_time):
                continue
            if t.next_station.lower() == station_name.lower():
                incoming.append(t.to_dict())
            elif t.current_station.lower() == station_name.lower():
                outgoing.append(t.to_dict())

        st_crowd = self.station_crowding_map.get(station_name, {})
        is_inc = self.active_scenario and station_name.lower() in str(self.active_scenario.target).lower()

        current_cong = st_crowd.get("crowding_pct", 45.0) if not is_inc else 82.5
        predicted_cong = round(min(98.0, current_cong + 12.0), 1)

        return {
            "station_name": station_name,
            "incoming_trains": incoming,
            "outgoing_trains": outgoing,
            "platform_demand": st_crowd.get("crowding_band", "MODERATE") if not is_inc else "HIGH",
            "current_congestion_pct": round(current_cong, 1),
            "predicted_congestion_15min_pct": predicted_cong,
            "next_train_eta": incoming[0]["expected_arrival_next"] if incoming else "08:12:00",
            "active_incidents": [self.active_scenario.name] if is_inc else [],
            "data_provenance": "SYNTHETIC & SYNTHETIC MODEL OUTPUT",
        }


def sim_time_active(train: Train, curr_sim_sec: int) -> bool:
    return train.scheduled_departure_sec <= curr_sim_sec and not train.is_completed

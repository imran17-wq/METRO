"""
operational_dynamics.py — Operational Dynamics & Emergent Behavior Engine.

Calculates dynamic dwell times, controlled stochastic running times, headway monitoring,
train bunching detection, station crowding, passenger accumulation feedback loop,
bunching alert lifecycle (DETECTED, PERSISTING, CLEARED), and emergent edge congestion.

Data Provenance Tags:
- SIMULATED OPERATIONS
- DERIVED SIMULATION OUTPUT
- SYNTHETIC
- SYNTHETIC MODEL OUTPUT
"""
import hashlib
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class HeadwayMetrics:
    line: str
    direction: str
    train_id: str
    preceding_train_id: Optional[str]
    scheduled_headway_sec: int
    actual_headway_sec: int
    headway_deviation_sec: int
    bunching_flag: bool
    data_provenance: str = "DERIVED SIMULATION OUTPUT"

    def to_dict(self) -> Dict:
        return {
            "line": self.line,
            "direction": self.direction,
            "train_id": self.train_id,
            "preceding_train_id": self.preceding_train_id,
            "scheduled_headway_sec": self.scheduled_headway_sec,
            "actual_headway_sec": self.actual_headway_sec,
            "headway_deviation_sec": self.headway_deviation_sec,
            "bunching_flag": self.bunching_flag,
            "data_provenance": self.data_provenance,
        }


@dataclass
class StationCrowdingMetrics:
    station_name: str
    platform_load: int
    station_capacity: int
    crowding_pct: float
    crowding_band: str  # "LOW", "MODERATE", "HIGH", "CRITICAL"
    data_provenance: str = "DERIVED SIMULATION OUTPUT"

    def to_dict(self) -> Dict:
        return {
            "station_name": self.station_name,
            "platform_load": self.platform_load,
            "station_capacity": self.station_capacity,
            "crowding_pct": round(self.crowding_pct, 1),
            "crowding_band": self.crowding_band,
            "data_provenance": self.data_provenance,
        }


class BunchingLifecycleManager:
    """
    Manages explicit alert lifecycle for train bunching:
    DETECTED -> PERSISTING -> CLEARED
    Prevents duplicate tick alert spamming.
    """

    def __init__(self):
        self.active_bunching_states: Dict[str, str] = {}  # key -> status ("DETECTED", "PERSISTING")

    def update_lifecycle(self, current_bunching_keys: Set[str]) -> List[Dict]:
        events = []

        # 1. Check for cleared bunching conditions
        for key in list(self.active_bunching_states.keys()):
            if key not in current_bunching_keys:
                del self.active_bunching_states[key]
                line, direction = key.split("_", 1)
                events.append({
                    "event": "CLEARED",
                    "key": key,
                    "line": line,
                    "direction": direction,
                })

        # 2. Check for newly detected or persisting bunching conditions
        for key in current_bunching_keys:
            line, direction = key.split("_", 1)
            if key not in self.active_bunching_states:
                self.active_bunching_states[key] = "DETECTED"
                events.append({
                    "event": "DETECTED",
                    "key": key,
                    "line": line,
                    "direction": direction,
                })
            else:
                self.active_bunching_states[key] = "PERSISTING"
                events.append({
                    "event": "PERSISTING",
                    "key": key,
                    "line": line,
                    "direction": direction,
                })

        return events


def calculate_passenger_accumulation(service_gap_sec: float, rate_per_sec: float = 0.5) -> int:
    """
    Calculates accumulated waiting passengers on platform during service delay gaps.
    """
    return int(round(max(0.0, service_gap_sec) * rate_per_sec))


def calculate_dynamic_dwell(
    station_name: str,
    time_slot: int = 36,
    is_interchange: bool = False,
    station_demand_ratio: float = 0.5,
    waiting_passengers: int = 40,
    base_dwell_sec: int = 30,
) -> int:
    """
    Calculates dynamic station dwell time based on passenger load and waiting queue:
    actual_dwell = base_dwell + boarding_penalty + alighting_penalty + interchange_penalty
    """
    ratio = max(0.0, station_demand_ratio)

    boarding_penalty = int(round(ratio * 20)) + int(round((waiting_passengers / 50.0) * 8.0))
    alighting_penalty = int(round(ratio * 10))
    interchange_penalty = 10 if is_interchange else 0

    total_dwell = base_dwell_sec + boarding_penalty + alighting_penalty + interchange_penalty
    return min(120, max(base_dwell_sec, total_dwell))


def calculate_actual_running_time(
    base_segment_time_sec: int,
    congestion_pct: float = 0.0,
    train_id: str = "",
    segment_id: str = "",
    sim_time_sec: int = 28800,
    seed: int = 42,
) -> int:
    """
    Calculates actual segment running time with controlled stochastic variation.
    Reproducible via fixed seed and deterministic hashing.
    """
    hash_input = f"{seed}-{train_id}-{segment_id}-{sim_time_sec // 300}".encode('utf-8')
    hash_val = int(hashlib.sha256(hash_input).hexdigest()[:8], 16)
    rng = random.Random(hash_val)

    variation = rng.uniform(-0.05, 0.10)
    congestion_penalty = (min(100.0, max(0.0, congestion_pct)) / 100.0) * 0.20

    multiplier = 1.0 + variation + congestion_penalty
    actual_time = int(round(base_segment_time_sec * multiplier))

    return max(45, actual_time)


def calculate_line_headways(
    trains_on_line: List[Dict],
    scheduled_headway_sec: int = 360,
    bunching_threshold_sec: int = 180,
) -> List[HeadwayMetrics]:
    """
    Calculates actual headway between consecutive trains on a line and flags train bunching.
    """
    results: List[HeadwayMetrics] = []
    if not trains_on_line:
        return results

    by_dir: Dict[str, List[Dict]] = {}
    for t in trains_on_line:
        d = t.get("direction", "UP")
        by_dir.setdefault(d, []).append(t)

    for direction, dir_trains in by_dir.items():
        sorted_trains = sorted(
            dir_trains,
            key=lambda x: (x.get("current_station_idx", 0), x.get("progress_pct", 0.0)),
            reverse=True  # Ahead train first
        )

        for i in range(len(sorted_trains)):
            curr_train = sorted_trains[i]
            t_id = curr_train.get("train_id", "")
            line = curr_train.get("line", "")

            if i + 1 < len(sorted_trains):
                following_train = sorted_trains[i + 1]
                foll_id = following_train.get("train_id")

                sched_gap = scheduled_headway_sec
                delay_gap = curr_train.get("delay_seconds", 0) - following_train.get("delay_seconds", 0)
                actual_hw = max(30, sched_gap - delay_gap)

                dev = actual_hw - scheduled_headway_sec
                bunching = actual_hw <= bunching_threshold_sec

                results.append(
                    HeadwayMetrics(
                        line=line,
                        direction=direction,
                        train_id=foll_id,
                        preceding_train_id=t_id,
                        scheduled_headway_sec=scheduled_headway_sec,
                        actual_headway_sec=actual_hw,
                        headway_deviation_sec=dev,
                        bunching_flag=bunching,
                    )
                )
            else:
                results.append(
                    HeadwayMetrics(
                        line=line,
                        direction=direction,
                        train_id=t_id,
                        preceding_train_id=None,
                        scheduled_headway_sec=scheduled_headway_sec,
                        actual_headway_sec=scheduled_headway_sec,
                        headway_deviation_sec=0,
                        bunching_flag=False,
                    )
                )

    return results


def calculate_station_crowding(
    station_name: str,
    is_interchange: bool = False,
    active_trains_count: int = 1,
    base_passenger_flow: int = 150,
    waiting_passengers: int = 40,
    time_slot: int = 36,
) -> StationCrowdingMetrics:
    """
    Computes platform load, capacity, and station crowding percentage organically.
    """
    capacity = 1200 if is_interchange else 600

    is_peak = (32 <= time_slot <= 40) or (68 <= time_slot <= 76)
    peak_multiplier = 1.6 if is_peak else 0.8

    platform_load = int(round(base_passenger_flow * peak_multiplier)) + waiting_passengers
    if is_interchange:
        platform_load = int(round(platform_load * 2.5))

    crowding_pct = max(5.0, min(100.0, (platform_load / capacity) * 100.0))

    if crowding_pct < 40.0:
        band = "LOW"
    elif crowding_pct < 70.0:
        band = "MODERATE"
    elif crowding_pct < 88.0:
        band = "HIGH"
    else:
        band = "CRITICAL"

    return StationCrowdingMetrics(
        station_name=station_name,
        platform_load=platform_load,
        station_capacity=capacity,
        crowding_pct=crowding_pct,
        crowding_band=band,
    )


def calculate_emergent_congestion(
    base_congestion_pct: float,
    station_crowding_pct: float = 30.0,
    headway_bunching: bool = False,
    delay_seconds: int = 0,
) -> float:
    """
    Derives dynamic track segment congestion from passenger flow, station crowding,
    headway irregularity, and delay propagation.
    """
    crowding_contrib = (station_crowding_pct - 30.0) * 0.25
    bunching_contrib = 15.0 if headway_bunching else 0.0
    delay_contrib = min(20.0, (delay_seconds / 60.0) * 4.0)

    emergent_pct = base_congestion_pct + crowding_contrib + bunching_contrib + delay_contrib
    return max(0.0, min(100.0, round(emergent_pct, 1)))

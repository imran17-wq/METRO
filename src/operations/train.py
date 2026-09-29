"""
train.py — Train Data Model and Movement Tracker for Namma Pulse OCC.

Tracks train entity status, position, segment progress, section occupancy,
leader/follower relationships, wait reasons, dwell time, headway metrics,
delay propagation, and explicit data provenance.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TrainStatus(str, Enum):
    ON_TIME = "ON_TIME"
    MINOR_DELAY = "MINOR_DELAY"
    DELAYED = "DELAYED"
    CRITICAL_DELAY = "CRITICAL_DELAY"
    STOPPED = "STOPPED"
    HELD = "HELD"
    COMPLETED = "COMPLETED"


class WaitReason(str, Enum):
    INSUFFICIENT_SEPARATION = "INSUFFICIENT_SEPARATION"
    BLOCKED_BY_TRAIN = "BLOCKED_BY_TRAIN"
    STATION_OCCUPIED = "STATION_OCCUPIED"
    OPERATOR_HOLD = "OPERATOR_HOLD"
    DISRUPTION = "DISRUPTION"


def evaluate_train_status(
    delay_seconds: int,
    is_held: bool = False,
    wait_reason: Optional[str] = None,
    is_completed: bool = False
) -> TrainStatus:
    """
    Evaluates train status based on delay seconds and operational state.
    """
    if is_completed:
        return TrainStatus.COMPLETED
    if is_held:
        return TrainStatus.STOPPED
    if wait_reason is not None:
        return TrainStatus.HELD
    if delay_seconds <= 60:
        return TrainStatus.ON_TIME
    elif delay_seconds <= 180:
        return TrainStatus.MINOR_DELAY
    elif delay_seconds <= 300:
        return TrainStatus.DELAYED
    else:
        return TrainStatus.CRITICAL_DELAY


@dataclass
class Train:
    """
    A simulated metro train unit.
    """
    train_id: str
    line: str
    direction: str  # "UP" or "DOWN"
    origin_station: str
    destination_station: str
    station_sequence: List[str]

    scheduled_departure_sec: int  # Seconds from midnight (e.g. 08:00:00 = 28800)
    scheduled_arrivals_sec: Dict[str, int] = field(default_factory=dict)
    scheduled_departures_sec: Dict[str, int] = field(default_factory=dict)

    # Simulated/Actual tracking (seconds from midnight)
    simulated_arrivals_sec: Dict[str, int] = field(default_factory=dict)
    simulated_departures_sec: Dict[str, int] = field(default_factory=dict)
    actual_arrivals_sec: Dict[str, int] = field(default_factory=dict)
    actual_departures_sec: Dict[str, int] = field(default_factory=dict)

    # Station delay tracking
    arrival_delays_sec: Dict[str, int] = field(default_factory=dict)
    departure_delays_sec: Dict[str, int] = field(default_factory=dict)

    # Section & train-following attributes
    current_section_id: Optional[str] = None
    next_section_id: Optional[str] = None
    leader_train_id: Optional[str] = None
    following_train_id: Optional[str] = None
    wait_reason: Optional[str] = None

    # Headway & bunching metrics
    actual_headway_sec: int = 360
    headway_deviation_sec: int = 0
    bunching_flag: bool = False

    current_station_idx: int = 0
    current_station: str = ""
    next_station: str = ""
    current_segment: str = ""
    progress_pct: float = 0.0

    delay_seconds: int = 0
    status: TrainStatus = TrainStatus.ON_TIME

    is_held: bool = False
    hold_reason: Optional[str] = None
    is_completed: bool = False

    data_provenance: str = "SIMULATED OPERATIONS"
    delay_provenance: str = "DERIVED SIMULATION OUTPUT"

    def __post_init__(self):
        if self.station_sequence:
            self.current_station = self.station_sequence[0]
            self.next_station = self.station_sequence[1] if len(self.station_sequence) > 1 else self.station_sequence[0]
            if len(self.station_sequence) > 1:
                self.current_segment = f"{self.station_sequence[0]} -> {self.station_sequence[1]}"
                self.current_section_id = f"{self.line.upper()}_{self.direction.upper()}_{self.current_station.upper()}_{self.next_station.upper()}"
            else:
                self.current_segment = self.station_sequence[0]

    def update_status(self):
        self.status = evaluate_train_status(
            delay_seconds=self.delay_seconds,
            is_held=self.is_held,
            wait_reason=self.wait_reason,
            is_completed=self.is_completed,
        )

    def to_dict(self) -> Dict:
        def sec_to_time(sec: int) -> str:
            h = (sec // 3600) % 24
            m = (sec % 3600) // 60
            s = sec % 60
            return f"{h:02d}:{m:02d}:{s:02d}"

        return {
            "train_id": self.train_id,
            "line": self.line,
            "direction": self.direction,
            "origin_station": self.origin_station,
            "destination_station": self.destination_station,
            "current_station_idx": self.current_station_idx,
            "current_station": self.current_station,
            "next_station": self.next_station,
            "current_segment": self.current_segment,
            "current_section_id": self.current_section_id,
            "next_section_id": self.next_section_id,
            "leader_train_id": self.leader_train_id,
            "following_train_id": self.following_train_id,
            "wait_reason": self.wait_reason,
            "progress_pct": round(self.progress_pct, 3),
            "scheduled_departure": sec_to_time(self.scheduled_departure_sec),
            "scheduled_arrival_next": sec_to_time(self.scheduled_arrivals_sec.get(self.next_station, self.scheduled_departure_sec)),
            "expected_arrival_next": sec_to_time(self.scheduled_arrivals_sec.get(self.next_station, self.scheduled_departure_sec) + self.delay_seconds),
            "actual_headway_sec": self.actual_headway_sec,
            "headway_deviation_sec": self.headway_deviation_sec,
            "bunching_flag": self.bunching_flag,
            "delay_seconds": self.delay_seconds,
            "delay_formatted": f"+{self.delay_seconds // 60} min" if self.delay_seconds >= 60 else f"{self.delay_seconds}s",
            "status": self.status.value,
            "is_held": self.is_held,
            "hold_reason": self.hold_reason,
            "is_completed": self.is_completed,
            "data_provenance": self.data_provenance,
            "delay_provenance": self.delay_provenance,
        }

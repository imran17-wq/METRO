"""
station_platform.py — Station Platform Occupancy & Passenger Queue Manager for Namma Pulse OCC.

Models platform availability per station, line, and direction (AVAILABLE, DWELLING, OCCUPIED, BLOCKED),
and manages passenger queue accumulation when train arrivals are delayed.

Data Provenance Tag: DERIVED SIMULATION OUTPUT
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class PlatformStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DWELLING = "DWELLING"
    OCCUPIED = "OCCUPIED"
    BLOCKED = "BLOCKED"


@dataclass
class StationPlatform:
    station_name: str
    line: str
    direction: str  # "UP" or "DOWN"
    status: PlatformStatus = PlatformStatus.AVAILABLE
    occupied_by_train: Optional[str] = None
    platform_capacity: int = 600
    waiting_passengers: int = 40
    last_service_time_sec: int = 28800
    blocked: bool = False
    data_provenance: str = "DERIVED SIMULATION OUTPUT"

    @property
    def occupancy_pct(self) -> float:
        return max(0.0, min(100.0, (self.waiting_passengers / self.platform_capacity) * 100.0))

    def to_dict(self) -> Dict:
        return {
            "station_name": self.station_name,
            "line": self.line,
            "direction": self.direction,
            "status": self.status.value,
            "occupied_by_train": self.occupied_by_train,
            "platform_capacity": self.platform_capacity,
            "waiting_passengers": self.waiting_passengers,
            "occupancy_pct": round(self.occupancy_pct, 1),
            "blocked": self.blocked,
            "data_provenance": self.data_provenance,
        }


class PlatformManager:
    """
    Manages platform occupancy and dynamic passenger queues across the metro network.
    """

    def __init__(self, station_data_by_line: Dict[str, List[str]]):
        self.platforms: Dict[str, StationPlatform] = {}
        self.build_platforms(station_data_by_line)

    def _make_key(self, station_name: str, line: str, direction: str) -> str:
        return f"{station_name.upper()}_{line.upper()}_{direction.upper()}"

    def build_platforms(self, station_data_by_line: Dict[str, List[str]]):
        self.platforms.clear()
        for line, stations in station_data_by_line.items():
            for st in stations:
                is_interchange = st in ("Majestic", "RV Road", "KR Pura")
                cap = 1200 if is_interchange else 600

                for direction in ("UP", "DOWN"):
                    key = self._make_key(st, line, direction)
                    self.platforms[key] = StationPlatform(
                        station_name=st,
                        line=line,
                        direction=direction,
                        platform_capacity=cap,
                        waiting_passengers=30 if is_interchange else 15,
                    )

    def get_platform(self, station_name: str, line: str, direction: str) -> Optional[StationPlatform]:
        key = self._make_key(station_name, line, direction)
        return self.platforms.get(key)

    def can_enter_platform(self, station_name: str, line: str, direction: str, train_id: str) -> bool:
        pf = self.get_platform(station_name, line, direction)
        if not pf:
            return True
        if pf.blocked:
            return False
        if pf.occupied_by_train is not None and pf.occupied_by_train != train_id:
            return False
        return True

    def occupy_platform(self, station_name: str, line: str, direction: str, train_id: str) -> bool:
        pf = self.get_platform(station_name, line, direction)
        if not pf or not self.can_enter_platform(station_name, line, direction, train_id):
            return False
        pf.status = PlatformStatus.DWELLING
        pf.occupied_by_train = train_id
        return True

    def release_platform(self, station_name: str, line: str, direction: str, train_id: str, sim_time_sec: int = 28800):
        pf = self.get_platform(station_name, line, direction)
        if pf and pf.occupied_by_train == train_id:
            pf.status = PlatformStatus.AVAILABLE
            pf.occupied_by_train = None
            pf.last_service_time_sec = sim_time_sec

    def accumulate_passengers(self, station_name: str, line: str, direction: str, elapsed_seconds: float, rate_per_sec: float = 0.4):
        pf = self.get_platform(station_name, line, direction)
        if pf:
            new_passengers = int(round(elapsed_seconds * rate_per_sec))
            pf.waiting_passengers = min(pf.platform_capacity, pf.waiting_passengers + new_passengers)

    def board_passengers(self, station_name: str, line: str, direction: str, max_board: int = 100) -> int:
        pf = self.get_platform(station_name, line, direction)
        if not pf:
            return 0
        boarded = min(pf.waiting_passengers, max_board)
        pf.waiting_passengers -= boarded
        return boarded

"""
src/simulation/disruption.py

Typed disruption models for Phase 5 Disruption Simulation & Network Resilience.
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class DisruptionType(str, Enum):
    STATION_CLOSURE = "STATION_CLOSURE"
    LINE_CLOSURE = "LINE_CLOSURE"
    EDGE_CLOSURE = "EDGE_CLOSURE"
    SEVERE_DELAY = "SEVERE_DELAY"
    CONGESTION_SURGE = "CONGESTION_SURGE"
    INTERCHANGE_CLOSURE = "INTERCHANGE_CLOSURE"
    DEMAND_SURGE = "DEMAND_SURGE"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Disruption:
    """
    A single disruption specification affecting network state.
    """
    id: str
    name: str
    type: DisruptionType
    severity: Severity
    description: str
    start_time: str = "00:00"
    end_time: str = "23:59"
    affected_lines: List[str] = field(default_factory=list)
    affected_stations: List[str] = field(default_factory=list)
    affected_edges: List[str] = field(default_factory=list)
    active: bool = True
    delay_multiplier: float = 1.0
    congestion_multiplier: float = 1.0
    demand_multiplier: float = 1.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value if isinstance(self.type, Enum) else self.type,
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "affected_lines": self.affected_lines,
            "affected_stations": self.affected_stations,
            "affected_edges": self.affected_edges,
            "active": self.active,
            "delay_multiplier": self.delay_multiplier,
            "congestion_multiplier": self.congestion_multiplier,
            "demand_multiplier": self.demand_multiplier,
        }

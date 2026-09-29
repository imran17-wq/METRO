"""
src/simulation/scenario.py

Scenario model and deterministic Scenario Library for Phase 5 Disruption Simulation.
All scenarios are clearly labeled SIMULATED SCENARIO.
"""
from __future__ import annotations

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.simulation.disruption import Disruption, DisruptionType, Severity
from src.config.simulation_settings import SEVERITY_MULTIPLIERS


logger = logging.getLogger(__name__)


@dataclass
class Scenario:
    """
    A reproducible disruption scenario definition containing one or more disruptions.
    """
    id: str
    name: str
    type: DisruptionType
    target: str                         # Station name, line name, or edge ID
    severity: Severity
    duration_min: int
    description: str
    disruptions: List[Disruption] = field(default_factory=list)
    active: bool = False
    provenance_label: str = "SIMULATED SCENARIO"
    active_lines: Optional[List[str]] = None  # Operational lines active during scenario
    headway_sec: Optional[int] = None         # Train service headway in seconds
    demand_multiplier: float = 1.0           # Scenario demand multiplier

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value if isinstance(self.type, Enum) else self.type,
            "target": self.target,
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "duration_min": self.duration_min,
            "description": self.description,
            "active": self.active,
            "provenance_label": self.provenance_label,
            "disruptions": [d.to_dict() for d in self.disruptions],
            "active_lines": self.active_lines,
            "headway_sec": self.headway_sec,
            "demand_multiplier": self.demand_multiplier,
        }


# ---------------------------------------------------------------------------
# Scenario Library (Pre-Packaged Scenarios)
# ---------------------------------------------------------------------------

SCENARIO_LIBRARY: Dict[str, Scenario] = {
    "current_operations": Scenario(
        id="current_operations",
        name="Current Operations",
        type=DisruptionType.CONGESTION_SURGE,
        target="Purple, Green, Yellow",
        severity=Severity.LOW,
        duration_min=0,
        description="Baseline 3-line operational network (Purple, Green, Yellow). Pink and Blue lines remain inactive/under construction.",
        active_lines=["Purple", "Green", "Yellow"],
        headway_sec=360,
        demand_multiplier=1.0,
        disruptions=[],
    ),
    "expanded_5_line": Scenario(
        id="expanded_5_line",
        name="Expanded 5-Line Network",
        type=DisruptionType.CONGESTION_SURGE,
        target="All 5 Lines (Purple, Green, Yellow, Pink, Blue)",
        severity=Severity.MEDIUM,
        duration_min=120,
        description="Simulated activation of Pink and Blue metro lines alongside Purple, Green, and Yellow.",
        active_lines=["Purple", "Green", "Yellow", "Pink", "Blue"],
        headway_sec=360,
        demand_multiplier=1.0,
        disruptions=[],
    ),
    "peak_expanded": Scenario(
        id="peak_expanded",
        name="Peak + Expanded 5-Line",
        type=DisruptionType.DEMAND_SURGE,
        target="All 5 Lines",
        severity=Severity.HIGH,
        duration_min=120,
        description="Peak hour operations on full 5-line network with 3-minute train headways (180s) and 1.5x passenger demand surge.",
        active_lines=["Purple", "Green", "Yellow", "Pink", "Blue"],
        headway_sec=180,
        demand_multiplier=1.5,
        disruptions=[],
    ),
    "full_multi_disruption": Scenario(
        id="full_multi_disruption",
        name="Full Multi-Disruption",
        type=DisruptionType.STATION_CLOSURE,
        target="Majestic, Silk Board, Nagawara",
        severity=Severity.CRITICAL,
        duration_min=60,
        description="Multi-disruption scenario on Expanded 5-Line network combining Majestic station closure, Central Silk Board passenger surge, and Nagawara signal delay.",
        active_lines=["Purple", "Green", "Yellow", "Pink", "Blue"],
        headway_sec=360,
        demand_multiplier=1.3,
        disruptions=[
            Disruption(
                id="d_majestic_closure",
                name="Majestic Hub Closure",
                type=DisruptionType.STATION_CLOSURE,
                severity=Severity.CRITICAL,
                description="Majestic platform and interchange closure.",
                affected_stations=["Nadaprabhu Kempegowda Station (Majestic)", "PL22", "GL17"],
                affected_lines=["Purple", "Green"],
                delay_multiplier=3.5,
                congestion_multiplier=2.5,
            ),
            Disruption(
                id="d_silk_board_surge",
                name="Silk Board Crowd Influx",
                type=DisruptionType.DEMAND_SURGE,
                severity=Severity.HIGH,
                description="Demand and congestion surge at Silk Board hub.",
                affected_stations=["Central Silk Board", "YL05", "BL23"],
                demand_multiplier=1.75,
                congestion_multiplier=1.6,
                delay_multiplier=1.4,
            ),
            Disruption(
                id="d_nagawara_delay",
                name="Nagawara Signal Delay",
                type=DisruptionType.SEVERE_DELAY,
                severity=Severity.MEDIUM,
                description="Signal delay on Nagawara line segments.",
                affected_stations=["Nagawara", "PK18", "BL06"],
                delay_multiplier=1.5,
                congestion_multiplier=1.3,
            ),
        ],
    ),
    "majestic_closure": Scenario(
        id="majestic_closure",
        name="Majestic Station Closure",
        type=DisruptionType.STATION_CLOSURE,
        target="Nadaprabhu Kempegowda Station (Majestic)",
        severity=Severity.CRITICAL,
        duration_min=60,
        description="Full closure of Majestic central hub due to structural maintenance. All incident line segments and transfers unavailable.",
        active_lines=["Purple", "Green", "Yellow"],
        headway_sec=360,
        demand_multiplier=1.0,
        disruptions=[
            Disruption(
                id="d_majestic_closure",
                name="Majestic Hub Closure",
                type=DisruptionType.STATION_CLOSURE,
                severity=Severity.CRITICAL,
                description="Majestic platform and interchange closure.",
                affected_stations=["Nadaprabhu Kempegowda Station (Majestic)", "PL22", "GL17"],
                affected_lines=["Purple", "Green"],
                delay_multiplier=3.5,
                congestion_multiplier=2.5,
            )
        ],
    ),
    "rv_road_closure": Scenario(
        id="rv_road_closure",
        name="RV Road Interchange Closure",
        type=DisruptionType.INTERCHANGE_CLOSURE,
        target="Rashtreeya Vidyalaya Road (RV Road)",
        severity=Severity.HIGH,
        duration_min=45,
        description="Platform transfer closure at RV Road between Green and Yellow lines. Through-train track segments remain operational.",
        active_lines=["Purple", "Green", "Yellow"],
        headway_sec=360,
        demand_multiplier=1.0,
        disruptions=[
            Disruption(
                id="d_rv_road_xfer",
                name="RV Road Transfer Edge Closure",
                type=DisruptionType.INTERCHANGE_CLOSURE,
                severity=Severity.HIGH,
                description="Transfer platform between Green and Yellow line disabled at RV Road.",
                affected_stations=["Rashtreeya Vidyalaya Road (RV Road)", "GL24", "YL01"],
                affected_edges=["XFER_GL24_YL01", "XFER_YL01_GL24"],
                delay_multiplier=2.0,
                congestion_multiplier=1.75,
            )
        ],
    ),
    "purple_closure": Scenario(
        id="purple_closure",
        name="Purple Line Closure",
        type=DisruptionType.LINE_CLOSURE,
        target="Purple",
        severity=Severity.CRITICAL,
        duration_min=90,
        description="Complete operational suspension along the entire Purple Line corridor.",
        active_lines=["Green", "Yellow"],
        headway_sec=360,
        demand_multiplier=1.0,
        disruptions=[
            Disruption(
                id="d_purple_line",
                name="Purple Line Full Suspension",
                type=DisruptionType.LINE_CLOSURE,
                severity=Severity.CRITICAL,
                description="All track segments on Purple Line disabled.",
                affected_lines=["Purple"],
                delay_multiplier=3.5,
                congestion_multiplier=2.5,
            )
        ],
    ),
    "blue_closure": Scenario(
        id="blue_closure",
        name="Blue Line Closure",
        type=DisruptionType.LINE_CLOSURE,
        target="Blue",
        severity=Severity.CRITICAL,
        duration_min=120,
        description="Blue Line under-construction corridor disabled for scenario testing.",
        active_lines=["Purple", "Green", "Yellow", "Pink"],
        headway_sec=360,
        demand_multiplier=1.0,
        disruptions=[
            Disruption(
                id="d_blue_line",
                name="Blue Line Corridor Disruption",
                type=DisruptionType.LINE_CLOSURE,
                severity=Severity.CRITICAL,
                description="Blue Line track segments unavailable.",
                affected_lines=["Blue"],
                delay_multiplier=3.5,
                congestion_multiplier=2.5,
            )
        ],
    ),
    "majestic_congestion": Scenario(
        id="majestic_congestion",
        name="Severe Congestion at Majestic",
        type=DisruptionType.CONGESTION_SURGE,
        target="Nadaprabhu Kempegowda Station (Majestic)",
        severity=Severity.HIGH,
        duration_min=30,
        description="Extreme passenger overcrowding at Majestic causing 1.75x congestion surge on incident segments.",
        active_lines=["Purple", "Green", "Yellow"],
        headway_sec=360,
        demand_multiplier=1.5,
        disruptions=[
            Disruption(
                id="d_majestic_cong",
                name="Majestic Overcrowding Surge",
                type=DisruptionType.CONGESTION_SURGE,
                severity=Severity.HIGH,
                description="Congestion surge on Majestic incident edges.",
                affected_stations=["Nadaprabhu Kempegowda Station (Majestic)", "PL22", "GL17"],
                congestion_multiplier=1.75,
                delay_multiplier=1.5,
            )
        ],
    ),
    "silk_board_surge": Scenario(
        id="silk_board_surge",
        name="Passenger Surge at Central Silk Board",
        type=DisruptionType.DEMAND_SURGE,
        target="Central Silk Board",
        severity=Severity.HIGH,
        duration_min=45,
        description="Mass transit peak crowd influx at Central Silk Board causing 1.75x passenger demand surge.",
        active_lines=["Purple", "Green", "Yellow"],
        headway_sec=360,
        demand_multiplier=1.75,
        disruptions=[
            Disruption(
                id="d_silk_board_surge",
                name="Silk Board Crowd Influx",
                type=DisruptionType.DEMAND_SURGE,
                severity=Severity.HIGH,
                description="Demand and congestion surge at Silk Board hub.",
                affected_stations=["Central Silk Board", "YL05", "BL23"],
                demand_multiplier=1.75,
                congestion_multiplier=1.6,
                delay_multiplier=1.4,
            )
        ],
    ),
    "kr_pura_track_closure": Scenario(
        id="kr_pura_track_closure",
        name="Track Closure near KR Pura",
        type=DisruptionType.EDGE_CLOSURE,
        target="Singayyanapalya to KR Pura Track Segment",
        severity=Severity.CRITICAL,
        duration_min=60,
        description="Track defect between Singayyanapalya (PL11) and KR Pura (PL12) disabling segment traversal.",
        active_lines=["Purple", "Green", "Yellow"],
        headway_sec=360,
        demand_multiplier=1.0,
        disruptions=[
            Disruption(
                id="d_kr_pura_edge",
                name="PL11_PL12 Track Segment Blockage",
                type=DisruptionType.EDGE_CLOSURE,
                severity=Severity.CRITICAL,
                description="Track segment between PL11 and PL12 closed.",
                affected_edges=["PL_E11", "PL_E11_R"],
                affected_stations=["Singayyanapalya", "Krishnarajapura (KR Pura)"],
                affected_lines=["Purple"],
                delay_multiplier=3.5,
            )
        ],
    ),
    "nagawara_delay": Scenario(
        id="nagawara_delay",
        name="Major Delay near Nagawara",
        type=DisruptionType.SEVERE_DELAY,
        target="Nagawara Station Area",
        severity=Severity.MEDIUM,
        duration_min=40,
        description="Signal failure near Nagawara causing 1.5x travel time delay on incident segments.",
        active_lines=["Purple", "Green", "Yellow"],
        headway_sec=360,
        demand_multiplier=1.0,
        disruptions=[
            Disruption(
                id="d_nagawara_delay",
                name="Nagawara Signal Delay",
                type=DisruptionType.SEVERE_DELAY,
                severity=Severity.MEDIUM,
                description="Signal delay on Nagawara line segments.",
                affected_stations=["Nagawara", "PK18", "BL06"],
                delay_multiplier=1.5,
                congestion_multiplier=1.3,
            )
        ],
    ),
}


def get_scenario(scenario_id: str) -> Optional[Scenario]:
    """Retrieve scenario definition from the Scenario Library."""
    return SCENARIO_LIBRARY.get(scenario_id)


def list_scenarios() -> List[Scenario]:
    """Return all available scenarios in the library."""
    return list(SCENARIO_LIBRARY.values())


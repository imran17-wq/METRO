"""
src/config/simulation_settings.py

Configuration parameters and severity calibration for Phase 5 Disruption
Simulation & Network Resilience Analysis.
"""
from __future__ import annotations

from typing import Dict, Any

# ---------------------------------------------------------------------------
# Representative OD Sampling Config
# ---------------------------------------------------------------------------
#: Default OD sample size for automated tests and fast API checks.
DEFAULT_OD_SAMPLE_SIZE: int = 50

#: Maximum allowed OD sample size for full resilience analysis.
MAX_OD_SAMPLE_SIZE: int = 500

#: Fixed seed for deterministic, reproducible OD sampling across runs.
RANDOM_SEED: int = 42

# ---------------------------------------------------------------------------
# Composite Resilience Score Weights (sum = 1.0)
# ---------------------------------------------------------------------------
RESILIENCE_SCORE_WEIGHTS: Dict[str, float] = {
    "route_availability": 0.40,      # Weight for % OD pairs reachable
    "travel_time_impact": 0.30,      # Weight for travel time degradation factor
    "unreachable_rate": 0.20,        # Penalty weight for disconnected pairs
    "rerouting_success": 0.10,       # Weight for % disrupted journeys rerouted
}

# ---------------------------------------------------------------------------
# Severity Multipliers
# ---------------------------------------------------------------------------
SEVERITY_MULTIPLIERS: Dict[str, Dict[str, Any]] = {
    "LOW": {
        "delay_multiplier": 1.25,
        "congestion_multiplier": 1.20,
        "is_closure": False,
        "description": "Minor operational delay or minor localized surge.",
    },
    "MEDIUM": {
        "delay_multiplier": 1.50,
        "congestion_multiplier": 1.40,
        "is_closure": False,
        "description": "Moderate delay / platform crowding.",
    },
    "HIGH": {
        "delay_multiplier": 2.00,
        "congestion_multiplier": 1.75,
        "is_closure": False,
        "description": "Major disruption with heavy delays and severe congestion.",
    },
    "CRITICAL": {
        "delay_multiplier": 3.50,
        "congestion_multiplier": 2.50,
        "is_closure": True,
        "description": "Critical infrastructure failure or full line/station closure.",
    },
}

# ---------------------------------------------------------------------------
# Cascading Congestion Demand Redistribution Parameters
# ---------------------------------------------------------------------------
#: Additional congestion percentage added per rerouted passenger unit.
REROUTE_CONGESTION_INCREMENT_PER_PAIR: float = 0.5

#: Maximum allowed congestion percentage cap.
MAX_CONGESTION_PCT_CAP: float = 95.0

# ---------------------------------------------------------------------------
# Provenance Constants
# ---------------------------------------------------------------------------
SIMULATION_PROVENANCE: Dict[str, str] = {
    "topology": "STATIC_TOPOLOGY_REAL_SOURCE_NETWORK",
    "demand": "SYNTHETIC",
    "prediction": "SYNTHETIC_MODEL_OUTPUT",
    "scenario": "SIMULATED_SCENARIO",
    "impact": "DERIVED_SIMULATION_OUTPUT",
    "route": "DERIVED",
}

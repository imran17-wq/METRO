"""
delay_generator.py — Stochastic synthetic delay event generator.

DATA PROVENANCE: SYNTHETIC
--------------------------
Delays are sampled from a Bernoulli process with probability varying by:
- Station type (interchange stations: higher probability)
- Time of day (peak slots: higher probability)
- Congestion level (HIGH/CRITICAL edges: higher probability)

No real BMRCL delay records are used.  These are synthetic events intended
to give the ML models (Phase 3) realistic non-trivial target values.

The generation parameters are fully configurable via the DemandConfig
dataclass in pipeline.py.  Every assumption is documented here and in
data_generation/README.md.

Delay cause categories (synthetic, illustrative only)
------------------------------------------------------
- CROWDING       : platform overflow / dwell extension
- SIGNAL_HOLD    : simulated ATC/signalling delay
- PLATFORM_BLOCK : preceding train slow clearance
- MAINTENANCE    : scheduled maintenance affecting schedule
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from src.demand.congestion import congestion_band

# ---------------------------------------------------------------------------
# Probability parameters (tunable)
# ---------------------------------------------------------------------------

# Base probability of a delay event on any edge in any slot.
BASE_DELAY_PROB: float = 0.02

# Multiplier applied to interchange edges.
INTERCHANGE_MULTIPLIER: float = 2.5

# Multipliers by congestion band.
CONGESTION_BAND_MULTIPLIER: Dict[str, float] = {
    "LOW": 1.0,
    "MEDIUM": 1.8,
    "HIGH": 3.0,
    "CRITICAL": 5.0,
}

# Peak-slot multiplier.
PEAK_MULTIPLIER: float = 1.6

# Delay magnitude distribution (minutes):
# Log-normal with μ=ln(4), σ=0.6 → median ≈ 4 min, mean ≈ 5 min.
DELAY_LOG_MU: float = 1.4
DELAY_LOG_SIGMA: float = 0.6

DELAY_CAUSES = ["CROWDING", "SIGNAL_HOLD", "PLATFORM_BLOCK", "MAINTENANCE"]
DELAY_CAUSE_PROBS = [0.50, 0.25, 0.15, 0.10]

# Minimum reportable delay (minutes).
MIN_DELAY_MIN: float = 1.0


def generate_delay_events(
    edge_congestion_records: List[Dict],
    slot: int,
    day_type: str,
    interchange_edges: set,
    rng: np.random.Generator,
) -> List[Dict]:
    """
    Generate stochastic delay events for a given time slot.

    Parameters
    ----------
    edge_congestion_records : list of dict
        Output of congestion.compute_congestion_records() for this slot.
    slot : int
        Time slot index.
    day_type : str
    interchange_edges : set
        Set of canonical edge tuples that are TRANSFER edges.
    rng : np.random.Generator
        Seeded random number generator for reproducibility.

    Returns
    -------
    list of delay event dicts.
    """
    from src.demand.temporal import is_peak_slot  # avoid circular import

    events: List[Dict] = []
    is_peak = is_peak_slot(slot, day_type)

    for rec in edge_congestion_records:
        edge_key = rec["edge_key"]
        band = rec["congestion_band"]
        is_interchange = edge_key in interchange_edges

        prob = BASE_DELAY_PROB
        prob *= CONGESTION_BAND_MULTIPLIER.get(band, 1.0)
        if is_interchange:
            prob *= INTERCHANGE_MULTIPLIER
        if is_peak:
            prob *= PEAK_MULTIPLIER
        prob = min(prob, 0.95)  # cap at 95%

        if rng.random() < prob:
            delay_min = rng.lognormal(DELAY_LOG_MU, DELAY_LOG_SIGMA)
            delay_min = max(MIN_DELAY_MIN, round(float(delay_min), 1))
            cause = rng.choice(DELAY_CAUSES, p=DELAY_CAUSE_PROBS)

            events.append({
                "edge_key": edge_key,
                "edge_id": rec["edge_id"],
                "from_id": rec["from_id"],
                "to_id": rec["to_id"],
                "line": rec["line"],
                "delay_min": delay_min,
                "cause": cause,
                "congestion_band": band,
                "is_interchange_edge": is_interchange,
            })

    return events

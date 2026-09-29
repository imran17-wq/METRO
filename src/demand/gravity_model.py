"""
gravity_model.py — Origin-Destination demand generator for Namma Pulse Phase 2.

DATA PROVENANCE: SYNTHETIC (generative, not fabricated-as-real)
---------------------------------------------------------------
Implements a gravity-style OD model:

    demand(O, D) ∝ w_origin(O) × w_destination(D) / (1 + α × d(O,D)^β)

where:
- w_origin, w_destination = station weights from station_characteristics.py
- d(O, D) = shortest-path hop distance (graph hop count)
- α = distance decay scale (configurable, default 0.3)
- β = distance decay exponent (configurable, default 1.5)

The resulting demand matrix is SYNTHETIC.  It is not derived from BMRCL
ridership surveys or ticketing data.  The gravity model is a standard
transport planning technique applied here with documented, tunable parameters.

Calibration sanity check
------------------------
The output is calibrated so that total daily system ridership is
approximately 600,000–800,000 trips — consistent with the general range
reported in Bengaluru Metro press coverage (2024–2025).  This provides a
rough-order-of-magnitude anchor, not a precise figure.

Full methodology: see data_generation/README.md.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import networkx as nx

from src.demand.station_characteristics import (
    STATION_TYPES,
    STATION_TYPE_WEIGHTS,
    BASE_ACTIVITY_WEIGHTS,
    EVENT_SURGE_STATIONS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model parameters (tunable)
# ---------------------------------------------------------------------------

# Distance decay: demand falls off with path distance.
# α = 0.3, β = 1.5 → moderate decay.  Increase β for stronger distance penalty.
DECAY_ALPHA: float = 0.3
DECAY_BETA: float = 1.5

# Global demand scale factor.
# Tuned so that daily total trips ≈ 600k–800k (rough calibration anchor).
DAILY_DEMAND_SCALE: float = 18.0


# ---------------------------------------------------------------------------
# OD distance matrix
# ---------------------------------------------------------------------------

def compute_hop_distances(
    G: nx.Graph,
    station_ids: List[str],
) -> Dict[Tuple[str, str], int]:
    """
    Compute shortest-path hop count for all station pairs.

    Uses NetworkX all_pairs_shortest_path_length (unweighted).
    Result is cached in a flat dict for fast lookup.

    Returns
    -------
    dict mapping (origin_id, destination_id) → hop_count
    """
    logger.info("Computing all-pairs hop distances for %d nodes...", len(station_ids))
    lengths = dict(nx.all_pairs_shortest_path_length(G))
    distances: Dict[Tuple[str, str], int] = {}
    node_set = set(station_ids)
    for u, dmap in lengths.items():
        if u not in node_set:
            continue
        for v, d in dmap.items():
            if v in node_set and u != v:
                distances[(u, v)] = d
    logger.info("Computed %d OD distance pairs.", len(distances))
    return distances


# ---------------------------------------------------------------------------
# Gravity demand matrix
# ---------------------------------------------------------------------------

def compute_gravity_base_demand(
    station_ids: List[str],
    hop_distances: Dict[Tuple[str, str], int],
    decay_alpha: float = DECAY_ALPHA,
    decay_beta: float = DECAY_BETA,
    scale: float = DAILY_DEMAND_SCALE,
) -> Dict[Tuple[str, str], float]:
    """
    Compute the base daily OD demand matrix using the gravity model.

    Parameters
    ----------
    station_ids : list of str
        All station node IDs to include.
    hop_distances : dict
        (origin_id, destination_id) → hop_count from compute_hop_distances().
    decay_alpha, decay_beta : float
        Distance decay parameters.
    scale : float
        Global scale factor.

    Returns
    -------
    dict mapping (origin_id, destination_id) → base daily demand (float)

    DATA_TYPE: SYNTHETIC
    """
    def activity_weight(sid: str) -> float:
        stype = STATION_TYPES.get(sid, "mixed")
        return BASE_ACTIVITY_WEIGHTS.get(stype, 1.0)

    od_demand: Dict[Tuple[str, str], float] = {}
    n = len(station_ids)

    for origin in station_ids:
        w_o = activity_weight(origin)
        for dest in station_ids:
            if origin == dest:
                continue
            hops = hop_distances.get((origin, dest))
            if hops is None or hops == 0:
                continue
            w_d = activity_weight(dest)
            # Gravity formula: demand ∝ w_o × w_d / (1 + α × d^β)
            gravity = (w_o * w_d) / (1.0 + decay_alpha * (hops ** decay_beta))
            od_demand[(origin, dest)] = gravity * scale

    logger.info(
        "Gravity base demand computed: %d OD pairs, total daily = %.0f trips",
        len(od_demand),
        sum(od_demand.values()),
    )
    return od_demand


# ---------------------------------------------------------------------------
# Time-of-day scaling
# ---------------------------------------------------------------------------

def scale_demand_by_time(
    base_od_demand: Dict[Tuple[str, str], float],
    time_factor: float,
    origin_weight_factor: float,
    dest_weight_factor: float,
    station_ids: List[str],
    noise_rng: Optional[np.random.Generator],
    noise_std: float = 0.10,
) -> Dict[Tuple[str, str], float]:
    """
    Apply temporal scaling and station-type directional weights to base demand.

    Parameters
    ----------
    base_od_demand : dict
    time_factor : float
        Overall multiplier for this time slot (from temporal curve).
    origin_weight_factor : float
        Directional multiplier for origin side (AM or PM).
    dest_weight_factor : float
        Directional multiplier for destination side (AM or PM).
    station_ids : list
    noise_rng : np.random.Generator or None
        If provided, add stochastic noise ±noise_std.
    noise_std : float
        Standard deviation of relative noise.

    Returns
    -------
    dict mapping (origin_id, destination_id) → slot demand (float, ≥ 0)
    """
    def origin_directional(sid: str, is_am: bool) -> float:
        stype = STATION_TYPES.get(sid, "mixed")
        w = STATION_TYPE_WEIGHTS.get(stype, (1.0, 1.0, 1.0, 1.0))
        return w[0] if is_am else w[2]  # orig_AM or orig_PM

    def dest_directional(sid: str, is_am: bool) -> float:
        stype = STATION_TYPES.get(sid, "mixed")
        w = STATION_TYPE_WEIGHTS.get(stype, (1.0, 1.0, 1.0, 1.0))
        return w[1] if is_am else w[3]  # dest_AM or dest_PM

    is_am = origin_weight_factor > dest_weight_factor  # AM: origins stronger

    slot_demand: Dict[Tuple[str, str], float] = {}
    for (o, d), base in base_od_demand.items():
        wo = origin_directional(o, is_am)
        wd = dest_directional(d, is_am)
        demand = base * time_factor * wo * wd * origin_weight_factor * dest_weight_factor
        if noise_rng is not None:
            noise = noise_rng.normal(1.0, noise_std)
            demand *= max(0.0, noise)
        slot_demand[(o, d)] = max(0.0, demand)

    return slot_demand


# ---------------------------------------------------------------------------
# Event-day surge
# ---------------------------------------------------------------------------

def apply_event_surge(
    slot_demand: Dict[Tuple[str, str], float],
    event_stations: Dict[str, float] = EVENT_SURGE_STATIONS,
) -> Dict[Tuple[str, str], float]:
    """
    Multiply demand for OD pairs involving event-adjacent stations.

    Applied ONLY when the day_type == "event".
    """
    surged: Dict[Tuple[str, str], float] = {}
    for (o, d), demand in slot_demand.items():
        surge_o = event_stations.get(o, 1.0)
        surge_d = event_stations.get(d, 1.0)
        surged[(o, d)] = demand * max(surge_o, surge_d)
    return surged

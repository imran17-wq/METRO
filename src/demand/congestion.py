"""
congestion.py — Converts edge passenger flow to congestion metrics.

DATA PROVENANCE: SYNTHETIC (DERIVED from synthetic flow + approximate capacity)
-------------------------------------------------------------------------------
Congestion is computed as:

    congestion_pct = (flow_passengers / capacity_per_slot) × 100

where capacity_per_slot is APPROXIMATE:
    capacity_per_slot = TRAIN_CAPACITY × trains_per_slot(frequency)

Train capacity and frequency are based on publicly available BMRCL
specifications.  They are REAL engineering parameters, but the flow values
are SYNTHETIC.  Therefore congestion is DERIVED (real formula, synthetic input).

Capacity assumptions
--------------------
- 6-coach train: ~990–1000 standees + seated.  We use 1000 as a round figure.
  SOURCE: BMRCL Bombardier Movia fleet specifications (public).  REAL.
- Peak frequency: 1 train per 5 minutes → 3 trains per 15-min slot.
  SOURCE: Approximate, from BMRCL schedule information.  DOCUMENTED ASSUMPTION.
- Off-peak frequency: 1 train per 10 minutes → 1.5 trains per 15-min slot.
  SOURCE: DOCUMENTED ASSUMPTION.

Congestion bands
----------------
LOW      : 0–50%
MEDIUM   : 50–80%
HIGH     : 80–100%
CRITICAL : >100%  (overflow — physically represents unaccommodated demand)
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from src.demand.temporal import SLOTS_PER_DAY, slot_to_hour, is_peak_slot

# ---------------------------------------------------------------------------
# Capacity parameters (tunable)
# ---------------------------------------------------------------------------

#: Approximate passenger capacity per 6-coach train.
#: SOURCE: BMRCL Bombardier Movia fleet.  REAL engineering spec.
TRAIN_CAPACITY: int = 1000

#: Trains per 15-minute slot during peak hours.
#: At 5-min headway: 3 trains per 15 min.  DOCUMENTED ASSUMPTION.
PEAK_TRAINS_PER_SLOT: float = 3.0

#: Trains per 15-minute slot during off-peak.
#: At 10-min headway: 1.5 trains per 15 min.  DOCUMENTED ASSUMPTION.
OFFPEAK_TRAINS_PER_SLOT: float = 1.5

#: Capacity per slot (passengers).
PEAK_CAPACITY_PER_SLOT: int = int(TRAIN_CAPACITY * PEAK_TRAINS_PER_SLOT)
OFFPEAK_CAPACITY_PER_SLOT: int = int(TRAIN_CAPACITY * OFFPEAK_TRAINS_PER_SLOT)

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------

CONGESTION_BANDS = [
    (0.0, 50.0,  "LOW"),
    (50.0, 80.0, "MEDIUM"),
    (80.0, 100.0, "HIGH"),
    (100.0, float("inf"), "CRITICAL"),
]


def congestion_band(pct: float) -> str:
    for lo, hi, label in CONGESTION_BANDS:
        if lo <= pct < hi:
            return label
    return "CRITICAL"


def slot_capacity(slot: int, day_type: str = "weekday") -> int:
    """Return the passenger capacity for a 15-min slot."""
    if day_type in ("weekday", "event") and is_peak_slot(slot, day_type):
        return PEAK_CAPACITY_PER_SLOT
    return OFFPEAK_CAPACITY_PER_SLOT


# ---------------------------------------------------------------------------
# Edge flow computation
# ---------------------------------------------------------------------------

def compute_edge_flows(
    od_demand: Dict[Tuple[str, str], float],
    all_paths: Dict[Tuple[str, str], List[str]],
) -> Dict[Tuple[str, str], float]:
    """
    Distribute OD demand onto edges by routing each pair along its shortest path.

    Parameters
    ----------
    od_demand : dict
        (origin_id, destination_id) → slot demand (passengers).
    all_paths : dict
        (origin_id, destination_id) → list of node IDs (shortest path).

    Returns
    -------
    dict mapping canonical edge tuple (min(u,v), max(u,v)) → flow (passengers).
    """
    edge_flow: Dict[Tuple[str, str], float] = {}

    for (o, d), demand in od_demand.items():
        if demand <= 0:
            continue
        path = all_paths.get((o, d))
        if not path or len(path) < 2:
            continue
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            key = (u, v) if u < v else (v, u)
            edge_flow[key] = edge_flow.get(key, 0.0) + demand

    return edge_flow


def compute_congestion_records(
    edge_flow: Dict[Tuple[str, str], float],
    slot: int,
    day_type: str,
    edge_id_map: Dict[Tuple[str, str], str],
    edge_line_map: Dict[Tuple[str, str], str],
) -> List[Dict]:
    """
    Compute congestion for each edge from flow data.

    Parameters
    ----------
    edge_flow : dict
        Canonical edge → flow passengers.
    slot : int
        Time slot index.
    day_type : str
    edge_id_map : dict
        canonical edge → edge_id string.
    edge_line_map : dict
        canonical edge → line name.

    Returns
    -------
    list of dicts — one record per edge.
    """
    capacity = slot_capacity(slot, day_type)
    records = []
    for edge_key, flow in edge_flow.items():
        pct = (flow / capacity) * 100.0 if capacity > 0 else 0.0
        band = congestion_band(pct)
        edge_id = edge_id_map.get(edge_key, f"E_{edge_key[0]}_{edge_key[1]}")
        line = edge_line_map.get(edge_key, "Unknown")
        records.append({
            "edge_key": edge_key,
            "edge_id": edge_id,
            "from_id": edge_key[0],
            "to_id": edge_key[1],
            "line": line,
            "flow_passengers": round(flow, 1),
            "capacity": capacity,
            "congestion_pct": round(pct, 2),
            "congestion_band": band,
        })
    return records


def compute_station_congestion(
    edge_congestion: List[Dict],
    station_ids: List[str],
    station_line_map: Dict[str, str],
) -> List[Dict]:
    """
    Aggregate edge congestion to station level (max of adjacent edges).

    Returns one record per station.
    """
    station_max: Dict[str, float] = {sid: 0.0 for sid in station_ids}

    for rec in edge_congestion:
        u, v = rec["from_id"], rec["to_id"]
        pct = rec["congestion_pct"]
        if u in station_max:
            station_max[u] = max(station_max[u], pct)
        if v in station_max:
            station_max[v] = max(station_max[v], pct)

    records = []
    for sid, pct in station_max.items():
        records.append({
            "station_id": sid,
            "line": station_line_map.get(sid, "Unknown"),
            "congestion_pct": round(pct, 2),
            "congestion_band": congestion_band(pct),
        })
    return records

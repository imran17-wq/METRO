"""
Shared path-parsing utilities for routing algorithms.
Includes state-aware edge weight evaluation based on active line metadata.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

import networkx as nx

from src.routing.route import RouteResult, RouteSegment
from src.graph.station_model import Station
from src.graph.metro_graph import get_active_lines

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weight constants
# ---------------------------------------------------------------------------

DEFAULT_SEGMENT_TIME_MIN: float = 2.5
DEFAULT_TRANSFER_TIME_MIN: float = 3.0

APPROX_NOTE = (
    "Travel times are APPROXIMATE: source topology (BMRCL PDF, 2025) does not "
    "include per-segment scheduled times. A fallback of 2.5 min/segment and "
    "3.0 min/interchange-transfer has been applied (DERIVED, not MEASURED)."
)


def make_segment_weight_func(
    stations: Dict[str, Station],
    active_lines: Optional[Set[str]] = None,
):
    """
    Factory creating a weight evaluation function for NetworkX path algorithms.

    Enforces active line constraints:
    1. Regular line edges require edge.line to be in active_lines.
    2. TRANSFER edges require BOTH participating endpoint station lines to be in active_lines.
    """
    actives = set(active_lines if active_lines is not None else get_active_lines())

    def segment_weight(u: str, v: str, data: dict) -> float:
        line = data.get("line", "")

        if line == "TRANSFER":
            line_u = stations[u].line if u in stations else None
            line_v = stations[v].line if v in stations else None
            if line_u not in actives or line_v not in actives:
                return float("inf")
            return DEFAULT_TRANSFER_TIME_MIN

        if line not in actives:
            return float("inf")

        t = data.get("scheduled_time_min")
        if t is None:
            return DEFAULT_SEGMENT_TIME_MIN
        return float(t)

    return segment_weight


def segment_weight(u: str, v: str, data: dict) -> float:
    """Fallback segment_weight function for backwards compatibility."""
    line = data.get("line", "")
    if line == "TRANSFER":
        return DEFAULT_TRANSFER_TIME_MIN

    t = data.get("scheduled_time_min")
    if t is None:
        return DEFAULT_SEGMENT_TIME_MIN
    return float(t)


# ---------------------------------------------------------------------------
# Path → RouteResult
# ---------------------------------------------------------------------------

def build_route_result(
    G: nx.Graph,
    raw_path: List[str],
    total_weight: float,
    algorithm: str,
    stations: Dict[str, Station],
) -> RouteResult:
    clean_ids: List[str] = []
    clean_names: List[str] = []
    segment_lines: List[str] = []
    interchange_names: List[str] = []
    transfer_times: float = 0.0

    current_line: Optional[str] = None

    for i, nid in enumerate(raw_path):
        s = stations[nid]

        if i == 0:
            clean_ids.append(nid)
            clean_names.append(s.station_name)
            current_line = s.line
            segment_lines.append(s.line)
            continue

        prev_nid = raw_path[i - 1]
        edge_data = G[prev_nid][nid]
        edge_line = edge_data.get("line", "")

        if edge_line == "TRANSFER":
            interchange_names.append(s.station_name)
            transfer_times += DEFAULT_TRANSFER_TIME_MIN
            current_line = s.line
        else:
            clean_ids.append(nid)
            clean_names.append(s.station_name)
            segment_lines.append(current_line or s.line)

    segments: List[RouteSegment] = []
    if clean_ids:
        seg_ids = [clean_ids[0]]
        seg_names = [clean_names[0]]
        seg_line = segment_lines[0]
        seg_time: float = 0.0

        for idx in range(1, len(clean_ids)):
            line_now = segment_lines[idx]

            if line_now != seg_line:
                segments.append(RouteSegment(
                    line=seg_line,
                    station_ids=seg_ids,
                    station_names=seg_names,
                    segment_time_min=round(seg_time, 2),
                ))
                seg_ids = [clean_ids[idx]]
                seg_names = [clean_names[idx]]
                seg_line = line_now
                seg_time = 0.0
            else:
                seg_ids.append(clean_ids[idx])
                seg_names.append(clean_names[idx])
                seg_time += DEFAULT_SEGMENT_TIME_MIN

        segments.append(RouteSegment(
            line=seg_line,
            station_ids=seg_ids,
            station_names=seg_names,
            segment_time_min=round(seg_time, 2),
        ))

    lines_used: List[str] = list(dict.fromkeys(seg.line for seg in segments))
    unique_interchanges: List[str] = list(dict.fromkeys(interchange_names))

    return RouteResult(
        origin=clean_names[0] if clean_names else "",
        destination=clean_names[-1] if clean_names else "",
        origin_id=clean_ids[0] if clean_ids else "",
        destination_id=clean_ids[-1] if clean_ids else "",
        station_ids=clean_ids,
        station_names=clean_names,
        segments=segments,
        total_time_min=round(total_weight, 2),
        total_distance_km=None,
        interchange_count=len(unique_interchanges),
        interchange_stations=unique_interchanges,
        hop_count=len(clean_ids) - 1,
        lines=lines_used,
        algorithm=algorithm,
        notes=[APPROX_NOTE],
    )

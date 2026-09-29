"""
Dijkstra shortest-path router for Namma Pulse.
Enforces line active state eligibility on single canonical graph.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, Set

import networkx as nx

from src.graph.station_model import Station
from src.routing.route import RouteResult
from src.routing.path_parser import make_segment_weight_func, build_route_result
from src.graph.metro_graph import get_active_lines

logger = logging.getLogger(__name__)


def find_dijkstra_route(
    graph: nx.Graph,
    origin_id: str,
    destination_id: str,
    stations: Dict[str, Station],
    active_lines: Optional[Set[str]] = None,
) -> Optional[RouteResult]:
    """Find the shortest-time path from origin to destination using Dijkstra."""
    if origin_id == destination_id:
        logger.warning("Dijkstra: origin == destination (%s)", origin_id)
        return None

    if origin_id not in graph or destination_id not in graph:
        logger.warning(
            "Dijkstra: node not found in graph: origin=%s dest=%s",
            origin_id, destination_id,
        )
        return None

    actives = active_lines if active_lines is not None else get_active_lines()

    # Check origin and destination line active state
    if stations[origin_id].line not in actives:
        logger.info("Dijkstra: origin line %s is inactive", stations[origin_id].line)
        return None
    if stations[destination_id].line not in actives:
        logger.info("Dijkstra: destination line %s is inactive", stations[destination_id].line)
        return None

    weight_fn = make_segment_weight_func(stations, actives)

    try:
        path = nx.dijkstra_path(
            graph, origin_id, destination_id, weight=weight_fn
        )
        total_weight = nx.dijkstra_path_length(
            graph, origin_id, destination_id, weight=weight_fn
        )
        if total_weight == float("inf"):
            return None
    except nx.NetworkXNoPath:
        logger.info("Dijkstra: no path between %s and %s", origin_id, destination_id)
        return None
    except nx.NodeNotFound as exc:
        logger.warning("Dijkstra: node not found — %s", exc)
        return None

    return build_route_result(graph, path, total_weight, "dijkstra", stations)

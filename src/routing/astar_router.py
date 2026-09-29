"""
A* router for Namma Pulse.
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


def _heuristic(node: str, goal: str) -> float:
    return 0.0


def find_astar_route(
    graph: nx.Graph,
    origin_id: str,
    destination_id: str,
    stations: Dict[str, Station],
    active_lines: Optional[Set[str]] = None,
) -> Optional[RouteResult]:
    """Find shortest path using A* with line state filtering."""
    if origin_id == destination_id:
        logger.warning("A*: origin == destination (%s)", origin_id)
        return None

    if origin_id not in graph or destination_id not in graph:
        logger.warning(
            "A*: node not found in graph: origin=%s dest=%s",
            origin_id, destination_id,
        )
        return None

    actives = active_lines if active_lines is not None else get_active_lines()

    if stations[origin_id].line not in actives:
        return None
    if stations[destination_id].line not in actives:
        return None

    weight_fn = make_segment_weight_func(stations, actives)

    try:
        path = nx.astar_path(
            graph,
            origin_id,
            destination_id,
            heuristic=_heuristic,
            weight=weight_fn,
        )
        total_weight = sum(
            weight_fn(path[i], path[i + 1], graph[path[i]][path[i + 1]])
            for i in range(len(path) - 1)
        )
        if total_weight == float("inf"):
            return None
    except nx.NetworkXNoPath:
        logger.info("A*: no path between %s and %s", origin_id, destination_id)
        return None
    except nx.NodeNotFound as exc:
        logger.warning("A*: node not found — %s", exc)
        return None

    result = build_route_result(graph, path, total_weight, "astar", stations)
    result.notes.append(
        "A* used a zero heuristic (equivalent to Dijkstra): no verified geographic "
        "coordinates are available in Phase 0 topology data."
    )
    return result

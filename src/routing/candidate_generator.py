"""
src/routing/candidate_generator.py

Candidate route generator for Phase 4 Intelligent Dynamic Rerouting.

Uses Yen's K-shortest simple paths algorithm via NetworkX's
`shortest_simple_paths` generator to produce up to K=5 candidate routes between
an origin node and a destination node.

DESIGN RULES
------------
1. Candidate routes use graph topology with dynamic edge costs as weights.
2. Inactive edges (active=false in NetworkState) return cost=inf and are ignored.
3. Inactive line endpoints/stations are excluded upfront.
4. Candidates are returned as raw node-ID paths: List[List[str]].
5. Duplicates (in terms of physical station traversal) are pruned.
6. Does NOT duplicate or rebuild the NetworkX graph.
"""
from __future__ import annotations

import itertools
import logging
from typing import Dict, List, Optional, Set

import networkx as nx

from src.config.routing_weights import K_CANDIDATES, ROUTING_WEIGHTS
from src.graph.station_model import Station
from src.routing.edge_cost import DynamicCostCalculator

logger = logging.getLogger(__name__)


class CandidateRouteGenerator:
    """
    Generates K simple candidate paths for a given origin/destination pair.
    """

    def __init__(self, graph: nx.Graph, stations: Dict[str, Station]) -> None:
        self.G = graph
        self.stations = stations

    def generate_candidates(
        self,
        origin_id: str,
        destination_id: str,
        cost_calculator: DynamicCostCalculator,
        active_lines: Set[str],
        profile_weights: Optional[Dict[str, float]] = None,
        k: int = K_CANDIDATES,
    ) -> List[List[str]]:
        """
        Generate up to k candidate simple paths (node ID lists).

        Parameters
        ----------
        origin_id       : Node ID of origin (e.g. 'PL01')
        destination_id  : Node ID of destination (e.g. 'GL32')
        cost_calculator : DynamicCostCalculator instance
        active_lines    : Set of operational/active lines
        profile_weights : Optional profile weight dict override
        k               : Number of candidates requested (default 5)

        Returns
        -------
        List of paths, where each path is a List[str] of node IDs.
        """
        if origin_id not in self.G or destination_id not in self.G:
            logger.warning(
                "Candidate generator: node not found (%s, %s)", origin_id, destination_id
            )
            return []

        # Check line eligibility of origin & destination nodes
        origin_line = self.stations[origin_id].line
        dest_line = self.stations[destination_id].line

        if origin_line not in active_lines or dest_line not in active_lines:
            logger.info(
                "Candidate generator: line inactive for origin/dest (%s on %s, %s on %s)",
                origin_id,
                origin_line,
                destination_id,
                dest_line,
            )
            return []

        # Define dynamic weight function for NetworkX algorithms
        def weight_fn(u: str, v: str, data: dict) -> float:
            # Check line eligibility of non-transfer edge
            line = data.get("line", "")
            if line == "TRANSFER":
                lu = self.stations[u].line if u in self.stations else None
                lv = self.stations[v].line if v in self.stations else None
                if lu not in active_lines or lv not in active_lines:
                    return float("inf")
            elif line not in active_lines:
                return float("inf")

            w = cost_calculator.edge_weight(u, v, data, profile_weights=profile_weights)
            return w

        candidates: List[List[str]] = []
        seen_station_sequences: Set[tuple] = set()

        try:
            # NetworkX shortest_simple_paths implements Yen's algorithm
            path_generator = nx.shortest_simple_paths(
                self.G, origin_id, destination_id, weight=weight_fn
            )

            # Pull paths until we get k distinct station sequences or generator exhausts
            # Inspect up to k * 4 paths to account for platform-transfer node variations
            for path in itertools.islice(path_generator, k * 4):
                # Calculate total cost to make sure path is traversable
                path_cost = sum(
                    weight_fn(path[i], path[i + 1], self.G[path[i]][path[i + 1]])
                    for i in range(len(path) - 1)
                )
                if path_cost == float("inf"):
                    continue

                # Map node IDs to physical station names for deduplication
                station_seq = tuple(
                    self.stations[nid].station_name for nid in path if nid in self.stations
                )

                if station_seq not in seen_station_sequences:
                    seen_station_sequences.add(station_seq)
                    candidates.append(path)
                    if len(candidates) >= k:
                        break

        except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
            logger.info(
                "Candidate generator: no path found between %s and %s: %s",
                origin_id,
                destination_id,
                exc,
            )
            return []

        return candidates

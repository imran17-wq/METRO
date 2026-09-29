"""
RoutingService — service layer between API endpoints and graph routing algorithms.
Single Canonical 5-Line Graph Architecture with Dynamic Line State Controls.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

import networkx as nx

from src.graph.station_model import Station
from src.graph.metro_graph import (
    build_metro_graph,
    get_active_lines,
    set_active_lines,
    activate_line,
    deactivate_line,
)
from src.routing.route import RouteResult
from src.routing.dijkstra_router import find_dijkstra_route
from src.routing.astar_router import find_astar_route
from src.config.settings import ALL_LINES, LINE_METADATA

logger = logging.getLogger(__name__)


class StationNotFoundError(ValueError):
    """Raised when a station name cannot be resolved to any graph node."""


class SameStationError(ValueError):
    """Raised when origin and destination are the same physical station."""


class InactiveLineError(ValueError):
    """Raised when origin, destination, or route requires an inactive line."""


class NoRouteError(LookupError):
    """Raised when the graph contains no path between origin and destination."""


class RoutingService:
    def __init__(self) -> None:
        self._graph: Optional[nx.Graph] = None
        self._stations: Dict[str, Station] = {}
        self._name_index: Dict[str, List[str]] = {}

    def initialise(self) -> None:
        if self._graph is not None:
            return
        self._graph = build_metro_graph()
        from src.graph import metro_graph as mg
        self._stations = dict(mg._stations)
        self._name_index = dict(mg._name_index)
        logger.info(
            "RoutingService initialised: %d unique station names, %d nodes, %d edges.",
            len(self._name_index),
            self._graph.number_of_nodes(),
            self._graph.number_of_edges(),
        )

    def _require_init(self) -> nx.Graph:
        if self._graph is None:
            self.initialise()
        return self._graph  # type: ignore

    def get_active_lines(self) -> Set[str]:
        return get_active_lines()

    def set_active_lines(self, lines: Set[str]) -> None:
        set_active_lines(lines)

    def activate_line(self, line: str) -> None:
        activate_line(line)

    def deactivate_line(self, line: str) -> None:
        deactivate_line(line)

    def search_stations(self, query: str) -> List[Dict]:
        self._require_init()
        q = query.strip().lower()
        results = []
        seen_names: set = set()
        for name, ids in self._name_index.items():
            if q in name.lower() and name not in seen_names:
                seen_names.add(name)
                rep_station = self._stations[ids[0]]
                lines = sorted({self._stations[sid].line for sid in ids})
                results.append({
                    "name": name,
                    "lines": lines,
                    "is_interchange": rep_station.is_interchange,
                    "representative_id": ids[0],
                })
        results.sort(key=lambda x: x["name"])
        return results

    def all_stations(self) -> List[Dict]:
        self._require_init()
        seen: set = set()
        results = []
        for name, ids in self._name_index.items():
            if name in seen:
                continue
            seen.add(name)
            rep = self._stations[ids[0]]
            lines = sorted({self._stations[sid].line for sid in ids})
            statuses = [LINE_METADATA.get(l, {}).get("status", "OPERATIONAL") for l in lines]
            results.append({
                "name": name,
                "lines": lines,
                "line_statuses": statuses,
                "is_interchange": rep.is_interchange,
                "representative_id": ids[0],
            })
        results.sort(key=lambda x: x["name"])
        return results

    def _resolve_name(self, name: str) -> List[str]:
        ids = self._name_index.get(name.strip())
        if ids:
            return ids
        lower = name.strip().lower()
        for n, ids in self._name_index.items():
            if n.lower() == lower:
                return ids
        candidates = [
            (n, ids) for n, ids in self._name_index.items()
            if lower in n.lower()
        ]
        if len(candidates) == 1:
            return candidates[0][1]
        if len(candidates) > 1:
            candidates.sort(key=lambda x: len(x[0]))
            return candidates[0][1]
        return []

    def route(
        self,
        origin_name: str,
        destination_name: str,
        algorithm: str = "dijkstra",
    ) -> RouteResult:
        G = self._require_init()
        alg = algorithm.lower().strip()
        if alg not in ("dijkstra", "astar"):
            raise ValueError(f"Unknown algorithm '{algorithm}'. Choose 'dijkstra' or 'astar'.")

        origin_ids = self._resolve_name(origin_name)
        if not origin_ids:
            raise StationNotFoundError(f"Station not found: '{origin_name}'.")

        dest_ids = self._resolve_name(destination_name)
        if not dest_ids:
            raise StationNotFoundError(f"Station not found: '{destination_name}'.")

        origin_physical = self._stations[origin_ids[0]].station_name
        dest_physical = self._stations[dest_ids[0]].station_name
        if origin_physical == dest_physical:
            raise SameStationError(f"Origin and destination are the same station: '{origin_physical}'.")

        actives = get_active_lines()

        # Check if origin or destination station lines are completely inactive
        origin_lines = {self._stations[sid].line for sid in origin_ids}
        dest_lines = {self._stations[sid].line for sid in dest_ids}

        inactive_origin_lines = origin_lines - actives
        inactive_dest_lines = dest_lines - actives

        if origin_lines and not (origin_lines & actives):
            line_str = ", ".join(sorted(list(inactive_origin_lines)))
            raise InactiveLineError(
                f"Route unavailable on the currently operational network. "
                f"{line_str} Line is currently inactive and under construction."
            )

        if dest_lines and not (dest_lines & actives):
            line_str = ", ".join(sorted(list(inactive_dest_lines)))
            raise InactiveLineError(
                f"Route unavailable on the currently operational network. "
                f"{line_str} Line is currently inactive and under construction."
            )

        router = find_dijkstra_route if alg == "dijkstra" else find_astar_route

        best: Optional[RouteResult] = None
        for oid in origin_ids:
            for did in dest_ids:
                if oid == did:
                    continue
                result = router(G, oid, did, self._stations, active_lines=actives)
                if result is not None:
                    if best is None or result.total_time_min < best.total_time_min:
                        best = result

        if best is None:
            inactive_lines = set(ALL_LINES) - actives
            if inactive_lines:
                line_str = ", ".join(sorted(list(inactive_lines)))
                raise NoRouteError(
                    f"Route unavailable on the currently operational network between '{origin_name}' and '{destination_name}'. "
                    f"{line_str} Line(s) are currently inactive and under construction."
                )
            raise NoRouteError(f"No route found between '{origin_name}' and '{destination_name}'.")

        return best

    def dynamic_route(
        self,
        origin_name: str,
        destination_name: str,
        network_state_service: Any,
        profile: str = "BALANCED",
        k: int = 5,
    ) -> DynamicRouteResult:
        """
        Phase 4 Intelligent Dynamic Rerouting.

        1. Resolves origin and destination names.
        2. Enforces active line eligibility.
        3. Generates K candidate routes using Yen's K-shortest paths algorithm.
        4. Scores candidates against dynamic edge costs from network_state_service.
        5. Applies Pareto dominance filtering to eliminate strictly inferior alternatives.
        6. Generates data-driven explanations for recommended route.
        7. Returns DynamicRouteResult containing recommended route & alternatives.
        """
        from src.routing.edge_cost import DynamicCostCalculator
        from src.routing.candidate_generator import CandidateRouteGenerator
        from src.routing.route_scorer import RouteScorer
        from src.routing.dominance import ParetoFilter
        from src.routing.explanation_generator import RouteExplanationGenerator
        from src.routing.path_parser import build_route_result
        from src.routing.route import DynamicRouteResult
        from src.config.routing_weights import ROUTE_PROFILES, DEFAULT_PROFILE

        G = self._require_init()
        prof = profile.upper().strip()
        if prof not in ROUTE_PROFILES:
            prof = DEFAULT_PROFILE

        origin_ids = self._resolve_name(origin_name)
        if not origin_ids:
            raise StationNotFoundError(f"Station not found: '{origin_name}'.")

        dest_ids = self._resolve_name(destination_name)
        if not dest_ids:
            raise StationNotFoundError(f"Station not found: '{destination_name}'.")

        origin_physical = self._stations[origin_ids[0]].station_name
        dest_physical = self._stations[dest_ids[0]].station_name
        if origin_physical == dest_physical:
            raise SameStationError(f"Origin and destination are the same station: '{origin_physical}'.")

        actives = get_active_lines()

        origin_lines = {self._stations[sid].line for sid in origin_ids}
        dest_lines = {self._stations[sid].line for sid in dest_ids}

        if origin_lines and not (origin_lines & actives):
            line_str = ", ".join(sorted(list(origin_lines - actives)))
            raise InactiveLineError(
                f"Route unavailable on the currently operational network. "
                f"{line_str} Line is currently inactive and under construction."
            )

        if dest_lines and not (dest_lines & actives):
            line_str = ", ".join(sorted(list(dest_lines - actives)))
            raise InactiveLineError(
                f"Route unavailable on the currently operational network. "
                f"{line_str} Line is currently inactive and under construction."
            )

        edge_index = network_state_service.edge_index if network_state_service else {}
        cost_calc = DynamicCostCalculator(edge_index)
        cand_gen = CandidateRouteGenerator(G, self._stations)
        scorer = RouteScorer(G, self._stations)

        all_candidates: List[List[str]] = []
        for oid in origin_ids:
            for did in dest_ids:
                if oid == did:
                    continue
                paths = cand_gen.generate_candidates(
                    oid, did, cost_calc, actives, profile_weights=ROUTE_PROFILES[prof], k=k
                )
                all_candidates.extend(paths)

        if not all_candidates:
            # Fallback to standard Dijkstra route if candidate generator yielded nothing
            fallback_res = self.route(origin_name, destination_name, algorithm="dijkstra")
            fallback_res.route_profile = prof
            fallback_res.prediction_source = "FALLBACK"
            return DynamicRouteResult(
                recommended=fallback_res,
                alternatives=[],
                profile=prof,
                network_state_timestamp=network_state_service.last_refreshed_utc or "N/A" if network_state_service else "N/A",
                model_versions={"status": "fallback"},
                data_provenance=network_state_service.provenance() if network_state_service else {"prediction": "FALLBACK"},
            )

        # Score candidates
        scored_candidates = scorer.score_and_rank_candidates(
            all_candidates, cost_calc, profile=prof
        )

        if not scored_candidates:
            raise NoRouteError(f"No valid route found between '{origin_name}' and '{destination_name}'.")

        # Apply Pareto dominance filter
        filtered_candidates = ParetoFilter.filter_dominated_candidates(scored_candidates)

        # Build RouteResult objects
        built_results: List[RouteResult] = []
        scores_list = [sc for _, sc in filtered_candidates]

        for idx, (path, sc) in enumerate(filtered_candidates):
            rr = build_route_result(G, path, sc.predicted_travel_time_min, "dynamic", self._stations)
            rr.route_profile = prof
            rr.total_dynamic_cost = sc.total_score
            rr.predicted_travel_time = sc.predicted_travel_time_min
            rr.predicted_congestion = sc.predicted_congestion_pct
            rr.delay_risk = sc.delay_risk_prob
            rr.reliability_score = sc.reliability_score
            rr.transfer_count = sc.transfer_count
            rr.score_breakdown = sc.score_breakdown
            rr.prediction_source = sc.prediction_source

            if idx == 0:
                # Top recommended route gets the generated explanation
                alts_scores = scores_list[1:]
                rr.recommendation_reason = RouteExplanationGenerator.generate_explanation(
                    sc, alts_scores, profile=prof
                )
            else:
                rr.recommendation_reason = f"Alternative route option ({prof} profile rank {idx + 1})."

            built_results.append(rr)

        recommended = built_results[0]
        alternatives = built_results[1:]

        prov = (
            network_state_service.provenance()
            if network_state_service
            else {"prediction": "FALLBACK", "route": "DERIVED"}
        )

        return DynamicRouteResult(
            recommended=recommended,
            alternatives=alternatives,
            profile=prof,
            network_state_timestamp=(
                network_state_service.last_refreshed_utc if network_state_service else "N/A"
            ) or "N/A",
            model_versions={"congestion": "1.0.0", "travel_time": "1.0.0", "delay_risk": "1.0.0"},
            data_provenance=prov,
        )


    def network_topology(self) -> Dict:
        G = self._require_init()
        actives = get_active_lines()

        stations_out = []
        for sid, s in self._stations.items():
            meta = LINE_METADATA.get(s.line, {"status": "OPERATIONAL"})
            stations_out.append({
                "id": sid,
                "name": s.station_name,
                "line": s.line,
                "sequence": s.sequence,
                "is_interchange": s.is_interchange,
                "interchange_lines": s.interchange_lines,
                "line_status": meta["status"],
                "is_active": s.line in actives,
                "x": 0.0,
                "y": 0.0,
            })

        edges_out = []
        for u, v, data in G.edges(data=True):
            line = data.get("line", "")
            edge_type = "transfer" if line == "TRANSFER" else "segment"
            edges_out.append({
                "from_id": u,
                "to_id": v,
                "line": line,
                "edge_type": edge_type,
                "edge_id": data.get("edge_id", ""),
            })

        interchange_locs = [
            {
                "name": "Nadaprabhu Kempegowda Station (Majestic)",
                "station_ids": ["PL22", "GL17"],
                "lines": ["Purple", "Green"],
                "x": 580.0,
                "y": 380.0,
            },
            {
                "name": "Rashtreeya Vidyalaya Road (RV Road)",
                "station_ids": ["GL24", "YL01"],
                "lines": ["Green", "Yellow"],
                "x": 580.0,
                "y": 700.0,
            },
            {
                "name": "Jayadeva Hospital",
                "station_ids": ["YL03", "PK05"],
                "lines": ["Yellow", "Pink"],
                "x": 763.0,
                "y": 700.0,
            },
            {
                "name": "Central Silk Board",
                "station_ids": ["YL05", "BL23"],
                "lines": ["Yellow", "Blue"],
                "x": 963.0,
                "y": 700.0,
            },
            {
                "name": "Mahatma Gandhi Road (MG Road)",
                "station_ids": ["PL18", "PK11"],
                "lines": ["Purple", "Pink"],
                "x": 843.0,
                "y": 380.0,
            },
            {
                "name": "Krishnarajapura (KR Pura)",
                "station_ids": ["PL12", "BL12"],
                "lines": ["Purple", "Blue"],
                "x": 1103.0,
                "y": 240.0,
            },
            {
                "name": "Nagawara",
                "station_ids": ["PK18", "BL06"],
                "lines": ["Pink", "Blue"],
                "x": 990.0,
                "y": 80.0,
            },
        ]

        return {
            "stations": stations_out,
            "edges": edges_out,
            "lines": ALL_LINES,
            "active_lines": sorted(list(actives)),
            "line_metadata": LINE_METADATA,
            "interchange_locations": interchange_locs,
        }

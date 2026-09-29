"""
src/routing/route_scorer.py

RouteScorer — Phase 4 Route Scoring Engine.

Responsibilities
----------------
1. Calculate dynamic edge costs for each segment in a candidate path.
2. Aggregate raw and normalized metric totals across the route.
3. Calculate component breakdown (travel time, congestion penalty, delay penalty, transfer penalty).
4. Apply profile weights (FASTEST, BALANCED, LEAST_CONGESTED, MOST_RELIABLE, FEWEST_TRANSFERS).
5. Compute reliability score (1.0 - delay_risk).
6. Rank candidate routes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import networkx as nx

from src.config.routing_weights import (
    DEFAULT_PROFILE,
    ROUTE_PROFILES,
    ROUTING_WEIGHTS,
)
from src.graph.station_model import Station
from src.routing.edge_cost import DynamicCostCalculator, RouteEdgeCost

logger = logging.getLogger(__name__)


@dataclass
class RouteScore:
    """
    Evaluated metric summary and score breakdown for a single candidate route.
    """
    total_score: float                  # Final weighted score (lower is better)
    predicted_travel_time_min: float    # Sum of segment predicted travel times (min)
    predicted_congestion_pct: float     # Average predicted congestion % across edges
    delay_risk_prob: float              # Max or combined delay probability across edges (0.0 to 1.0)
    reliability_score: float            # 1.0 - delay_risk_prob (0.0 to 1.0)
    transfer_count: int                 # Number of transfers
    transfer_penalty_min: float         # Transfer penalty contribution in minutes
    prediction_source: str              # "ML_MODEL", "FALLBACK", "SCHEDULED"

    # Score breakdown (all components in minute-equivalent values before weighting)
    score_breakdown: Dict[str, float]

    # Individual edge cost details
    edge_costs: List[RouteEdgeCost]


class RouteScorer:
    """
    Evaluates raw node-ID paths against dynamic network state and profile weights.
    """

    def __init__(self, graph: nx.Graph, stations: Dict[str, Station]) -> None:
        self.G = graph
        self.stations = stations

    def score_path(
        self,
        path: List[str],
        cost_calculator: DynamicCostCalculator,
        profile: str = DEFAULT_PROFILE,
    ) -> Optional[RouteScore]:
        """
        Evaluate a single node-ID path using dynamic cost metrics and profile weights.

        Parameters
        ----------
        path            : List of node IDs representing route
        cost_calculator : DynamicCostCalculator instance
        profile         : Profile name (e.g. "BALANCED", "FASTEST", ...)

        Returns
        -------
        RouteScore dataclass or None if path contains impassable edge.
        """
        if len(path) < 2:
            return None

        profile_weights = ROUTE_PROFILES.get(profile, ROUTE_PROFILES[DEFAULT_PROFILE])

        edge_costs: List[RouteEdgeCost] = []
        total_tt: float = 0.0
        sum_congestion: float = 0.0
        segment_count: int = 0
        max_delay_risk: float = 0.0
        transfer_count: int = 0
        pred_sources: set = set()

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_data = self.G[u][v]

            cost = cost_calculator.compute(u, v, edge_data)
            if cost.travel_time == float("inf"):
                return None  # Impassable edge

            edge_costs.append(cost)
            pred_sources.add(cost.prediction_source)

            if cost.is_transfer:
                transfer_count += 1
                total_tt += cost.travel_time
            else:
                total_tt += cost.travel_time
                sum_congestion += cost.raw_congestion_pct
                segment_count += 1
                if cost.raw_delay_risk > max_delay_risk:
                    max_delay_risk = cost.raw_delay_risk

        avg_congestion = (sum_congestion / segment_count) if segment_count > 0 else 0.0

        # Component minute-equivalents for breakdown
        tt_comp = total_tt
        cong_comp = sum(c.congestion_penalty for c in edge_costs)
        delay_comp = sum(c.delay_penalty for c in edge_costs)
        xfer_comp = sum(c.transfer_penalty for c in edge_costs)

        # Apply profile weight multipliers
        w_t = profile_weights["travel_time"]
        w_c = profile_weights["congestion"]
        w_d = profile_weights["delay_risk"]
        w_r = profile_weights["transfer"]

        total_score = (
            w_t * tt_comp
            + w_c * cong_comp
            + w_d * delay_comp
            + w_r * xfer_comp
        )

        reliability_score = round(max(0.0, 1.0 - max_delay_risk), 4)

        overall_source = (
            "SYNTHETIC MODEL OUTPUT"
            if "SYNTHETIC MODEL OUTPUT" in pred_sources or "ML_MODEL" in pred_sources
            else ("FALLBACK" if "FALLBACK" in pred_sources else "SCHEDULED")
        )

        breakdown = {
            "travel_time": round(tt_comp, 2),
            "congestion_penalty": round(cong_comp, 2),
            "delay_penalty": round(delay_comp, 2),
            "transfer_penalty": round(xfer_comp, 2),
            "total": round(total_score, 2),
        }

        return RouteScore(
            total_score=round(total_score, 2),
            predicted_travel_time_min=round(total_tt, 2),
            predicted_congestion_pct=round(avg_congestion, 2),
            delay_risk_prob=round(max_delay_risk, 4),
            reliability_score=reliability_score,
            transfer_count=transfer_count,
            transfer_penalty_min=round(xfer_comp, 2),
            prediction_source=overall_source,
            score_breakdown=breakdown,
            edge_costs=edge_costs,
        )

    def score_and_rank_candidates(
        self,
        candidate_paths: List[List[str]],
        cost_calculator: DynamicCostCalculator,
        profile: str = DEFAULT_PROFILE,
    ) -> List[Tuple[List[str], RouteScore]]:
        """
        Evaluate and rank a list of candidate node-ID paths.

        Returns list of (path, RouteScore) tuples sorted by total_score ascending.
        """
        scored: List[Tuple[List[str], RouteScore]] = []

        for path in candidate_paths:
            score = self.score_path(path, cost_calculator, profile)
            if score is not None:
                scored.append((path, score))

        scored.sort(key=lambda item: item[1].total_score)
        return scored

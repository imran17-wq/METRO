"""
src/routing/dominance.py

Pareto Route Dominance Filter for Phase 4 Intelligent Dynamic Rerouting.

Rule
----
Route A dominates Route B if:
1. Route A is no worse than Route B in all 4 key dimensions:
   - Travel time (A.travel_time <= B.travel_time)
   - Congestion (A.congestion <= B.congestion)
   - Delay risk (A.delay_risk <= B.delay_risk)
   - Transfers (A.transfers <= B.transfers)
2. AND Route A is strictly better than Route B in at least one of these 4 dimensions.

Dominated alternative routes are excluded from comparison results to prevent
showing clearly inferior options in the UI.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from src.routing.route_scorer import RouteScore

logger = logging.getLogger(__name__)

# Tolerance epsilon for floating point comparison
EPSILON = 1e-4


def is_dominated(candidate: RouteScore, benchmark: RouteScore) -> bool:
    """
    Check if `candidate` is Pareto-dominated by `benchmark`.

    Returns True if benchmark is no worse in all dimensions and strictly better
    in at least one.
    """
    c_tt = candidate.predicted_travel_time_min
    b_tt = benchmark.predicted_travel_time_min

    c_cg = candidate.predicted_congestion_pct
    b_cg = benchmark.predicted_congestion_pct

    c_dr = candidate.delay_risk_prob
    b_dr = benchmark.delay_risk_prob

    c_tf = candidate.transfer_count
    b_tf = benchmark.transfer_count

    # Condition 1: Benchmark is no worse in any dimension
    no_worse = (
        (b_tt <= c_tt + EPSILON)
        and (b_cg <= c_cg + EPSILON)
        and (b_dr <= c_dr + EPSILON)
        and (b_tf <= c_tf)
    )

    if not no_worse:
        return False

    # Condition 2: Benchmark is strictly better in at least one dimension
    strictly_better = (
        (b_tt < c_tt - EPSILON)
        or (b_cg < c_cg - EPSILON)
        or (b_dr < c_dr - EPSILON)
        or (b_tf < c_tf)
    )

    return strictly_better


class ParetoFilter:
    """
    Filters out Pareto-dominated routes from candidate results.
    """

    @staticmethod
    def filter_dominated_candidates(
        scored_candidates: List[Tuple[List[str], RouteScore]]
    ) -> List[Tuple[List[str], RouteScore]]:
        """
        Takes a list of (path, RouteScore) tuples and returns only non-dominated items,
        preserving original rank ordering.

        The top-ranked (first) route is always preserved as the primary reference.
        """
        if len(scored_candidates) <= 1:
            return scored_candidates

        non_dominated: List[Tuple[List[str], RouteScore]] = []

        for path, score in scored_candidates:
            dominated = False
            for existing_path, existing_score in non_dominated:
                if is_dominated(score, existing_score):
                    dominated = True
                    logger.debug(
                        "Route path %s dominated by %s", path, existing_path
                    )
                    break
            if not dominated:
                non_dominated.append((path, score))

        return non_dominated

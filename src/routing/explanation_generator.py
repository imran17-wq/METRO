"""
src/routing/explanation_generator.py

Data-driven route explanation generator for Phase 4 Intelligent Dynamic Rerouting.

Generates human-readable explanations ("Why this route?") based strictly on
actual metric differences between the recommended route and alternative candidate routes.

Examples:
- "Recommended because it is 3.2 minutes faster than the next best route while avoiding a high-congestion segment."
- "Recommended because it has 18.5% lower predicted congestion and lower delay risk."
- "Recommended for fewest transfers (0 vs 1), saving 3.0 min in platform transfer time."
- "Best balance of travel time (28.5 min), congestion (24.2%), and reliability (98.0%)."
"""
from __future__ import annotations

import logging
from typing import List, Optional

from src.routing.route_scorer import RouteScore

logger = logging.getLogger(__name__)


class RouteExplanationGenerator:
    """
    Generates data-driven explanations for route recommendations.
    """

    @staticmethod
    def generate_explanation(
        recommended_score: RouteScore,
        alternatives: Optional[List[RouteScore]] = None,
        profile: str = "BALANCED",
    ) -> str:
        """
        Generate explanation string based on metric comparison with alternatives.

        Parameters
        ----------
        recommended_score : RouteScore of chosen route
        alternatives        : List of alternative RouteScores
        profile            : Selected route profile

        Returns
        -------
        String explaining why this route is recommended.
        """
        r = recommended_score
        alts = alternatives or []

        if not alts:
            if profile == "FASTEST":
                return f"Fastest direct route available ({r.predicted_travel_time_min:.1f} min travel time)."
            elif profile == "LEAST_CONGESTED":
                return f"Lowest congestion route available ({r.predicted_congestion_pct:.1f}% average congestion)."
            elif profile == "MOST_RELIABLE":
                return f"Most reliable route available ({r.reliability_score * 100:.1f}% reliability score)."
            elif profile == "FEWEST_TRANSFERS":
                return f"Direct route requiring {r.transfer_count} transfer(s)."
            else:
                return f"Optimal route ({r.predicted_travel_time_min:.1f} min, {r.predicted_congestion_pct:.1f}% congestion, {r.transfer_count} transfers)."

        # Compare against the primary alternative (second best overall route)
        alt = alts[0]

        tt_diff = alt.predicted_travel_time_min - r.predicted_travel_time_min
        cg_diff = alt.predicted_congestion_pct - r.predicted_congestion_pct
        dr_diff = alt.delay_risk_prob - r.delay_risk_prob
        tf_diff = alt.transfer_count - r.transfer_count

        reasons: List[str] = []

        # Time difference
        if tt_diff > 0.5:
            reasons.append(f"{tt_diff:.1f} minutes faster")
        elif tt_diff < -0.5:
            # Slower but chosen due to profile preferences (e.g. lower congestion)
            pass

        # Congestion difference
        if cg_diff > 5.0:
            reasons.append(f"{cg_diff:.1f}% lower predicted congestion")

        # Transfer difference
        if tf_diff > 0:
            reasons.append(f"{tf_diff} fewer transfer{'s' if tf_diff > 1 else ''}")

        # Reliability difference
        if dr_diff > 0.05:
            reasons.append("substantially lower delay risk")

        if profile == "FASTEST":
            if tt_diff > 0.1:
                return f"Recommended as the fastest route: {tt_diff:.1f} min faster than alternative option."
            return f"Fastest route with predicted travel time of {r.predicted_travel_time_min:.1f} min."

        if profile == "LEAST_CONGESTED":
            if cg_diff > 1.0:
                return f"Recommended for lowest congestion: {cg_diff:.1f}% lower predicted congestion than alternative option."
            return f"Optimal congestion profile with average load of {r.predicted_congestion_pct:.1f}%."

        if profile == "MOST_RELIABLE":
            if dr_diff > 0.01 or (r.reliability_score > alt.reliability_score):
                rel_pct = (r.reliability_score - alt.reliability_score) * 100
                if rel_pct > 0.5:
                    return f"Recommended for highest reliability: {rel_pct:.1f}% higher reliability rating than alternative option."
            return f"Highest reliability route with {r.reliability_score * 100:.1f}% reliability score."

        if profile == "FEWEST_TRANSFERS":
            if tf_diff > 0:
                return f"Recommended for fewest transfers: {r.transfer_count} transfer(s) vs {alt.transfer_count} on alternative route."
            return f"Minimises line transfers ({r.transfer_count} transfer(s))."

        # Default BALANCED profile explanation synthesis
        if reasons:
            joined = " and ".join(reasons)
            return f"Recommended because it offers {joined}."

        return f"Best overall balance of travel time ({r.predicted_travel_time_min:.1f} min), congestion ({r.predicted_congestion_pct:.1f}%), and reliability ({r.reliability_score * 100:.1f}%)."

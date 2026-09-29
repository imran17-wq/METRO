"""
src/routing/edge_cost.py

Dynamic edge cost model for Phase 4 Intelligent Dynamic Rerouting.

RouteEdgeCost holds all cost components for a single edge.
DynamicCostCalculator converts raw NetworkState edge data into a cost,
using configurable weights from routing_weights.py.

COST FORMULA (per edge)
-----------------------
  travel_time_score   = predicted_travel_time_min
                        (falls back to scheduled_time_min → FALLBACK_SEGMENT_TIME_MIN)

  congestion_score    = (predicted_congestion_pct / 100.0) * CONGESTION_SCALE_MIN

  delay_score         = delay_risk_prob * DELAY_SCALE_MIN

  transfer_score      = TRANSFER_BASE_MIN  (only on TRANSFER edges)

  total_cost          = (w_t * travel_time_score
                       + w_c * congestion_score
                       + w_d * delay_score
                       + w_r * transfer_score)

Components are kept separately on RouteEdgeCost for use in explanations
and score breakdowns.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.config.routing_weights import (
    CONGESTION_SCALE_MIN,
    DELAY_SCALE_MIN,
    TRANSFER_BASE_MIN,
    FALLBACK_CONGESTION_PCT,
    FALLBACK_DELAY_RISK,
    FALLBACK_SEGMENT_TIME_MIN,
    FALLBACK_TRANSFER_TIME_MIN,
    ROUTING_WEIGHTS,
)

logger = logging.getLogger(__name__)


@dataclass
class RouteEdgeCost:
    """
    Per-edge cost breakdown for a single segment or transfer.

    All components are in normalized minute-equivalent units so they can
    be combined with profile weight multipliers.
    """
    edge_id: str
    line: str
    is_transfer: bool

    # Raw predictions (stored for provenance / debugging)
    raw_travel_time_min: float
    raw_congestion_pct: float
    raw_delay_risk: float
    prediction_source: str          # "ML_MODEL", "FALLBACK", "SCHEDULED"

    # Normalized score components (minute-equivalent)
    travel_time: float              # = raw_travel_time_min
    congestion_penalty: float       # = (cong_pct / 100) * CONGESTION_SCALE_MIN
    delay_penalty: float            # = delay_risk * DELAY_SCALE_MIN
    transfer_penalty: float         # = TRANSFER_BASE_MIN if transfer else 0.0

    # Weighted total (profile-specific weights applied later in RouteScorer)
    total_cost: float = field(init=False)

    def __post_init__(self) -> None:
        self.total_cost = (
            ROUTING_WEIGHTS["travel_time"] * self.travel_time
            + ROUTING_WEIGHTS["congestion"] * self.congestion_penalty
            + ROUTING_WEIGHTS["delay_risk"] * self.delay_penalty
            + ROUTING_WEIGHTS["transfer"] * self.transfer_penalty
        )


class DynamicCostCalculator:
    """
    Converts a per-edge NetworkState dict into a RouteEdgeCost.

    The NetworkState dict is keyed by edge_id and contains the fields
    produced by NetworkStateBuilder.build_state():

        edge_id, from_id, to_id, line, line_status, active,
        scheduled_time_min, predicted_travel_time_min,
        predicted_congestion_pct, congestion_band,
        delay_risk_prob, data_provenance

    If an edge is marked active=False it is treated as unavailable (inf cost).
    If ML predictions are absent, configurable fallback values are used and
    prediction_source is set to "FALLBACK".
    """

    def __init__(self, edge_state_index: Dict[str, Dict[str, Any]]) -> None:
        """
        Parameters
        ----------
        edge_state_index : dict[edge_id → edge_state_dict]
            Pre-built index from NetworkStateService.
        """
        self._idx = edge_state_index

    def compute(
        self,
        u: str,
        v: str,
        edge_data: Dict[str, Any],
    ) -> RouteEdgeCost:
        """
        Compute the dynamic cost for edge (u, v).

        Parameters
        ----------
        u, v       : node IDs (graph endpoints)
        edge_data  : NetworkX edge attribute dict

        Returns
        -------
        RouteEdgeCost with total_cost = inf if edge is unavailable.
        """
        edge_id: str = edge_data.get("edge_id", f"E_{u}_{v}")
        line: str = edge_data.get("line", "")
        is_transfer = (line == "TRANSFER")

        state = self._idx.get(edge_id)

        # ── Availability check ──────────────────────────────────────────────
        if state is not None and not state.get("active", True):
            return _inf_cost(edge_id, line, is_transfer)

        # ── Extract predictions ─────────────────────────────────────────────
        if is_transfer:
            # Transfer edges: no ML congestion/delay predictions
            raw_tt = FALLBACK_TRANSFER_TIME_MIN
            raw_cong = 0.0
            raw_delay = 0.0
            src = "SCHEDULED"
        elif state is None:
            # Edge not in NetworkState index → full fallback
            raw_tt = edge_data.get("scheduled_time_min") or FALLBACK_SEGMENT_TIME_MIN
            raw_cong = FALLBACK_CONGESTION_PCT
            raw_delay = FALLBACK_DELAY_RISK
            src = "FALLBACK"
            logger.debug("Edge %s not in NetworkState — using fallback costs.", edge_id)
        else:
            # ML predictions present
            raw_tt_ml = state.get("predicted_travel_time_min")
            raw_cong_ml = state.get("predicted_congestion_pct")
            raw_delay_ml = state.get("delay_risk_prob")

            raw_tt = (
                float(raw_tt_ml)
                if raw_tt_ml is not None
                else (edge_data.get("scheduled_time_min") or FALLBACK_SEGMENT_TIME_MIN)
            )
            raw_cong = float(raw_cong_ml) if raw_cong_ml is not None else FALLBACK_CONGESTION_PCT
            raw_delay = float(raw_delay_ml) if raw_delay_ml is not None else FALLBACK_DELAY_RISK

            # Determine prediction source
            if raw_tt_ml is not None or raw_cong_ml is not None:
                src = state.get("data_provenance", "ML_MODEL")
            else:
                src = "FALLBACK"

        # ── Normalize ───────────────────────────────────────────────────────
        cong_penalty = (raw_cong / 100.0) * CONGESTION_SCALE_MIN
        delay_penalty = raw_delay * DELAY_SCALE_MIN
        xfer_penalty = TRANSFER_BASE_MIN if is_transfer else 0.0

        return RouteEdgeCost(
            edge_id=edge_id,
            line=line,
            is_transfer=is_transfer,
            raw_travel_time_min=raw_tt,
            raw_congestion_pct=raw_cong,
            raw_delay_risk=raw_delay,
            prediction_source=src,
            travel_time=raw_tt,
            congestion_penalty=cong_penalty,
            delay_penalty=delay_penalty,
            transfer_penalty=xfer_penalty,
        )

    def edge_weight(
        self,
        u: str,
        v: str,
        edge_data: Dict[str, Any],
        profile_weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Return a scalar edge weight suitable for use as the NetworkX weight
        function.  profile_weights overrides ROUTING_WEIGHTS if supplied.

        Returns float('inf') for inactive edges.
        """
        cost = self.compute(u, v, edge_data)
        if cost.travel_time == float("inf"):
            return float("inf")

        pw = profile_weights or ROUTING_WEIGHTS
        return (
            pw.get("travel_time", 1.0) * cost.travel_time
            + pw.get("congestion", 0.25) * cost.congestion_penalty
            + pw.get("delay_risk", 0.20) * cost.delay_penalty
            + pw.get("transfer", 2.0) * cost.transfer_penalty
        )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _inf_cost(edge_id: str, line: str, is_transfer: bool) -> RouteEdgeCost:
    """Return a RouteEdgeCost representing an impassable edge."""
    return RouteEdgeCost(
        edge_id=edge_id,
        line=line,
        is_transfer=is_transfer,
        raw_travel_time_min=float("inf"),
        raw_congestion_pct=0.0,
        raw_delay_risk=0.0,
        prediction_source="UNAVAILABLE",
        travel_time=float("inf"),
        congestion_penalty=0.0,
        delay_penalty=0.0,
        transfer_penalty=0.0,
    )

"""
src/ml/network_state.py

NetworkStateBuilder: Combines static canonical 5-line graph + ML predictions + line active states.
Does NOT rebuild the NetworkX graph. Preserves graph topology.
Enforces User Correction 2 for Pink/Blue: predictions are null, active is false.
"""
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import networkx as nx

from src.graph.metro_graph import build_metro_graph
from src.config.settings import DEFAULT_ACTIVE_LINES, LINE_METADATA

logger = logging.getLogger(__name__)


def compute_congestion_band(pct: Optional[float]) -> Optional[str]:
    """Derive congestion band from congestion percentage."""
    if pct is None:
        return None
    if pct < 20.0:
        return "LOW"
    if pct < 50.0:
        return "MEDIUM"
    if pct < 80.0:
        return "HIGH"
    return "CRITICAL"


class NetworkStateBuilder:
    """
    Constructs edge network state for routing and UI visualization.
    Static graph is loaded once into memory.
    """

    def __init__(self, graph: Optional[nx.Graph] = None) -> None:
        self.G: nx.Graph = graph if graph is not None else build_metro_graph()

    def build_state(
        self,
        date_str: str,
        time_slot: int,
        congestion_model: Optional[Any] = None,
        travel_time_model: Optional[Any] = None,
        delay_risk_model: Optional[Any] = None,
        active_lines: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build per-edge network state for all 127 edges in the canonical graph.

        Returns list of dicts with edge-level predictions and state metadata.
        """
        if active_lines is None:
            active_lines = set(DEFAULT_ACTIVE_LINES)

        # Prepare dummy input query DataFrame for ML model predictions
        query_rows = []
        edge_keys = []

        for u, v, data in self.G.edges(data=True):
            edge_id = data.get("edge_id", f"E_{u}_{v}")
            line = data.get("line", "Unknown")
            if line == "TRANSFER":
                u_line = self.G.nodes[u].get("line", "")
                v_line = self.G.nodes[v].get("line", "")
                is_active = (u_line in active_lines) and (v_line in active_lines)
            else:
                is_active = line in active_lines

            query_rows.append({
                "date": pd.to_datetime(date_str),
                "time_slot": time_slot,
                "slot_start": f"{time_slot * 15 // 60:02d}:{time_slot * 15 % 60:02d}",
                "edge_id": edge_id,
                "line": line,
                "u": u,
                "v": v,
                "is_active": is_active,
            })
            edge_keys.append((u, v, edge_id, line, is_active))

        query_df = pd.DataFrame(query_rows)

        # Run ML predictions for operational lines (Purple, Green, Yellow, TRANSFER)
        op_query_df = query_df[query_df["line"].isin(["Purple", "Green", "Yellow", "TRANSFER"])].copy()

        cong_preds: Dict[str, float] = {}
        tt_preds: Dict[str, float] = {}
        delay_probs: Dict[str, float] = {}

        if congestion_model is not None and not op_query_df.empty:
            try:
                preds = congestion_model.predict_dataframe(op_query_df)
                cong_preds = dict(zip(op_query_df["edge_id"], preds))
            except Exception as e:
                logger.error("Error predicting congestion: %s", e)

        if travel_time_model is not None and not op_query_df.empty:
            try:
                preds = travel_time_model.predict_dataframe(op_query_df)
                tt_preds = dict(zip(op_query_df["edge_id"], preds))
            except Exception as e:
                logger.error("Error predicting travel time: %s", e)

        if delay_risk_model is not None and not op_query_df.empty:
            try:
                probs = delay_risk_model.predict_proba(op_query_df)
                delay_probs = dict(zip(op_query_df["edge_id"], probs))
            except Exception as e:
                logger.error("Error predicting delay risk: %s", e)

        state_entries = []
        for u, v, edge_id, line, is_active in edge_keys:
            base_status = LINE_METADATA.get(line, {}).get("status", "OPERATIONAL")

            if line in ["Pink", "Blue"]:
                if is_active:
                    state_entries.append({
                        "edge_id": edge_id,
                        "from_id": u,
                        "to_id": v,
                        "line": line,
                        "line_status": "SIMULATED SERVICE",
                        "active": True,
                        "scheduled_time_min": 2.5,
                        "predicted_travel_time_min": 2.5,
                        "predicted_congestion_pct": 15.0,
                        "congestion_band": "LOW",
                        "delay_risk_prob": 0.02,
                        "data_provenance": "SIMULATED SERVICE",
                    })
                else:
                    state_entries.append({
                        "edge_id": edge_id,
                        "from_id": u,
                        "to_id": v,
                        "line": line,
                        "line_status": "UNDER_CONSTRUCTION",
                        "active": False,
                        "scheduled_time_min": 2.5,
                        "predicted_travel_time_min": None,
                        "predicted_congestion_pct": None,
                        "congestion_band": None,
                        "delay_risk_prob": None,
                        "data_provenance": "NO_SYNTHETIC_DATA",
                    })
            else:
                c_pct = cong_preds.get(edge_id, 15.0)
                t_min = tt_preds.get(edge_id, 2.5 if line != "TRANSFER" else 3.0)
                d_prob = delay_probs.get(edge_id, 0.02)
                c_band = compute_congestion_band(c_pct)

                state_entries.append({
                    "edge_id": edge_id,
                    "from_id": u,
                    "to_id": v,
                    "line": line,
                    "line_status": base_status,
                    "active": is_active,
                    "scheduled_time_min": 3.0 if line == "TRANSFER" else 2.5,
                    "predicted_travel_time_min": round(float(t_min), 2),
                    "predicted_congestion_pct": round(float(c_pct), 2),
                    "congestion_band": c_band,
                    "delay_risk_prob": round(float(d_prob), 4),
                    "data_provenance": "SYNTHETIC MODEL OUTPUT",
                })

        return state_entries

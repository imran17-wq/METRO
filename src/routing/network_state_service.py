"""
src/routing/network_state_service.py

NetworkStateService — clean service boundary between the routing layer and
the ML/prediction infrastructure.

Responsibilities
----------------
- Wrap NetworkStateBuilder.build_state() and return an indexed dict keyed
  by edge_id for O(1) lookup during routing.
- Cache the last-built state so repeated routing calls within the same
  request do not rebuild.
- Record the timestamp of every state build so routing responses can
  report exactly which network state was used.
- Expose refresh() for future live-data ingestion (Phase 5+).

Design note
-----------
No websockets or real-time feeds are implemented here.  The service boundary
exists so that Phase 5 can replace or extend `refresh()` without touching
routing logic.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.ml.network_state import NetworkStateBuilder

logger = logging.getLogger(__name__)


class NetworkStateService:
    """
    Caching service that provides per-edge network state to the routing layer.

    Parameters
    ----------
    network_state_builder : NetworkStateBuilder
        Pre-constructed builder (shares the canonical graph with RoutingService).
    """

    def __init__(self, network_state_builder: NetworkStateBuilder) -> None:
        self._builder = network_state_builder
        self._edge_index: Dict[str, Dict[str, Any]] = {}
        self._last_date: Optional[str] = None
        self._last_time_slot: Optional[int] = None
        self._last_refreshed_utc: Optional[str] = None
        self._prediction_source: str = "NONE"
        self._overlay_dict: Dict[str, Dict[str, Any]] = {}

    # ── Phase 5 Disruption Overlay Controls ──────────────────────────────

    def apply_disruption_overlay(self, overlay: Dict[str, Dict[str, Any]]) -> None:
        """
        Apply edge disruption overlay dict onto base network state.
        Modifies effective_active, travel_time, congestion values.
        """
        self._overlay_dict = dict(overlay)
        logger.info("Disruption overlay applied to NetworkStateService (%d edges affected).", len(self._overlay_dict))

    def clear_disruption_overlay(self) -> None:
        """
        Remove disruption overlay and restore exact base network state.
        """
        self._overlay_dict = {}
        logger.info("Disruption overlay cleared from NetworkStateService. Base state restored.")

    @property
    def overlay_dict(self) -> Dict[str, Dict[str, Any]]:
        return self._overlay_dict

    @property
    def is_disruption_active(self) -> bool:
        return bool(self._overlay_dict)

    # ── Public API ────────────────────────────────────────────────────────

    def refresh(
        self,
        date_str: str,
        time_slot: int,
        congestion_model: Optional[Any] = None,
        travel_time_model: Optional[Any] = None,
        delay_risk_model: Optional[Any] = None,
        active_lines: Optional[set] = None,
    ) -> None:
        """
        Build (or rebuild) the network state for the given date and time slot.
        """
        logger.info(
            "NetworkStateService: building state for date=%s slot=%d", date_str, time_slot
        )
        if active_lines is None:
            from src.graph.metro_graph import get_active_lines
            active_lines = get_active_lines()

        state_list: List[Dict[str, Any]] = self._builder.build_state(
            date_str=date_str,
            time_slot=time_slot,
            congestion_model=congestion_model,
            travel_time_model=travel_time_model,
            delay_risk_model=delay_risk_model,
            active_lines=active_lines,
        )

        self._edge_index = {entry["edge_id"]: entry for entry in state_list}
        self._last_date = date_str
        self._last_time_slot = time_slot
        self._last_refreshed_utc = datetime.now(timezone.utc).isoformat()

        # Determine prediction source for provenance
        has_model = any(
            m is not None for m in [congestion_model, travel_time_model, delay_risk_model]
        )
        self._prediction_source = "SYNTHETIC_MODEL_OUTPUT" if has_model else "FALLBACK"

        logger.info(
            "NetworkStateService: indexed %d edges (prediction_source=%s).",
            len(self._edge_index),
            self._prediction_source,
        )

    def get_edge_state(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """Return the state dict for a single edge (merged with active disruption overlay)."""
        base = self._edge_index.get(edge_id)
        if base is None:
            return None
        over = self._overlay_dict.get(edge_id)
        if over is None:
            return base
        merged = dict(base)
        merged.update(over)
        return merged

    @property
    def edge_index(self) -> Dict[str, Dict[str, Any]]:
        """Full edge_id → state dict index (merged with active disruption overlay)."""
        if not self._overlay_dict:
            return self._edge_index
        res = {}
        for eid, base in self._edge_index.items():
            over = self._overlay_dict.get(eid)
            if over:
                merged = dict(base)
                merged.update(over)
                res[eid] = merged
            else:
                res[eid] = base
        return res

    @property
    def is_ready(self) -> bool:
        """True if at least one refresh() has completed."""
        return bool(self._edge_index)

    @property
    def last_refreshed_utc(self) -> Optional[str]:
        """ISO-8601 UTC timestamp of last successful refresh."""
        return self._last_refreshed_utc

    @property
    def last_date(self) -> Optional[str]:
        return self._last_date

    @property
    def last_time_slot(self) -> Optional[int]:
        return self._last_time_slot

    @property
    def prediction_source(self) -> str:
        if self._overlay_dict:
            return "SIMULATED_SCENARIO"
        return self._prediction_source

    def provenance(self) -> Dict[str, str]:
        """Return provenance metadata suitable for embedding in API responses."""
        return {
            "topology": "STATIC_TOPOLOGY_REAL_SOURCE_NETWORK",
            "demand": "SYNTHETIC",
            "prediction": self.prediction_source,
            "scenario": "SIMULATED_SCENARIO" if self._overlay_dict else "NONE",
            "route": "DERIVED",
            "network_state_date": self._last_date or "UNKNOWN",
            "network_state_time_slot": (
                str(self._last_time_slot) if self._last_time_slot is not None else "UNKNOWN"
            ),
            "network_state_refreshed_utc": self._last_refreshed_utc or "NEVER",
        }


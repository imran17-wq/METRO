"""
Route data model for Namma Pulse Phase 1 routing engine.

RouteResult is the single canonical output type for all routing algorithms.
All fields are type-annotated.  Future phases will extend this (e.g.,
adding congestion_score or reliability_band) without changing the existing
field contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RouteSegment:
    """
    A contiguous sequence of stations on a single metro line.

    One RouteResult may contain multiple segments when a route crosses
    interchange stations (e.g., Purple → Green at Majestic).
    """
    line: str
    station_ids: List[str]
    station_names: List[str]
    segment_time_min: float  # approximate; NA source → fallback used

    def __len__(self) -> int:
        return len(self.station_ids)


@dataclass
class RouteResult:
    """
    Canonical output of a routing query.

    Design notes
    ------------
    - `total_distance_km` is None because Phase 0 source data does not
      contain per-segment distances.  It will be populated in a later phase
      once distances are sourced from BMRCL survey data.
    - `total_time_min` uses APPROXIMATE fallback weights (see dijkstra_router.py).
    - `algorithm` distinguishes Dijkstra vs A* for comparison purposes.
    """

    # Origin / destination
    origin: str                     # Human-readable name
    destination: str                # Human-readable name
    origin_id: str                  # Graph node ID (e.g., "PL01")
    destination_id: str             # Graph node ID (e.g., "GL32")

    # Path
    station_ids: List[str]          # Ordered node IDs (interchange nodes appear once)
    station_names: List[str]        # Ordered human-readable names
    segments: List[RouteSegment]    # Grouped by line

    # Summary
    total_time_min: float           # APPROXIMATE (see notes field)
    total_distance_km: Optional[float]  # None — not available from source data
    interchange_count: int
    interchange_stations: List[str] # Physical station names where line changes
    hop_count: int                  # Number of stations − 1
    lines: List[str]                # Unique lines used, in traversal order

    # Metadata
    algorithm: str                  # "dijkstra", "astar", or "dynamic"
    notes: List[str]                # Provenance / approximation notices

    # Phase 4 Dynamic Routing Extensions (Optional for backward compatibility)
    route_profile: Optional[str] = None
    total_dynamic_cost: Optional[float] = None
    predicted_travel_time: Optional[float] = None
    predicted_congestion: Optional[float] = None
    delay_risk: Optional[float] = None
    reliability_score: Optional[float] = None
    transfer_count: Optional[int] = None
    score_breakdown: Optional[dict] = None
    recommendation_reason: Optional[str] = None
    prediction_source: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialise to a plain dict for JSON responses."""
        res = {
            "origin": self.origin,
            "destination": self.destination,
            "origin_id": self.origin_id,
            "destination_id": self.destination_id,
            "station_ids": self.station_ids,
            "station_names": self.station_names,
            "segments": [
                {
                    "line": s.line,
                    "station_ids": s.station_ids,
                    "station_names": s.station_names,
                    "segment_time_min": s.segment_time_min,
                }
                for s in self.segments
            ],
            "total_time_min": self.total_time_min,
            "total_distance_km": self.total_distance_km,
            "interchange_count": self.interchange_count,
            "interchange_stations": self.interchange_stations,
            "hop_count": self.hop_count,
            "lines": self.lines,
            "algorithm": self.algorithm,
            "notes": self.notes,
        }

        # Phase 4 dynamic fields
        if self.route_profile is not None:
            res["route_profile"] = self.route_profile
        if self.total_dynamic_cost is not None:
            res["total_dynamic_cost"] = self.total_dynamic_cost
        if self.predicted_travel_time is not None:
            res["predicted_travel_time"] = self.predicted_travel_time
        if self.predicted_congestion is not None:
            res["predicted_congestion"] = self.predicted_congestion
        if self.delay_risk is not None:
            res["delay_risk"] = self.delay_risk
        if self.reliability_score is not None:
            res["reliability_score"] = self.reliability_score
        if self.transfer_count is not None:
            res["transfer_count"] = self.transfer_count
        if self.score_breakdown is not None:
            res["score_breakdown"] = self.score_breakdown
        if self.recommendation_reason is not None:
            res["recommendation_reason"] = self.recommendation_reason
        if self.prediction_source is not None:
            res["prediction_source"] = self.prediction_source

        return res


@dataclass
class DynamicRouteResult:
    """
    Container for Phase 4 dynamic routing result with recommended route,
    alternatives, profile metadata, and provenance.
    """
    recommended: RouteResult
    alternatives: List[RouteResult]
    profile: str
    network_state_timestamp: str
    model_versions: dict
    data_provenance: dict

    def to_dict(self) -> dict:
        return {
            "recommended": self.recommended.to_dict(),
            "alternatives": [alt.to_dict() for alt in self.alternatives],
            "profile": self.profile,
            "network_state_timestamp": self.network_state_timestamp,
            "model_versions": self.model_versions,
            "data_provenance": self.data_provenance,
        }


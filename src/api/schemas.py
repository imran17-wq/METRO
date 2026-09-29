"""
Pydantic schemas for the Namma Pulse REST API.

All response models have explicit field types and docstrings so that the
auto-generated OpenAPI spec is self-explanatory.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Station schemas
# ---------------------------------------------------------------------------

class StationOut(BaseModel):
    """A unique physical metro station (interchange stations appear once)."""
    name: str = Field(..., description="Canonical station name from source topology")
    lines: List[str] = Field(..., description="Lines serving this station")
    is_interchange: bool = Field(..., description="True if two or more lines share this stop")
    representative_id: str = Field(..., description="One graph node ID for this station")


class StationsResponse(BaseModel):
    """List of all operational stations."""
    count: int
    stations: List[StationOut]


# ---------------------------------------------------------------------------
# Network topology schema
# ---------------------------------------------------------------------------

class StationTopology(BaseModel):
    id: str
    name: str
    line: str
    sequence: int
    is_interchange: bool
    interchange_lines: List[str]
    x: float = Field(..., description="Schematic SVG x-coordinate")
    y: float = Field(..., description="Schematic SVG y-coordinate")


class EdgeTopology(BaseModel):
    from_id: str
    to_id: str
    line: str
    edge_type: str  # "segment" or "transfer"
    edge_id: str


class InterchangeLocation(BaseModel):
    name: str
    station_ids: List[str]
    x: float
    y: float


class NetworkResponse(BaseModel):
    """Full network topology for MetroMap rendering."""
    stations: List[StationTopology]
    edges: List[EdgeTopology]
    lines: List[str]
    interchange_locations: List[InterchangeLocation]


# ---------------------------------------------------------------------------
# Route schemas
# ---------------------------------------------------------------------------

class RouteSegmentOut(BaseModel):
    line: str
    station_ids: List[str]
    station_names: List[str]
    segment_time_min: float


class ScoreBreakdown(BaseModel):
    travel_time: float
    congestion_penalty: float
    delay_penalty: float
    transfer_penalty: float
    total: float


class RouteResponse(BaseModel):
    """
    Result of a routing query.
    """
    origin: str
    destination: str
    origin_id: str
    destination_id: str
    algorithm: str
    station_ids: List[str]
    station_names: List[str]
    segments: List[RouteSegmentOut]
    total_time_min: float
    total_distance_km: Optional[float]
    interchange_count: int
    interchange_stations: List[str]
    hop_count: int
    lines: List[str]
    notes: List[str]

    # Phase 4 dynamic routing extensions
    route_profile: Optional[str] = None
    total_dynamic_cost: Optional[float] = None
    predicted_travel_time: Optional[float] = None
    predicted_congestion: Optional[float] = None
    delay_risk: Optional[float] = None
    reliability_score: Optional[float] = None
    transfer_count: Optional[int] = None
    score_breakdown: Optional[ScoreBreakdown] = None
    recommendation_reason: Optional[str] = None
    prediction_source: Optional[str] = None


class DynamicRouteCompareResponse(BaseModel):
    """
    Phase 4 candidate route comparison response.
    Returns recommended route, non-dominated alternative routes, profile,
    network state timestamp, and data provenance.
    """
    recommended: RouteResponse
    alternatives: List[RouteResponse]
    profile: str
    network_state_timestamp: str
    model_versions: Dict[str, Any]
    data_provenance: Dict[str, Any]



# ---------------------------------------------------------------------------
# Prediction & ML schemas
# ---------------------------------------------------------------------------

class CongestionPrediction(BaseModel):
    edge_id: str
    line: str
    date: str
    time_slot: int
    slot_start: str
    predicted_congestion_pct: Optional[float]
    congestion_band: Optional[str]
    model_version: str
    data_provenance: str = "SYNTHETIC MODEL OUTPUT"


class TravelTimePrediction(BaseModel):
    edge_id: str
    line: str
    date: str
    time_slot: int
    slot_start: str
    scheduled_time_min: float
    predicted_travel_time_min: Optional[float]
    model_version: str
    data_provenance: str = "SYNTHETIC MODEL OUTPUT"


class EdgeNetworkState(BaseModel):
    edge_id: str
    from_id: str
    to_id: str
    line: str
    line_status: str
    active: bool
    scheduled_time_min: float
    predicted_travel_time_min: Optional[float]
    predicted_congestion_pct: Optional[float]
    congestion_band: Optional[str]
    delay_risk_prob: Optional[float]
    data_provenance: str


class NetworkStateResponse(BaseModel):
    date: str
    time_slot: int
    slot_start: str
    edge_count: int
    edges: List[EdgeNetworkState]


class ModelPerformanceResponse(BaseModel):
    congestion: Dict[str, Any]
    travel_time: Dict[str, Any]
    delay_risk: Dict[str, Any]


# ---------------------------------------------------------------------------
# Phase 5 Simulation & Resilience schemas
# ---------------------------------------------------------------------------

class DisruptionOut(BaseModel):
    id: str
    name: str
    type: str
    severity: str
    description: str
    start_time: str
    end_time: str
    affected_lines: List[str]
    affected_stations: List[str]
    affected_edges: List[str]
    active: bool
    delay_multiplier: float
    congestion_multiplier: float
    demand_multiplier: float


class ScenarioOut(BaseModel):
    id: str
    name: str
    type: str
    target: str
    severity: str
    duration_min: int
    description: str
    active: bool
    provenance_label: str = "SIMULATED SCENARIO"
    disruptions: List[DisruptionOut]
    active_lines: Optional[List[str]] = None
    headway_sec: Optional[int] = None
    demand_multiplier: Optional[float] = 1.0


class CustomScenarioRequest(BaseModel):
    id: Optional[str] = Field(None, description="Custom scenario ID")
    name: str = Field(..., description="Custom scenario name")
    type: Optional[str] = Field("CONGESTION_SURGE", description="Disruption type")
    target: Optional[str] = Field("Custom Target", description="Target description")
    severity: Optional[str] = Field("MEDIUM", description="Severity level")
    duration_min: Optional[int] = Field(60, description="Duration in minutes")
    description: Optional[str] = Field("Custom user defined scenario", description="Scenario description")
    active_lines: List[str] = Field(..., description="List of active lines e.g. ['Purple', 'Green', 'Yellow', 'Pink', 'Blue']")
    headway_sec: Optional[int] = Field(360, description="Train service headway in seconds")
    demand_multiplier: Optional[float] = Field(1.0, description="Demand multiplier")
    disruptions: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Optional custom disruptions")


class SimulationStateResponse(BaseModel):
    active_scenario: Optional[ScenarioOut]
    is_active: bool
    affected_edge_count: int
    provenance: str = "SIMULATED SCENARIO"


class RouteImpactResponse(BaseModel):
    origin: str
    destination: str
    profile: str
    scenario_id: Optional[str]
    unreachable: bool
    error_detail: Optional[str] = None
    baseline_route: Optional[Dict[str, Any]]
    disrupted_route: Optional[Dict[str, Any]]
    baseline_time_min: Optional[float] = None
    disrupted_time_min: Optional[float] = None
    travel_time_change_min: Optional[float] = None
    travel_time_change_pct: Optional[float] = None
    baseline_congestion_pct: Optional[float] = None
    disrupted_congestion_pct: Optional[float] = None
    congestion_change_pct: Optional[float] = None
    baseline_transfers: Optional[int] = None
    disrupted_transfers: Optional[int] = None
    transfer_change: Optional[int] = None
    route_changed: bool
    recommendation: str
    data_provenance: Dict[str, str]


class ResilienceMetricsResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    sample_size: int
    seed: int
    route_availability_pct: float
    avg_travel_time_impact_pct: float
    unreachable_od_rate_pct: float
    rerouting_success_rate_pct: float
    avg_transfer_change: float
    resilience_score: float
    reachable_count: int
    unreachable_count: int
    disrupted_count: int
    rerouted_count: int
    cascading_congestion_edges: List[Dict[str, Any]]
    data_provenance: Dict[str, str]


# ---------------------------------------------------------------------------
# Operations Control Center (OCC) schemas (Phase 6.1)
# ---------------------------------------------------------------------------

class TrainOut(BaseModel):
    train_id: str
    line: str
    direction: str
    origin_station: str
    destination_station: str
    current_station_idx: int
    current_station: str
    next_station: str
    current_segment: str
    current_section_id: Optional[str] = None
    next_section_id: Optional[str] = None
    leader_train_id: Optional[str] = None
    following_train_id: Optional[str] = None
    wait_reason: Optional[str] = None
    progress_pct: float
    scheduled_departure: str
    scheduled_arrival_next: str
    expected_arrival_next: str
    actual_headway_sec: Optional[int] = 360
    headway_deviation_sec: Optional[int] = 0
    bunching_flag: Optional[bool] = False
    delay_seconds: int
    delay_formatted: str
    status: str
    is_held: bool
    hold_reason: Optional[str] = None
    is_completed: bool
    data_provenance: str = "SIMULATED OPERATIONS"
    delay_provenance: str = "DERIVED SIMULATION OUTPUT"


class ClockOut(BaseModel):
    current_time_sec: int
    formatted_time: str
    is_running: bool
    speed_multiplier: float
    data_provenance: str = "SIMULATED OPERATIONS"


class AlertOut(BaseModel):
    id: str
    timestamp: str
    severity: str
    priority: Optional[int] = 1
    icon: str
    title: str
    message: str
    source: str = "SIMULATED OPERATIONS"


class OperationsKPIsOut(BaseModel):
    total_trains: int
    on_time: int
    delayed: int
    stopped: int
    bunching_trains: Optional[int] = 0
    active_incidents: int
    high_congestion_areas: int


class OperationsStateResponse(BaseModel):
    clock: ClockOut
    network_status: str
    network_status_badge: str
    active_scenario: Optional[Dict[str, Any]] = None
    kpis: OperationsKPIsOut
    trains: List[TrainOut]
    sections: Optional[List[Dict[str, Any]]] = None
    headways: Optional[List[Dict[str, Any]]] = None
    alerts: List[AlertOut]
    data_provenance: str = "SIMULATED OPERATIONS"


class StationInspectionResponse(BaseModel):
    station_name: str
    incoming_trains: List[Dict[str, Any]]
    outgoing_trains: List[Dict[str, Any]]
    platform_demand: str
    current_congestion_pct: float
    predicted_congestion_15min_pct: float
    next_train_eta: str
    active_incidents: List[str]
    data_provenance: str = "SYNTHETIC & SYNTHETIC MODEL OUTPUT"


class SpeedRequest(BaseModel):
    speed: float = Field(..., description="Simulation speed multiplier (1.0, 2.0, 5.0, 10.0)")


class TickRequest(BaseModel):
    seconds: float = Field(1.0, description="Elapsed simulation seconds to advance")


# ---------------------------------------------------------------------------
# Error schema
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int


# ---------------------------------------------------------------------------
# Health schema
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    graph_nodes: int
    graph_edges: int
    phase: str



"""
Namma Pulse — FastAPI application entry point.
Single Canonical 5-Line Graph Architecture + Phase 3 ML Prediction Layer.
"""
from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import LOG_LEVEL, LOG_FORMAT, PROJECT_ROOT
from src.routing.routing_service import (
    RoutingService,
    StationNotFoundError,
    SameStationError,
    InactiveLineError,
    NoRouteError,
)
from src.api.schemas import (
    StationsResponse,
    StationOut,
    NetworkResponse,
    StationTopology,
    EdgeTopology,
    InterchangeLocation,
    RouteResponse,
    RouteSegmentOut,
    ScoreBreakdown,
    DynamicRouteCompareResponse,
    HealthResponse,
    CongestionPrediction,
    TravelTimePrediction,
    EdgeNetworkState,
    NetworkStateResponse,
    ModelPerformanceResponse,
    ScenarioOut,
    DisruptionOut,
    CustomScenarioRequest,
    SimulationStateResponse,
    RouteImpactResponse,
    ResilienceMetricsResponse,
)
from src.ml.models.congestion_model import CongestionModel
from src.ml.models.travel_time_model import TravelTimeModel
from src.ml.models.delay_risk_model import DelayRiskModel
from src.ml.network_state import NetworkStateBuilder
from src.routing.network_state_service import NetworkStateService
from src.simulation import (
    Scenario,
    Disruption,
    DisruptionType,
    Severity,
    ScenarioEngine,
    ImpactAnalyzer,
    ResilienceEvaluator,
    get_scenario,
    list_scenarios,
)
from src.config.simulation_settings import (
    DEFAULT_OD_SAMPLE_SIZE,
    MAX_OD_SAMPLE_SIZE,
    RANDOM_SEED,
)

logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton services
# ---------------------------------------------------------------------------

routing_service = RoutingService()
scenario_engine = ScenarioEngine()
network_state_builder: Optional[NetworkStateBuilder] = None
network_state_service: Optional[NetworkStateService] = None
congestion_model: Optional[CongestionModel] = None
travel_time_model: Optional[TravelTimeModel] = None
delay_risk_model: Optional[DelayRiskModel] = None

congestion_model: Optional[CongestionModel] = None
travel_time_model: Optional[TravelTimeModel] = None
delay_risk_model: Optional[DelayRiskModel] = None

# Current simulation timestamp defaults
SIMULATION_DEFAULT_DATE = "2024-01-08"
SIMULATION_DEFAULT_TIME_SLOT = 36


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the single canonical 5-line graph and load ML models on startup."""
    global network_state_builder, network_state_service, congestion_model, travel_time_model, delay_risk_model
    logger.info("Building canonical 5-line metro graph on startup...")
    routing_service.initialise()
    network_state_builder = NetworkStateBuilder(routing_service._graph)
    network_state_service = NetworkStateService(network_state_builder)

    # Load ML models if artifacts exist
    try:
        c_model = CongestionModel()
        c_model.load()
        congestion_model = c_model
        logger.info("CongestionModel loaded successfully.")
    except Exception as e:
        logger.warning("Could not load CongestionModel: %s", e)

    try:
        t_model = TravelTimeModel()
        t_model.load()
        travel_time_model = t_model
        logger.info("TravelTimeModel loaded successfully.")
    except Exception as e:
        logger.warning("Could not load TravelTimeModel: %s", e)

    try:
        d_model = DelayRiskModel()
        d_model.load()
        delay_risk_model = d_model
        logger.info("DelayRiskModel loaded successfully.")
    except Exception as e:
        logger.warning("Could not load DelayRiskModel: %s", e)

    # Initial state refresh with default simulation timestamp
    network_state_service.refresh(
        date_str=SIMULATION_DEFAULT_DATE,
        time_slot=SIMULATION_DEFAULT_TIME_SLOT,
        congestion_model=congestion_model,
        travel_time_model=travel_time_model,
        delay_risk_model=delay_risk_model,
    )

    logger.info("Graph and ML services ready. API accepting requests.")
    yield
    logger.info("Shutting down Namma Pulse API.")


def _ensure_network_state(
    date: Optional[str] = None,
    time_slot: Optional[int] = None,
) -> NetworkStateService:
    global network_state_builder, network_state_service
    if routing_service._graph is None:
        routing_service.initialise()
    if network_state_builder is None:
        network_state_builder = NetworkStateBuilder(routing_service._graph)
    if network_state_service is None:
        network_state_service = NetworkStateService(network_state_builder)

    req_date = date or SIMULATION_DEFAULT_DATE
    req_slot = time_slot if time_slot is not None else SIMULATION_DEFAULT_TIME_SLOT

    if (
        not network_state_service.is_ready
        or network_state_service.last_date != req_date
        or network_state_service.last_time_slot != req_slot
    ):
        network_state_service.refresh(
            date_str=req_date,
            time_slot=req_slot,
            congestion_model=congestion_model,
            travel_time_model=travel_time_model,
            delay_risk_model=delay_risk_model,
            active_lines=routing_service.get_active_lines(),
        )

    return network_state_service



# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Namma Pulse API",
    description="Bengaluru Metro Intelligent Route & Congestion Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Existing System & Routing Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["System"])
def root():
    return {
        "status": "online",
        "system": "Namma Pulse — Simulated Bengaluru Metro Operations Control Center API",
        "docs": "/docs",
        "health": "/api/health",
        "operations_state": "/api/operations/state",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health():
    if routing_service._graph is None:
        routing_service.initialise()
    g = routing_service._graph
    return HealthResponse(
        status="ok",
        graph_nodes=g.number_of_nodes(),
        graph_edges=g.number_of_edges(),
        phase="6.1",
    )





@app.get("/api/stations", response_model=StationsResponse, tags=["Stations"])
def get_stations(
    q: Optional[str] = Query(default=None, description="Optional search query"),
):
    if q:
        raw = routing_service.search_stations(q)
    else:
        raw = routing_service.all_stations()

    stations = [
        StationOut(
            name=s["name"],
            lines=s["lines"],
            is_interchange=s["is_interchange"],
            representative_id=s["representative_id"],
        )
        for s in raw
    ]
    return StationsResponse(count=len(stations), stations=stations)


@app.get("/api/network", response_model=NetworkResponse, tags=["Network"])
def get_network():
    topology = routing_service.network_topology()

    stations = [StationTopology(**s) for s in topology["stations"]]
    edges = [EdgeTopology(**e) for e in topology["edges"]]
    interchanges = [InterchangeLocation(**i) for i in topology["interchange_locations"]]

    return NetworkResponse(
        stations=stations,
        edges=edges,
        lines=topology["lines"],
        interchange_locations=interchanges,
    )


def _convert_route_to_schema(rr) -> RouteResponse:
    segments = [
        RouteSegmentOut(
            line=s.line,
            station_ids=s.station_ids,
            station_names=s.station_names,
            segment_time_min=s.segment_time_min,
        )
        for s in rr.segments
    ]
    breakdown = (
        ScoreBreakdown(**rr.score_breakdown) if rr.score_breakdown else None
    )
    return RouteResponse(
        origin=rr.origin,
        destination=rr.destination,
        origin_id=rr.origin_id,
        destination_id=rr.destination_id,
        algorithm=rr.algorithm,
        station_ids=rr.station_ids,
        station_names=rr.station_names,
        segments=segments,
        total_time_min=rr.total_time_min,
        total_distance_km=rr.total_distance_km,
        interchange_count=rr.interchange_count,
        interchange_stations=rr.interchange_stations,
        hop_count=rr.hop_count,
        lines=rr.lines,
        notes=rr.notes,
        route_profile=rr.route_profile,
        total_dynamic_cost=rr.total_dynamic_cost,
        predicted_travel_time=rr.predicted_travel_time,
        predicted_congestion=rr.predicted_congestion,
        delay_risk=rr.delay_risk,
        reliability_score=rr.reliability_score,
        transfer_count=rr.transfer_count,
        score_breakdown=breakdown,
        recommendation_reason=rr.recommendation_reason,
        prediction_source=rr.prediction_source,
    )


@app.get("/api/route", response_model=RouteResponse, tags=["Routing"])
def get_route(
    origin: str = Query(..., description="Origin station name"),
    destination: str = Query(..., description="Destination station name"),
    algorithm: str = Query(default="dijkstra", description="Routing algorithm"),
    profile: Optional[str] = Query(default=None, description="Optional Phase 4 route profile"),
    date: Optional[str] = Query(default=None, description="Optional YYYY-MM-DD date for dynamic state"),
    time_slot: Optional[int] = Query(default=None, description="Optional time slot index (24..89)"),
):
    try:
        if profile is not None:
            # Dynamic Phase 4 route query
            state_svc = _ensure_network_state(date, time_slot)
            dyn_res = routing_service.dynamic_route(origin, destination, state_svc, profile=profile)
            return _convert_route_to_schema(dyn_res.recommended)

        # Baseline Phase 1 Dijkstra / A* route query
        result = routing_service.route(origin, destination, algorithm)
        return _convert_route_to_schema(result)

    except StationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InactiveLineError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except NoRouteError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SameStationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/routes/compare", response_model=DynamicRouteCompareResponse, tags=["Routing"])
def compare_routes(
    origin: str = Query(..., description="Origin station name"),
    destination: str = Query(..., description="Destination station name"),
    profile: str = Query(default="BALANCED", description="Route profile"),
    date: Optional[str] = Query(default=None, description="Optional YYYY-MM-DD date"),
    time_slot: Optional[int] = Query(default=None, description="Optional time slot index"),
):
    try:
        state_svc = _ensure_network_state(date, time_slot)
        dyn_res = routing_service.dynamic_route(
            origin, destination, state_svc, profile=profile, k=5
        )

        rec_out = _convert_route_to_schema(dyn_res.recommended)
        alts_out = [_convert_route_to_schema(alt) for alt in dyn_res.alternatives]

        return DynamicRouteCompareResponse(
            recommended=rec_out,
            alternatives=alts_out,
            profile=dyn_res.profile,
            network_state_timestamp=dyn_res.network_state_timestamp,
            model_versions=dyn_res.model_versions,
            data_provenance=dyn_res.data_provenance,
        )

    except StationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InactiveLineError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except NoRouteError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SameStationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))



# ---------------------------------------------------------------------------
# Phase 3 ML Prediction Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/predictions/congestion", response_model=List[CongestionPrediction], tags=["ML Predictions"])
def get_congestion_predictions(
    date: str = Query(default="2024-01-08", description="Date YYYY-MM-DD"),
    time_slot: int = Query(default=36, ge=24, le=89, description="15-min slot index (24=06:00, 36=09:00, 89=22:15)"),
    line: Optional[str] = Query(default=None, description="Optional line filter"),
):
    if network_state_builder is None:
        raise HTTPException(status_code=503, detail="Network state builder not initialized.")

    states = network_state_builder.build_state(
        date_str=date,
        time_slot=time_slot,
        congestion_model=congestion_model,
        travel_time_model=travel_time_model,
        delay_risk_model=delay_risk_model,
    )

    preds = []
    slot_start = f"{time_slot * 15 // 60:02d}:{time_slot * 15 % 60:02d}"
    for s in states:
        if line and s["line"].lower() != line.lower():
            continue
        preds.append(
            CongestionPrediction(
                edge_id=s["edge_id"],
                line=s["line"],
                date=date,
                time_slot=time_slot,
                slot_start=slot_start,
                predicted_congestion_pct=s["predicted_congestion_pct"],
                congestion_band=s["congestion_band"],
                model_version=congestion_model.metrics.get("model_version", "1.0.0") if congestion_model else "1.0.0",
                data_provenance=s["data_provenance"],
            )
        )
    return preds


@app.get("/api/predictions/network-state", response_model=NetworkStateResponse, tags=["ML Predictions"])
def get_network_state(
    date: str = Query(default="2024-01-08", description="Date YYYY-MM-DD"),
    time_slot: int = Query(default=36, ge=24, le=89, description="15-min slot index"),
):
    if network_state_builder is None:
        raise HTTPException(status_code=503, detail="Network state builder not initialized.")

    states = network_state_builder.build_state(
        date_str=date,
        time_slot=time_slot,
        congestion_model=congestion_model,
        travel_time_model=travel_time_model,
        delay_risk_model=delay_risk_model,
    )

    slot_start = f"{time_slot * 15 // 60:02d}:{time_slot * 15 % 60:02d}"
    edges = [EdgeNetworkState(**s) for s in states]

    return NetworkStateResponse(
        date=date,
        time_slot=time_slot,
        slot_start=slot_start,
        edge_count=len(edges),
        edges=edges,
    )


@app.get("/api/predictions/model-performance", response_model=ModelPerformanceResponse, tags=["ML Predictions"])
def get_model_performance():
    c_meta = congestion_model.metrics if congestion_model else {"status": "not_loaded"}
    t_meta = travel_time_model.metrics if travel_time_model else {"status": "not_loaded"}
    d_meta = delay_risk_model.metrics if delay_risk_model else {"status": "not_loaded"}

    # Load SHAP feature importance if available
    shap_file = PROJECT_ROOT / "models" / "congestion" / "shap_importance.json"
    if shap_file.exists():
        with open(shap_file) as f:
            c_meta = dict(c_meta)
            c_meta["shap_importance"] = json.load(f)

    return ModelPerformanceResponse(
        congestion=c_meta,
        travel_time=t_meta,
        delay_risk=d_meta,
    )


# ---------------------------------------------------------------------------
# Phase 5 Disruption Simulation & Network Resilience Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/simulation/scenarios", response_model=List[ScenarioOut], tags=["Simulation"])
def get_simulation_scenarios():
    """List all available pre-packaged scenarios in the Scenario Library."""
    return [ScenarioOut(**sc.to_dict()) for sc in list_scenarios()]


@app.get("/api/simulation/scenarios/{scenario_id}", response_model=ScenarioOut, tags=["Simulation"])
def get_simulation_scenario(scenario_id: str):
    """Retrieve details for a specific scenario."""
    sc = get_scenario(scenario_id)
    if sc is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    return ScenarioOut(**sc.to_dict())


@app.post("/api/simulation/scenarios/custom/activate", tags=["Simulation"])
def activate_custom_scenario(req: CustomScenarioRequest):
    """Activate a custom scenario dynamically built by the user."""
    if not req.active_lines or len(req.active_lines) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one metro line must remain active in the simulation."
        )

    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()

    disruptions = []
    if req.disruptions:
        for idx, d_data in enumerate(req.disruptions):
            disruptions.append(
                Disruption(
                    id=d_data.get("id", f"custom_d_{idx}"),
                    name=d_data.get("name", "Custom Disruption"),
                    type=DisruptionType(d_data.get("type", "CONGESTION_SURGE")),
                    severity=Severity(d_data.get("severity", "MEDIUM")),
                    description=d_data.get("description", "Custom disruption overlay"),
                    affected_lines=d_data.get("affected_lines", []),
                    affected_stations=d_data.get("affected_stations", []),
                    affected_edges=d_data.get("affected_edges", []),
                    delay_multiplier=float(d_data.get("delay_multiplier", 1.0)),
                    congestion_multiplier=float(d_data.get("congestion_multiplier", 1.0)),
                    demand_multiplier=float(d_data.get("demand_multiplier", 1.0)),
                )
            )

    sc = Scenario(
        id=req.id or f"custom_{hash(req.name)}",
        name=req.name,
        type=DisruptionType(req.type or "CONGESTION_SURGE"),
        target=req.target or "Custom Target",
        severity=Severity(req.severity or "MEDIUM"),
        duration_min=req.duration_min or 60,
        description=req.description or "Custom user-defined scenario",
        disruptions=disruptions,
        active_lines=req.active_lines,
        headway_sec=req.headway_sec or 360,
        demand_multiplier=req.demand_multiplier if req.demand_multiplier is not None else 1.0,
    )

    try:
        res = scenario_engine.activate_scenario(
            scenario_id_or_obj=sc,
            network_state_service=state_svc,
            routing_service=routing_service,
            operations_engine=ops_eng,
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/simulation/scenarios/{scenario_id}/activate", tags=["Simulation"])
def activate_scenario(scenario_id: str):
    """Activate a scenario overlay onto the network state with backend propagation."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()
    try:
        res = scenario_engine.activate_scenario(
            scenario_id_or_obj=scenario_id,
            network_state_service=state_svc,
            routing_service=routing_service,
            operations_engine=ops_eng,
        )
        return res
    except ValueError as exc:
        if "At least one metro line" in str(exc):
            raise HTTPException(status_code=400, detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/simulation/scenarios/{scenario_id}/deactivate", tags=["Simulation"])
def deactivate_scenario(scenario_id: str):
    """Deactivate active scenario and restore exact base network state."""
    state_svc = _ensure_network_state()
    ops_eng = _ensure_operations_engine()
    res = scenario_engine.deactivate_scenario(
        network_state_service=state_svc,
        routing_service=routing_service,
        operations_engine=ops_eng,
    )
    return res


@app.get("/api/simulation/state", response_model=SimulationStateResponse, tags=["Simulation"])
def get_simulation_state():
    """Get current active simulation state and active scenario metadata."""
    state = scenario_engine.get_simulation_state()
    sc_out = ScenarioOut(**state["active_scenario"]) if state["active_scenario"] else None
    return SimulationStateResponse(
        active_scenario=sc_out,
        is_active=state["is_active"],
        affected_edge_count=state["affected_edge_count"],
        provenance=state["provenance"],
    )


@app.get("/api/simulation/impact", response_model=RouteImpactResponse, tags=["Simulation"])
def get_route_impact(
    origin: str = Query(..., description="Origin station name"),
    destination: str = Query(..., description="Destination station name"),
    profile: str = Query(default="BALANCED", description="Route profile"),
    scenario_id: Optional[str] = Query(default=None, description="Optional scenario ID to simulate"),
):
    """Compare baseline (un-disrupted) vs disrupted route for a single OD pair."""
    state_svc = _ensure_network_state()

    # If scenario_id is passed and not active, temporarily activate for comparison
    currently_active = scenario_engine.active_scenario
    temp_activation = False

    if scenario_id and (currently_active is None or currently_active.id != scenario_id):
        scenario_engine.activate_scenario(scenario_id, state_svc)
        temp_activation = True
    try:
        res = ImpactAnalyzer.compare_route_impact(
            origin, destination, routing_service, state_svc, profile=profile, scenario_id=scenario_id
        )
        return RouteImpactResponse(**res)
    finally:
        if temp_activation:
            scenario_engine.deactivate_scenario(state_svc)



@app.get("/api/simulation/resilience", response_model=ResilienceMetricsResponse, tags=["Simulation"])

def get_network_resilience(
    scenario_id: Optional[str] = Query(default=None, description="Scenario ID to evaluate"),
    sample_size: int = Query(default=DEFAULT_OD_SAMPLE_SIZE, ge=10, le=MAX_OD_SAMPLE_SIZE, description="Representative OD sample size"),
    profile: str = Query(default="BALANCED", description="Route profile"),
):
    """Evaluate network resilience metrics and score across representative OD sample."""
    state_svc = _ensure_network_state()

    sc_target = None
    if scenario_id:
        sc_target = get_scenario(scenario_id)
    elif scenario_engine.active_scenario:
        sc_target = scenario_engine.active_scenario

    if sc_target is None:
        raise HTTPException(status_code=400, detail="No active scenario or scenario_id specified.")

    # Temporarily activate if evaluating non-active scenario
    currently_active = scenario_engine.active_scenario
    temp_activation = False
    if currently_active is None or currently_active.id != sc_target.id:
        scenario_engine.activate_scenario(sc_target.id, state_svc)
        temp_activation = True

    try:
        evaluator = ResilienceEvaluator(routing_service)
        metrics = evaluator.evaluate_resilience(
            state_svc, sc_target, sample_size=sample_size, seed=RANDOM_SEED, profile=profile
        )
        return ResilienceMetricsResponse(**metrics.to_dict())
    finally:
        if temp_activation:
            scenario_engine.deactivate_scenario(state_svc)

from src.graph.metro_graph import get_line_stations
from src.operations import OperationsEngine, NetworkOperationStatus

from src.api.schemas import (
    OperationsStateResponse,
    StationInspectionResponse,
    TrainOut,
    SpeedRequest,
    TickRequest,
)

operations_engine: Optional[OperationsEngine] = None


def _ensure_operations_engine() -> OperationsEngine:
    global operations_engine
    if routing_service._graph is None:
        routing_service.initialise()

    if operations_engine is None:
        stations_by_line: Dict[str, List[str]] = {}
        for line in ["Purple", "Green", "Yellow", "Pink", "Blue"]:
            st_list = get_line_stations(line)
            if st_list:
                stations_by_line[line] = [s.station_name for s in st_list]


        operations_engine = OperationsEngine(
            station_data_by_line=stations_by_line,
            graph=routing_service._graph,
        )

    # Sync with active scenario if present
    if scenario_engine.active_scenario is not None:
        operations_engine.update_disruption_state(
            scenario_engine.active_scenario,
            scenario_engine.affected_edges,
        )
    else:
        operations_engine.update_disruption_state(None, set())


    return operations_engine


# ---------------------------------------------------------------------------
# Operations Control Center (OCC) Endpoints (Phase 6.1)
# ---------------------------------------------------------------------------

@app.get("/api/operations/state", response_model=OperationsStateResponse, tags=["Operations OCC"])
def get_operations_state():
    """Returns complete Operations Control Center state (simulated time, KPIs, trains, alerts)."""
    ops = _ensure_operations_engine()
    return OperationsStateResponse(**ops.get_state())


@app.get("/api/operations/trains", response_model=List[TrainOut], tags=["Operations OCC"])
def get_operations_trains():
    """Returns list of active simulated trains."""
    ops = _ensure_operations_engine()
    state = ops.get_state()
    return [TrainOut(**t) for t in state["trains"]]


@app.get("/api/operations/trains/{train_id}", response_model=TrainOut, tags=["Operations OCC"])
def get_operations_train_by_id(train_id: str):
    """Returns inspection details for a specific train."""
    ops = _ensure_operations_engine()
    for t in ops.trains:
        if t.train_id == train_id:
            return TrainOut(**t.to_dict())
    raise HTTPException(status_code=404, detail=f"Train '{train_id}' not found.")


@app.get("/api/operations/stations/{station_id_or_name}", response_model=StationInspectionResponse, tags=["Operations OCC"])
def get_operations_station_inspection(station_id_or_name: str):
    """Returns OCC station inspection data (incoming/outgoing trains, platform demand, congestion)."""
    ops = _ensure_operations_engine()
    # Resolve station name if node ID was supplied
    st_name = station_id_or_name
    if routing_service._graph and station_id_or_name in routing_service._graph.nodes:
        st_name = routing_service._graph.nodes[station_id_or_name].get("name", station_id_or_name)

    inspection = ops.get_station_inspection(st_name)
    return StationInspectionResponse(**inspection)


@app.post("/api/operations/simulation/start", response_model=OperationsStateResponse, tags=["Operations OCC"])
def start_operations_simulation():
    """Starts simulated operations clock."""
    ops = _ensure_operations_engine()
    ops.clock.play()
    return OperationsStateResponse(**ops.get_state())


@app.post("/api/operations/simulation/pause", response_model=OperationsStateResponse, tags=["Operations OCC"])
def pause_operations_simulation():
    """Pauses simulated operations clock."""
    ops = _ensure_operations_engine()
    ops.clock.pause()
    return OperationsStateResponse(**ops.get_state())


@app.post("/api/operations/simulation/reset", response_model=OperationsStateResponse, tags=["Operations OCC"])
def reset_operations_simulation():
    """Resets simulated operations clock, active scenario, active lines, and train schedules to baseline CURRENT_OPERATIONS."""
    state_svc = _ensure_network_state()
    ops = _ensure_operations_engine()
    scenario_engine.deactivate_scenario(
        network_state_service=state_svc,
        routing_service=routing_service,
        operations_engine=ops,
    )
    ops.clock.reset()
    ops.set_active_lines({"Purple", "Green", "Yellow"}, headway_sec=360)
    return OperationsStateResponse(**ops.get_state())


@app.post("/api/simulation/reset", tags=["Simulation"])
def reset_simulation_state():
    """Full atomic RESET restoring baseline CURRENT_OPERATIONS state."""
    state_svc = _ensure_network_state()
    ops = _ensure_operations_engine()
    res = scenario_engine.deactivate_scenario(
        network_state_service=state_svc,
        routing_service=routing_service,
        operations_engine=ops,
    )
    ops.clock.reset()
    ops.set_active_lines({"Purple", "Green", "Yellow"}, headway_sec=360)
    return {
        "status": "RESET_COMPLETE",
        "active_scenario": "current_operations",
        "active_lines": ["Purple", "Green", "Yellow"],
        "clock": ops.clock.formatted_time(),
        "state_restored": True,
    }


@app.post("/api/operations/simulation/tick", response_model=OperationsStateResponse, tags=["Operations OCC"])
def tick_operations_simulation(req: TickRequest):
    """Advances simulated operations clock by N seconds."""
    ops = _ensure_operations_engine()
    ops.step(req.seconds)
    return OperationsStateResponse(**ops.get_state())


@app.post("/api/operations/simulation/speed", response_model=OperationsStateResponse, tags=["Operations OCC"])
def set_operations_simulation_speed(req: SpeedRequest):
    """Sets simulation speed multiplier (1.0, 2.0, 5.0, 10.0)."""
    ops = _ensure_operations_engine()
    ops.clock.set_speed(req.speed)
    return OperationsStateResponse(**ops.get_state())



@app.post("/api/operations/trains/{train_id}/hold", tags=["Operations OCC"])
def hold_train_endpoint(train_id: str):
    """Simulated operator command: Hold train at current station."""
    ops = _ensure_operations_engine()
    success = ops.hold_train(train_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Train '{train_id}' not found.")
    return {"status": "HELD", "train_id": train_id, "clock": ops.clock.to_dict()}


@app.post("/api/operations/trains/{train_id}/release", tags=["Operations OCC"])
def release_train_endpoint(train_id: str):
    """Simulated operator command: Release held train."""
    ops = _ensure_operations_engine()
    success = ops.release_train(train_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Train '{train_id}' not found.")
    return {"status": "RELEASED", "train_id": train_id, "clock": ops.clock.to_dict()}



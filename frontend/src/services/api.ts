/**
 * api.ts — typed API service layer for Namma Pulse frontend.
 */

import type {
  StationsResponse,
  NetworkResponse,
  RouteResponse,
  CongestionPrediction,
  NetworkStateResponse,
  ModelPerformanceResponse,
  Algorithm,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";


async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, options);


  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const err = await response.json();
      detail = err.detail ?? detail;
    } catch (_) {}
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Core Endpoints
// ---------------------------------------------------------------------------

export const fetchHealth = () =>
  apiFetch<{ status: string; graph_nodes: number; graph_edges: number; phase: string }>(
    "/api/health"
  );

export const fetchStations = (query?: string): Promise<StationsResponse> => {
  const q = query ? `?q=${encodeURIComponent(query)}` : "";
  return apiFetch<StationsResponse>(`/api/stations${q}`);
};

export const fetchNetwork = (): Promise<NetworkResponse> =>
  apiFetch<NetworkResponse>("/api/network");

export const fetchRoute = (
  origin: string,
  destination: string,
  algorithm: Algorithm = "dijkstra"
): Promise<RouteResponse> => {
  const params = new URLSearchParams({
    origin,
    destination,
    algorithm,
  });
  return apiFetch<RouteResponse>(`/api/route?${params}`);
};

export const fetchRouteComparison = (
  origin: string,
  destination: string,
  profile: string = "BALANCED",
  date?: string,
  timeSlot?: number
): Promise<import("../types").DynamicRouteCompareResponse> => {
  const params = new URLSearchParams({
    origin,
    destination,
    profile,
  });
  if (date) params.append("date", date);
  if (timeSlot !== undefined) params.append("time_slot", timeSlot.toString());
  return apiFetch<import("../types").DynamicRouteCompareResponse>(`/api/routes/compare?${params}`);
};


// ---------------------------------------------------------------------------
// Phase 3 Prediction Endpoints
// ---------------------------------------------------------------------------

export const fetchCongestionPredictions = (
  date: string = "2024-01-08",
  timeSlot: number = 36,
  line?: string
): Promise<CongestionPrediction[]> => {
  const params = new URLSearchParams({
    date,
    time_slot: timeSlot.toString(),
  });
  if (line) params.append("line", line);
  return apiFetch<CongestionPrediction[]>(`/api/predictions/congestion?${params}`);
};

export const fetchNetworkState = (
  date: string = "2024-01-08",
  timeSlot: number = 36
): Promise<NetworkStateResponse> => {
  const params = new URLSearchParams({
    date,
    time_slot: timeSlot.toString(),
  });
  return apiFetch<NetworkStateResponse>(`/api/predictions/network-state?${params}`);
};

export const fetchModelPerformance = (): Promise<ModelPerformanceResponse> =>
  apiFetch<ModelPerformanceResponse>("/api/predictions/model-performance");

// ---------------------------------------------------------------------------
// Phase 5 Disruption Simulation & Resilience Endpoints
// ---------------------------------------------------------------------------

export const fetchSimulationScenarios = (): Promise<import("../types").ScenarioOut[]> =>
  apiFetch<import("../types").ScenarioOut[]>("/api/simulation/scenarios");

export const fetchSimulationScenario = (scenarioId: string): Promise<import("../types").ScenarioOut> =>
  apiFetch<import("../types").ScenarioOut>(`/api/simulation/scenarios/${scenarioId}`);

export const activateSimulationScenario = (scenarioId: string): Promise<Record<string, unknown>> =>
  apiFetch<Record<string, unknown>>(`/api/simulation/scenarios/${scenarioId}/activate`, {
    method: "POST",
  });

export const activateCustomScenario = (scenario: {
  name: string;
  active_lines: string[];
  headway_sec?: number;
  demand_multiplier?: number;
  disruptions?: Record<string, unknown>[];
}): Promise<Record<string, unknown>> =>
  apiFetch<Record<string, unknown>>("/api/simulation/scenarios/custom/activate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
  });

export const deactivateSimulationScenario = (scenarioId: string): Promise<Record<string, unknown>> =>
  apiFetch<Record<string, unknown>>(`/api/simulation/scenarios/${scenarioId}/deactivate`, {
    method: "POST",
  });

export const resetSimulation = (): Promise<Record<string, unknown>> =>
  apiFetch<Record<string, unknown>>("/api/simulation/reset", {
    method: "POST",
  });

export const fetchSimulationState = (): Promise<import("../types").SimulationStateResponse> =>
  apiFetch<import("../types").SimulationStateResponse>("/api/simulation/state");

export const fetchRouteImpact = (
  origin: string,
  destination: string,
  profile: string = "BALANCED",
  scenarioId?: string
): Promise<import("../types").RouteImpactResponse> => {
  const params = new URLSearchParams({ origin, destination, profile });
  if (scenarioId) params.append("scenario_id", scenarioId);
  return apiFetch<import("../types").RouteImpactResponse>(`/api/simulation/impact?${params}`);
};

export const fetchNetworkResilience = (
  scenarioId?: string,
  sampleSize: number = 50,
  profile: string = "BALANCED"
): Promise<import("../types").ResilienceMetricsResponse> => {
  const params = new URLSearchParams({ sample_size: sampleSize.toString(), profile });
  if (scenarioId) params.append("scenario_id", scenarioId);
  return apiFetch<import("../types").ResilienceMetricsResponse>(`/api/simulation/resilience?${params}`);
};

// ---------------------------------------------------------------------------
// Phase 6.1 Operations Control Center (OCC) Endpoints
// ---------------------------------------------------------------------------

export const fetchOperationsState = (): Promise<import("../types").OperationsState> =>
  apiFetch<import("../types").OperationsState>("/api/operations/state");

export const startOperationsSimulation = (): Promise<import("../types").OperationsState> =>
  apiFetch<import("../types").OperationsState>("/api/operations/simulation/start", { method: "POST" });

export const pauseOperationsSimulation = (): Promise<import("../types").OperationsState> =>
  apiFetch<import("../types").OperationsState>("/api/operations/simulation/pause", { method: "POST" });

export const resetOperationsSimulation = (): Promise<import("../types").OperationsState> =>
  apiFetch<import("../types").OperationsState>("/api/operations/simulation/reset", { method: "POST" });

export const tickOperationsSimulation = (seconds: number = 1.0): Promise<import("../types").OperationsState> =>
  apiFetch<import("../types").OperationsState>("/api/operations/simulation/tick", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seconds }),
  });

export const setOperationsSimulationSpeed = (speed: number): Promise<import("../types").OperationsState> =>
  apiFetch<import("../types").OperationsState>("/api/operations/simulation/speed", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speed }),
  });


export const holdTrain = (trainId: string): Promise<Record<string, unknown>> =>
  apiFetch<Record<string, unknown>>(`/api/operations/trains/${trainId}/hold`, { method: "POST" });

export const releaseTrain = (trainId: string): Promise<Record<string, unknown>> =>
  apiFetch<Record<string, unknown>>(`/api/operations/trains/${trainId}/release`, { method: "POST" });

export const fetchStationInspection = (stationIdOrName: string): Promise<import("../types").StationInspection> =>
  apiFetch<import("../types").StationInspection>(`/api/operations/stations/${encodeURIComponent(stationIdOrName)}`);



/**
 * useStore.ts — global application state with Zustand.
 */

import { create } from "zustand";
import type {
  NetworkResponse,
  RouteResponse,
  Algorithm,
  RouteProfile,
  DynamicRouteCompareResponse,
  ScenarioOut,
  RouteImpactResponse,
  ResilienceMetricsResponse,
} from "../types";

interface AppState {
  // Network topology
  network: NetworkResponse | null;
  networkLoading: boolean;
  networkError: string | null;
  setNetwork: (n: NetworkResponse) => void;
  setNetworkLoading: (v: boolean) => void;
  setNetworkError: (e: string | null) => void;

  // Route planner inputs
  origin: string;
  destination: string;
  algorithm: Algorithm;
  routeProfile: RouteProfile;
  setOrigin: (s: string) => void;
  setDestination: (s: string) => void;
  setAlgorithm: (a: Algorithm) => void;
  setRouteProfile: (p: RouteProfile) => void;

  // Route result
  routeResult: RouteResponse | null;
  compareResult: DynamicRouteCompareResponse | null;
  selectedAlternative: RouteResponse | null;
  routeLoading: boolean;
  routeError: string | null;
  setRouteResult: (r: RouteResponse | null) => void;
  setCompareResult: (c: DynamicRouteCompareResponse | null) => void;
  setSelectedAlternative: (a: RouteResponse | null) => void;
  setRouteLoading: (v: boolean) => void;
  setRouteError: (e: string | null) => void;

  // Simulation & Resilience state
  activeScenario: ScenarioOut | null;
  impactResult: RouteImpactResponse | null;
  resilienceMetrics: ResilienceMetricsResponse | null;
  simulationLoading: boolean;
  simulationError: string | null;
  setActiveScenario: (s: ScenarioOut | null) => void;
  setImpactResult: (i: RouteImpactResponse | null) => void;
  setResilienceMetrics: (r: ResilienceMetricsResponse | null) => void;
  setSimulationLoading: (v: boolean) => void;
  setSimulationError: (e: string | null) => void;

  // Operations Control Center (Phase 6.1)
  operationsState: import("../types").OperationsState | null;
  selectedTrain: import("../types").Train | null;
  selectedStationInspection: import("../types").StationInspection | null;
  setOperationsState: (s: import("../types").OperationsState | null) => void;
  setSelectedTrain: (t: import("../types").Train | null) => void;
  setSelectedStationInspection: (st: import("../types").StationInspection | null) => void;

  // Map interaction
  hoveredStation: string | null;
  selectedStation: string | null;
  setHoveredStation: (id: string | null) => void;
  setSelectedStation: (id: string | null) => void;
}

export const useStore = create<AppState>((set) => ({
  // Network
  network: null,
  networkLoading: false,
  networkError: null,
  setNetwork: (n) => set({ network: n, networkLoading: false, networkError: null }),
  setNetworkLoading: (v) => set({ networkLoading: v }),
  setNetworkError: (e) => set({ networkError: e, networkLoading: false }),

  // Route planner inputs
  origin: "",
  destination: "",
  algorithm: "dijkstra",
  routeProfile: "BALANCED",
  setOrigin: (s) => set({ origin: s, routeResult: null, compareResult: null, selectedAlternative: null, routeError: null }),
  setDestination: (s) => set({ destination: s, routeResult: null, compareResult: null, selectedAlternative: null, routeError: null }),
  setAlgorithm: (a) => set({ algorithm: a }),
  setRouteProfile: (p) => set({ routeProfile: p }),

  // Route result
  routeResult: null,
  compareResult: null,
  selectedAlternative: null,
  routeLoading: false,
  routeError: null,
  setRouteResult: (r) => set({ routeResult: r, routeLoading: false, routeError: null }),
  setCompareResult: (c) => set({ compareResult: c, routeResult: c ? c.recommended : null, selectedAlternative: null, routeLoading: false, routeError: null }),
  setSelectedAlternative: (a) => set({ selectedAlternative: a }),
  setRouteLoading: (v) => set({ routeLoading: v }),
  setRouteError: (e) => set({ routeError: e, routeLoading: false }),

  // Simulation & Resilience state
  activeScenario: null,
  impactResult: null,
  resilienceMetrics: null,
  simulationLoading: false,
  simulationError: null,
  setActiveScenario: (s) => set({ activeScenario: s }),
  setImpactResult: (i) => set({ impactResult: i, simulationLoading: false, simulationError: null }),
  setResilienceMetrics: (r) => set({ resilienceMetrics: r, simulationLoading: false, simulationError: null }),
  setSimulationLoading: (v) => set({ simulationLoading: v }),
  setSimulationError: (e) => set({ simulationError: e, simulationLoading: false }),

  // Operations Control Center
  operationsState: null,
  selectedTrain: null,
  selectedStationInspection: null,
  setOperationsState: (s) => set({ operationsState: s }),
  setSelectedTrain: (t) => set({ selectedTrain: t }),
  setSelectedStationInspection: (st) => set({ selectedStationInspection: st }),

  // Map interaction
  hoveredStation: null,
  selectedStation: null,
  setHoveredStation: (id) => set({ hoveredStation: id }),
  setSelectedStation: (id) => set({ selectedStation: id }),
}));




// Shared TypeScript types for Namma Pulse frontend.

export interface ApiError {
  detail: string;
}

export interface Station {
  name: string;
  lines: string[];
  is_interchange: boolean;
  representative_id: string;
}

export interface StationsResponse {
  count: number;
  stations: Station[];
}

export interface StationTopology {
  id: string;
  name: string;
  line: string;
  sequence: number;
  is_interchange: boolean;
  interchange_lines: string[];
  line_status?: string;
  is_active?: boolean;
  x: number;
  y: number;
}

export interface EdgeTopology {
  from_id: string;
  to_id: string;
  line: string;
  edge_type: "segment" | "transfer";
  edge_id: string;
}

export interface InterchangeLocation {
  name: string;
  station_ids: string[];
  lines?: string[];
  x: number;
  y: number;
}

export interface NetworkResponse {
  stations: StationTopology[];
  edges: EdgeTopology[];
  lines: string[];
  active_lines?: string[];
  interchange_locations: InterchangeLocation[];
}

export interface RouteSegment {
  line: string;
  station_ids: string[];
  station_names: string[];
  segment_time_min: number;
}

export type RouteProfile =
  | "BALANCED"
  | "FASTEST"
  | "LEAST_CONGESTED"
  | "MOST_RELIABLE"
  | "FEWEST_TRANSFERS";

export interface ScoreBreakdown {
  travel_time: number;
  congestion_penalty: number;
  delay_penalty: number;
  transfer_penalty: number;
  total: number;
}

export interface RouteResponse {
  origin: string;
  destination: string;
  origin_id: string;
  destination_id: string;
  algorithm: string;
  station_ids: string[];
  station_names: string[];
  segments: RouteSegment[];
  total_time_min: number;
  total_distance_km: number | null;
  interchange_count: number;
  interchange_stations: string[];
  hop_count: number;
  lines: string[];
  notes: string[];

  // Phase 4 Extensions
  route_profile?: RouteProfile;
  total_dynamic_cost?: number;
  predicted_travel_time?: number;
  predicted_congestion?: number;
  delay_risk?: number;
  reliability_score?: number;
  transfer_count?: number;
  score_breakdown?: ScoreBreakdown;
  recommendation_reason?: string;
  prediction_source?: string;
}

export interface DynamicRouteCompareResponse {
  recommended: RouteResponse;
  alternatives: RouteResponse[];
  profile: RouteProfile;
  network_state_timestamp: string;
  model_versions: Record<string, unknown>;
  data_provenance: Record<string, string>;
}

export interface DisruptionOut {
  id: string;
  name: string;
  type: string;
  severity: string;
  description: string;
  start_time: string;
  end_time: string;
  affected_lines: string[];
  affected_stations: string[];
  affected_edges: string[];
  active: boolean;
  delay_multiplier: number;
  congestion_multiplier: number;
  demand_multiplier: number;
}

export interface ScenarioOut {
  id: string;
  name: string;
  type: string;
  target: string;
  severity: string;
  duration_min: number;
  description: string;
  active: boolean;
  provenance_label: string;
  disruptions: DisruptionOut[];
  active_lines?: string[];
  headway_sec?: number;
  demand_multiplier?: number;
}

export interface SimulationStateResponse {
  active_scenario: ScenarioOut | null;
  is_active: boolean;
  affected_edge_count: number;
  provenance: string;
}

export interface RouteImpactResponse {
  origin: string;
  destination: string;
  profile: string;
  scenario_id?: string;
  unreachable: boolean;
  error_detail?: string;
  baseline_route: RouteResponse | null;
  disrupted_route: RouteResponse | null;
  baseline_time_min?: number;
  disrupted_time_min?: number;
  travel_time_change_min?: number;
  travel_time_change_pct?: number;
  baseline_congestion_pct?: number;
  disrupted_congestion_pct?: number;
  congestion_change_pct?: number;
  baseline_transfers?: number;
  disrupted_transfers?: number;
  transfer_change?: number;
  route_changed: boolean;
  recommendation: string;
  data_provenance: Record<string, string>;
}

export interface CascadingCongestionEdge {
  edge: string;
  rerouted_passengers_load: number;
  derived_congestion_increase_pct: number;
  data_provenance: string;
}

export interface ResilienceMetricsResponse {
  scenario_id: string;
  scenario_name: string;
  sample_size: number;
  seed: number;
  route_availability_pct: number;
  avg_travel_time_impact_pct: number;
  unreachable_od_rate_pct: number;
  rerouting_success_rate_pct: number;
  avg_transfer_change: number;
  resilience_score: number;
  reachable_count: number;
  unreachable_count: number;
  disrupted_count: number;
  rerouted_count: number;
  cascading_congestion_edges: CascadingCongestionEdge[];
  data_provenance: Record<string, string>;
}



export interface CongestionPrediction {
  edge_id: string;
  line: string;
  date: string;
  time_slot: number;
  slot_start: string;
  predicted_congestion_pct: number | null;
  congestion_band: string | null;
  model_version: string;
  data_provenance: string;
}

export interface EdgeNetworkState {
  edge_id: string;
  from_id: string;
  to_id: string;
  line: string;
  line_status: string;
  active: boolean;
  scheduled_time_min: number;
  predicted_travel_time_min: number | null;
  predicted_congestion_pct: number | null;
  congestion_band: string | null;
  delay_risk_prob: number | null;
  data_provenance: string;
}

export interface NetworkStateResponse {
  date: string;
  time_slot: number;
  slot_start: string;
  edge_count: number;
  edges: EdgeNetworkState[];
}

export interface ModelMetrics {
  model_name?: string;
  model_version?: string;
  algorithm?: string;
  target?: string;
  validation_method?: string;
  features?: string[];
  test_metrics?: {
    mae?: number;
    rmse?: number;
    r2?: number;
    pr_auc?: number;
    roc_auc?: number;
    precision?: number;
    recall?: number;
    f1?: number;
  };
  baseline_test_metrics?: {
    mae?: number;
    rmse?: number;
  };
  comparison?: {
    baseline_mae?: number;
    model_mae?: number;
    mae_improvement_pct?: number;
    baseline_rmse?: number;
    model_rmse?: number;
    rmse_improvement_pct?: number;
  };
  shap_importance?: Record<string, number>;
  skipped?: boolean;
  reason?: string;
}

export interface ModelPerformanceResponse {
  congestion: ModelMetrics;
  travel_time: ModelMetrics;
  delay_risk: ModelMetrics;
}

export type LineColor = "Purple" | "Green" | "Yellow" | "Pink" | "Blue";

export const LINE_COLORS: Record<LineColor, string> = {
  Purple: "#7B2D8B",
  Green: "#2A7D4F",
  Yellow: "#D4A017",
  Pink: "#E05297",
  Blue: "#00A3E0",
};

export const LINE_COLORS_LIGHT: Record<LineColor, string> = {
  Purple: "#9B4DAB",
  Green: "#3A9D6F",
  Yellow: "#E8BB3A",
  Pink: "#F073B0",
  Blue: "#38C2F8",
};

export const LINE_STATUS: Record<LineColor, { label: string; isOperational: boolean }> = {
  Purple: { label: "Operational", isOperational: true },
  Green: { label: "Operational", isOperational: true },
  Yellow: { label: "Operational", isOperational: true },
  Pink: { label: "Under Construction", isOperational: false },
  Blue: { label: "Under Construction", isOperational: false },
};

export type Algorithm = "dijkstra" | "astar";
export type DataProvenance = "REAL" | "SYNTHETIC" | "DERIVED" | "SIMULATED";

export interface Train {
  train_id: string;
  line: string;

  direction: string;
  origin_station: string;
  destination_station: string;
  current_station_idx: number;
  current_station: string;
  next_station: string;
  current_segment: string;
  progress_pct: number;
  scheduled_departure: string;
  scheduled_arrival_next: string;
  expected_arrival_next: string;
  delay_seconds: number;
  delay_formatted: string;
  status: "ON_TIME" | "MINOR_DELAY" | "DELAYED" | "CRITICAL_DELAY" | "STOPPED" | "COMPLETED";
  is_held: boolean;
  hold_reason?: string;
  is_completed: boolean;
  data_provenance: string;
}

export interface OperationsClock {
  current_time_sec: number;
  formatted_time: string;
  is_running: boolean;
  speed_multiplier: number;
  data_provenance: string;
}

export interface OperationsAlert {
  id: string;
  timestamp: string;
  severity: "INFO" | "WARNING" | "CONGESTION" | "CRITICAL";
  icon: string;
  title: string;
  message: string;
  source: string;
}

export interface OperationsKPIs {
  total_trains: number;
  on_time: number;
  delayed: number;
  stopped: number;
  active_incidents: number;
  high_congestion_areas: number;
}

export interface OperationsState {
  clock: OperationsClock;
  network_status: "NORMAL" | "DEGRADED" | "DISRUPTED" | "CRITICAL";
  network_status_badge: string;
  active_scenario: ScenarioOut | null;
  kpis: OperationsKPIs;
  trains: Train[];
  alerts: OperationsAlert[];
  data_provenance: string;
}

export interface StationInspection {
  station_name: string;
  incoming_trains: Train[];
  outgoing_trains: Train[];
  platform_demand: string;
  current_congestion_pct: number;
  predicted_congestion_15min_pct: number;
  next_train_eta: string;
  active_incidents: string[];
  data_provenance: string;
}


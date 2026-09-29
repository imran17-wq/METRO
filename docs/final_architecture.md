# Namma Pulse — Final System Architecture (Phases 0–6)

## 1. System Overview

Namma Pulse is an end-to-end **Intelligent Route Optimization, Congestion Management, and Network Resilience Analysis System** built for the Bengaluru Metro Rail Corporation Limited (BMRCL) network.

The platform combines:
1. A single canonical NetworkX graph representation of the 5-line Bengaluru metro system ($N=118$ physical stations, $E=124$ edge pairs).
2. A synthetic passenger demand and gravity-model flow pipeline ($1.4\text{M}$ trips/week across 96 daily 15-minute time slots).
3. A Machine Learning prediction layer (LightGBM congestion & travel-time regressors, XGBoost delay risk classifier, SHAP explainability).
4. An Intelligent Dynamic Router generating candidate paths ($K=5$) via Yen's algorithm, evaluated against a multi-factor cost model and filtered by 4D Pareto dominance across 5 configurable user profiles.
5. A Disruption Simulation & Network Resilience Engine supporting 7 operational disruption categories and 8 pre-packaged deterministic scenarios with zero-topology graph mutation.
6. An Executive Command Center frontend dashboard with authoritative shared disruption state, real API 1-click demo workflow, and data provenance taxonomy.

---

## 2. Canonical Graph & Line Topology

The graph is constructed in `src/graph/metro_graph.py` from verified BMRCL reference specifications (`data/processed/stations.csv` and `data/processed/edges.csv`).

- **Physical Stations**: 118 stations across 5 lines.
- **Interchange Hubs**: 7 interchanges (Nadaprabhu Kempegowda Station Majestic, Rashtreeya Vidyalaya Road RV Road, Krishnarajapura KR Pura, Central Silk Board, Jayadeva Hospital, MG Road, Nagawara).
- **Line Status**:
  - `Purple Line` ($37$ stations): OPERATIONAL
  - `Green Line` ($31$ stations): OPERATIONAL
  - `Yellow Line` ($16$ stations): OPERATIONAL
  - `Pink Line` ($18$ stations): UNDER CONSTRUCTION / INACTIVE
  - `Blue Line` ($30$ stations): UNDER CONSTRUCTION / INACTIVE

---

## 3. Synthetic Data & Demand Pipeline

- **Demand Model**: Gravity model ($D_{ij} = \frac{A_i \cdot P_j}{d_{ij}^\gamma}$) incorporating station categories (`residential`, `commercial`, `it_hub`, `transit_hub`, `airport`) and 15-minute temporal slot factors.
- **Capacity**: 1,000 passengers per 6-coach train ($100\%$ capacity = nominal rating; peak capacity cap = $95\%$).
- **Dataset**: Generated reproducibly with fixed random seed 42 over 30 simulated calendar days ($2,880$ time slots).

---

## 4. Machine Learning Prediction & Explainability Layer

- **Congestion Model**: LightGBM Regressor predicting 15-minute slot edge congestion percentage.
- **Travel-Time Model**: LightGBM Regressor predicting dynamic travel duration per edge segment.
- **Delay Risk Model**: XGBoost Binary Classifier predicting segment delay probability ($P_{\text{delay}} \ge 0.15$).
- **SHAP Explainability**: SHAP TreeExplainer global importance rankings.
- **Honest Performance Reporting**: Historical baseline (MAE: $0.10\%$) is reported alongside LightGBM (MAE: $0.44\%$) on synthetic data.

---

## 5. Intelligent Dynamic Routing Engine

- **Candidate Generation**: Yen's K-Shortest Simple Paths algorithm ($K=5$) on the single canonical graph without graph duplication.
- **Dynamic Cost Function**:
  $$\text{Cost}(e) = w_T \cdot T_e + w_C \cdot \text{Penalty}_C(C_e) + w_D \cdot \text{Penalty}_D(D_e) + w_{\text{XFER}} \cdot \text{Penalty}_{\text{XFER}}$$
- **5 Route Profiles**: `BALANCED`, `FASTEST`, `LEAST_CONGESTED`, `MOST_RELIABLE`, `FEWEST_TRANSFERS`.
- **Pareto Dominance Filter**: Removes candidate routes strictly dominated across travel time, congestion %, delay risk, and transfers.
- **Explanation Generator**: Synthesizes data-driven natural language explanations based on metric deltas.

---

## 6. Disruption Simulation & Network Resilience Engine

- **Zero Topology Mutation**: `ScenarioEngine` applies dynamic edge overlay dicts onto `NetworkStateService`. The underlying `nx.Graph` structure is 100% static.
- **7 Disruption Categories**: `STATION_CLOSURE`, `LINE_CLOSURE`, `EDGE_CLOSURE`, `INTERCHANGE_CLOSURE`, `SEVERE_DELAY`, `CONGESTION_SURGE`, `DEMAND_SURGE`.
- **8 Scenario Library Entries**: Majestic Closure, RV Road Interchange Closure, Purple Line Closure, Blue Line Closure, Majestic Congestion, Silk Board Demand Surge, KR Pura Track Closure, Nagawara Delay.
- **Cascading Demand Redistribution**: Reassigns demand from disrupted journeys onto alternative candidate paths, aggregating load only on alternative edges (`DERIVED_SIMULATION_OUTPUT`).
- **Composite Resilience Score ($0-100$)**:
  $$\text{ResilienceScore} = 0.40 \cdot S_{\text{avail}} + 0.30 \cdot S_{\text{time}} + 0.20 \cdot S_{\text{unreach}} + 0.10 \cdot S_{\text{reroute}}$$

---

## 7. Data Provenance Taxonomy

| Badge | Classification | Description |
|---|---|---|
| `REAL SOURCE NETWORK` | REAL | Verified topology, station names, and fleet specs from BMRCL reference. |
| `SYNTHETIC` | SYNTHETIC | Gravity-model passenger demand, OD matrix, and delay events. |
| `SYNTHETIC MODEL OUTPUT` | MODEL | Predictions generated by LightGBM / XGBoost models. |
| `DERIVED` | DERIVED | Dynamic route costs, Pareto filtering, and composite resilience scores. |
| `SIMULATED SCENARIO` | SIMULATED | What-if scenario disruption overlays. |

---

## 8. Frontend Architecture & Shared State

- **Framework**: React 18 + TypeScript + Vite + TailwindCSS.
- **Shared State**: Single Zustand store (`useStore.ts`) synced with FastAPI backend `NetworkStateService`. Activation/deactivation on `/simulation` or `/resilience` immediately updates all pages (`Command Center`, `Route Planner`, `MetroMap`).
- **MetroMap Component**: Solid rendering of all 5 base lines. Dynamic route highlights, disruption markers, and alternative route overlays rendered on top.

---

## 9. End-to-End Workflow Example

### Step 1: Baseline Route Call
- **Journey**: `Whitefield (Kadugodi)` → `Silk Institute`
- **API Call**: `GET /api/routes/compare?origin=Whitefield%20(Kadugodi)&destination=Silk%20Institute&profile=BALANCED`
- **Result**: Baseline Time: **42.0 min**, Transfers: **1** (Purple → Green at Majestic)

### Step 2: Activate Disruption Scenario
- **API Call**: `POST /api/simulation/scenarios/majestic_closure/activate`
- **Result**: `status = ACTIVE`, $12$ edges affected by Majestic platform closure.

### Step 3: Recalculate Disrupted Route
- **API Call**: `GET /api/routes/compare?origin=Whitefield%20(Kadugodi)&destination=Silk%20Institute&profile=BALANCED`
- **Result**: Disrupted Time: **51.0 min** ($+9.0\text{ min}$, $+21.4\%$), Transfers: **2** (Rerouted around Majestic via RV Road interchange).

### Step 4: Request Resilience Impact
- **API Call**: `GET /api/simulation/resilience?scenario_id=majestic_closure&sample_size=50`
- **Result**: Resilience Score: **87.2 / 100**, Route Availability: **100%**, Rerouting Success: **100%**.

### Step 5: Deactivate Scenario & Restore State
- **API Call**: `POST /api/simulation/scenarios/majestic_closure/deactivate`
- **Result**: `status = DEACTIVATED`, $0$ affected edges. Baseline route time restored to **42.0 min**.

---

## 10. System Limitations & Future Work

### Limitations
1. **Synthetic Demand**: Demand matrix and congestion flows are synthetically generated using gravity models due to lack of public BMRCL AFC tap-in/tap-out data.
2. **Fixed Time Slots**: Predictions operate on 15-minute discrete time buckets.

### Future Work
1. Real-time GTFS-RT / AFC tap-in API data ingestion.
2. Multi-modal integration (BMTC feeder bus + Metro dynamic ticketing).

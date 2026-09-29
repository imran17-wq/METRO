# Namma Pulse

**Bengaluru Metro Intelligent Route & Congestion Management System**

---

## Phase 0 — Network Foundation

### What is Namma Pulse?

Namma Pulse is an intelligent transit analytics system for the Bengaluru (Namma) Metro network. It models the metro as a graph, validates its topology, and will eventually provide real-time congestion prediction and intelligent rerouting.

This repository currently contains **Phase 0**: the clean, validated graph representation of the operational metro network. No ML models, no dashboards, no synthetic demand — just the real network, correctly modelled.

---

### Why a Graph?

A metro network is inherently a graph:

- **Stations are nodes** — discrete points where passengers board and alight.
- **Track segments are edges** — connections between consecutive stations.

A graph representation allows:
- Shortest-path queries (Dijkstra, A\*, etc.)
- Interchange detection
- Line-specific filtering
- Later: dynamic edge weights (congestion, disruption, reliability)

The implementation uses **NetworkX** (`nx.Graph`) — an undirected graph that naturally supports bidirectional traversal, edge metadata, and future extensibility.

---

### Network Scope (Phase 0)

#### Included Lines

| Line | Terminals | Stations |
|------|-----------|----------|
| 🟣 Purple | Whitefield (Kadugodi) ↔ Challaghatta | 36 |
| 🟢 Green | Madavara ↔ Silk Institute | 32 |
| 🟡 Yellow | RV Road ↔ Bommasandra | 16 |

**Total nodes:** 84 | **Total edges:** 83

#### Deliberately Excluded Lines

| Line | Reason |
|------|--------|
| 🩷 Pink | Under construction / not fully operational. Will be added as an expansion scenario. |
| 🔵 Blue | Under construction / not fully operational. Will be added as an expansion scenario. |

---

### What the Nodes Represent

Each node in the graph represents a **line-specific station record**:

- A station that exists on two lines appears **twice** (once per line), with the same physical name but different node IDs (e.g., `PL22` and `GL17` both represent Majestic station).
- Interchange stations are linked by a **TRANSFER edge** (distance = 0 km, time = 0 min placeholder) to allow routing algorithms to change lines.

Node attributes: `station_name`, `line`, `sequence`, `is_interchange`, `interchange_lines`, `notes`.

---

### What the Edges Represent

Each edge represents a **track segment between two consecutive stations on the same line**.

Edge attributes:

| Field | Status | Notes |
|-------|--------|-------|
| `edge_id` | ✅ Present | Unique ID (e.g., `PL_E01`) |
| `line` | ✅ Present | Line name |
| `sequence` | ✅ Present | Position within the line |
| `distance_km` | ❌ `NA` | Not available from source map |
| `scheduled_time_min` | ❌ `NA` | Not available in per-segment form |
| `predicted_travel_time` | 🔜 Reserved | Phase 3+ (ML output) |
| `congestion_penalty` | 🔜 Reserved | Phase 3+ |
| `disruption_status` | 🔜 Reserved | Phase 4+ (real-time feed) |
| `reliability_score` | 🔜 Reserved | Phase 4+ |

---

### How the PDF Was Used

The source map (`Metro_Map_2025_-_Bengaluru_City.pdf`) was used as the **primary visual reference** for:
- Station names (preserved as closely as possible)
- Station ordering within each line
- Interchange identification

Since the PDF could not be machine-parsed, the topology was extracted visually and **cross-referenced** against:
- Wikipedia – Namma Metro article
- BMRCL official website (bengalurumetro.in)
- beegru.com and other secondary sources

All discrepancies are recorded in [`docs/topology_issues.md`](docs/topology_issues.md).

---

### What is Known vs Approximate

| Data | Status |
|------|--------|
| Station names | REAL (from PDF + cross-references) |
| Station sequence | REAL (from map visual order) |
| Interchange stations | REAL (Majestic: Purple↔Green; RV Road: Green↔Yellow) |
| Edge connections (consecutive pairs) | REAL |
| Per-segment distances | NOT AVAILABLE (NA) |
| Per-segment travel times | NOT AVAILABLE (NA) |
| Transfer walk times at interchanges | APPROXIMATE (0.0 placeholder; real ≈ 3–8 min) |

See [`docs/data_provenance.md`](docs/data_provenance.md) for full classification.

---

### Project Structure

```
namma-pulse/
├── data/
│   ├── processed/
│   │   ├── stations.csv       ← Station nodes dataset
│   │   └── edges.csv          ← Edge segment dataset
│   ├── raw/                   ← (future: GTFS feeds, raw scrapes)
│   └── reference/             ← (future: DPR documents, survey data)
│
├── src/
│   ├── graph/
│   │   ├── metro_graph.py     ← Core graph builder & query API
│   │   ├── station_model.py   ← Station dataclass
│   │   ├── edge_model.py      ← Edge dataclass
│   │   └── validation.py      ← Structural validation checks
│   └── config/
│       └── settings.py        ← Paths and constants
│
├── scripts/
│   ├── build_network.py       ← Build graph and print summary
│   └── validate_network.py    ← Run all validation checks
│
├── tests/
│   ├── test_graph.py          ← Graph API unit tests
│   ├── test_station_data.py   ← CSV dataset tests
│   └── test_network_integrity.py  ← Network-level integrity tests
│
├── docs/
│   ├── topology.md            ← Full station table reference
│   ├── topology_issues.md     ← Ambiguities and open questions
│   └── data_provenance.md     ← Data classification
│
├── requirements.txt
└── README.md
```

---

### Setup & Running

#### 1. Install dependencies

```bash
pip install -r requirements.txt
```

#### 2. Build the graph

```bash
python scripts/build_network.py
```

#### 3. Run validation

```bash
python scripts/validate_network.py
```

#### 4. Run unit tests

```bash
python -m pytest tests/ -v
```

---

---

### Phase 3 — ML Prediction Layer

#### Overview
Phase 3 adds an explainable machine learning prediction layer for edge congestion percentage, realistic travel time, and delay event risk. All predictions include explicit data provenance metadata (`data_provenance = SYNTHETIC MODEL OUTPUT`).

#### Key Features
- **Congestion Model**: LightGBM Regressor (edge × 15-min slot granularity).
- **Travel-Time Model**: LightGBM Regressor (realistic travel time including congestion penalties & delay events).
- **Delay Risk Model**: XGBoost Classifier (predicts probability of delay occurrence).
- **Target Leakage Prevention**: Enforced feature audit via `src/ml/features/leakage_check.py`.
- **Chronological Validation**: 30-day synthetic dataset split strictly by date order (70% train / 15% val / 15% test).
- **Network State Builder**: Combines static 5-line graph + ML predictions + active line states. Pink/Blue under-construction lines are assigned `null` predictions (`NO_SYNTHETIC_DATA`).
- **SHAP Explainability**: SHAP TreeExplainer global importance rankings and natural language explanations.

#### ML Commands
```bash
# 1. Expand synthetic dataset to 30 days
python scripts/expand_synthetic_data.py

# 2. Train and evaluate all ML models
python scripts/train_ml_models.py

# 3. Run full test suite
python -m pytest tests/ -v
```

See [`docs/ml_architecture.md`](docs/ml_architecture.md) for full architectural documentation.

---

### Phase 4 — Intelligent Dynamic Rerouting

#### Overview
Phase 4 elevates Namma Pulse from a shortest-path router into an **Intelligent Dynamic Rerouting System**. It generates K candidate routes, scores them against dynamic network state (travel time, predicted congestion %, delay risk, platform transfers), applies Pareto dominance filtering, and returns data-driven recommendations with alternative route comparisons.

#### Key Features
- **Candidate Route Generation**: Yen's K-shortest simple paths ($K=5$) on the single canonical graph without graph duplication.
- **Dynamic Edge Cost Model**: Multi-factor cost combining predicted travel time, normalized congestion penalty, delay risk penalty, and transfer penalty.
- **5 Configurable Route Profiles**: `FASTEST`, `BALANCED` (default), `LEAST_CONGESTED`, `MOST_RELIABLE`, and `FEWEST_TRANSFERS` (all weights in `src/config/routing_weights.py`).
- **Pareto Dominance Filter**: Automatically filters out strictly inferior alternative routes across 4 dimensions.
- **Data-Driven Explanations**: Dynamically synthesizes explanations ("Why this route?") from actual metric deltas.
- **Fallback Capability**: Gracefully falls back to scheduled/baseline routing if ML models or state are missing.
- **REST API Endpoints**: Extended `GET /api/route` and new `GET /api/routes/compare`.
- **Frontend Upgrade**: Integrated profile selector, recommended route card, score breakdown, and candidate route comparison overlay on the finalized 5-line MetroMap.

See [`docs/routing_engine.md`](docs/routing_engine.md) for full architectural details.

---

### Phase 5 — Disruption Simulation & Network Resilience

#### Overview
Phase 5 introduces a reproducible, scenario-based **Disruption Simulation & Network Resilience Engine**. It simulates 7 operational disruption types across an 8-scenario deterministic library using a zero-mutation network state overlay pattern. Integrates directly with Phase 4 dynamic routing to evaluate journey impact deltas, calculate representative OD resilience metrics, estimate targeted cascading demand redistribution, and display simulation results on the React frontend.

#### Key Features
- **Zero-Mutation Overlay**: Network state overlays modify edge availability and costs without changing or rebuilding the canonical NetworkX graph topology. Deactivation restores the exact base network state.
- **7 Disruption Types**: `STATION_CLOSURE`, `LINE_CLOSURE`, `EDGE_CLOSURE`, `INTERCHANGE_CLOSURE`, `SEVERE_DELAY`, `CONGESTION_SURGE`, `DEMAND_SURGE`.
- **8 Pre-Packaged Deterministic Scenarios**: Majestic Closure, RV Road Interchange Closure, Purple Line Closure, Blue Line Closure, Majestic Congestion, Silk Board Demand Surge, KR Pura Track Closure, Nagawara Delay.
- **Before vs After Route Comparison**: Calculates travel time deltas (min, %), transfer deltas, rerouted status, or unreachable status.
- **Representative OD Resilience Evaluator**: Evaluates a sample of OD station pairs (default 50, max 500, fixed seed 42) for Route Availability %, Avg Travel Time Impact %, Unreachable OD Rate %, and Rerouting Success %.
- **Targeted Cascading Congestion Redistribution**: Reassigns affected OD demand only onto alternative edges traversed by rerouted journeys (`DERIVED_SIMULATION_OUTPUT`).
- **Composite Resilience Score**: Documented 0–100 score combining availability (40%), travel time impact (30%), unreachable rate (20%), and rerouting success (10%).
- **REST API Endpoints**: Endpoints under `/api/simulation/*` for scenario management, activation, state, impact, resilience, and route comparison.
- **Frontend Resilience Simulator**: Dedicated React page (`/simulation`) with scenario selector, severity badges, activate/deactivate controls, impact cards, resilience gauge, and map disruption overlays.

See [`docs/disruption_simulation.md`](docs/disruption_simulation.md) for full architectural documentation.

---

### Phase 6 — Executive Command Center & Demo Integration

#### Overview
Phase 6 unifies all completed capabilities (Phases 0–5) into an integrated executive **Namma Pulse Command Center** dashboard. Features authoritative shared backend disruption state, a 1-click real API demo workflow runner, 8 dedicated page views, honest data reporting, and an explicit data provenance taxonomy.

#### Key Features
- **Executive Command Center**: Centralized dashboard displaying dynamic network counts (derived from metadata), network conditions, quick route launcher, active disruption banner, and resilience summary.
- **Shared Backend Disruption State**: Single source of truth. Scenario activation/deactivation on `/simulation` or `/resilience` immediately propagates across Command Center, Route Planner, and MetroMap.
See [`docs/final_architecture.md`](docs/final_architecture.md) for complete end-to-end system architecture.

---

### Phase 6.1 — Metro Operations Control Simulation

#### Overview
Phase 6.1 repositions Namma Pulse as a simulated **Bengaluru Metro Operations Control Center (OCC)**. It introduces a deterministic simulation clock, synthetic timetable generation, real-time train movement along canonical line paths, dynamic station dwell times, delay propagation, an operational alert engine, train & station inspection panels, simulation control actions (`HOLD`/`RELEASE`), and full integration with Phase 3 ML predictions, Phase 4 dynamic routing, and Phase 5 disruption scenarios.

#### Key Features
- **Deterministic Simulation Clock**: Simulated time starting at `08:00:00` with `PLAY`, `PAUSE`, `RESET` and speed multipliers (`1x`, `2x`, `5x`, `10x`).
- **Backend-Authoritative Train Movement**: Moving train positions derived from simulation time, timetable schedule, segment travel time, dwell time, and hold states.
- **Synthetic Operational Timetable**: Reproducible service schedule (seed 42) for default active lines (`Purple`, `Green`, `Yellow`). Pink & Blue remain inactive by default.
- **Dynamic Dwell & Downstream Delay**: Base 30s dwell + crowding penalties ($+10$s / $+20$s). Downstream delays propagate dynamically.
- **Operator Simulation Controls**: `HOLD TRAIN` / `RELEASE TRAIN` commands directly influencing simulated train movement.
- **Control Room Dashboard**: Moving train markers on the locked solid 5-line MetroMap, Train Inspection Panel, Station Inspection Panel, Alert Console, and Network Operation Status (`🟢 NORMAL`, `🟡 DEGRADED`, `🟠 DISRUPTED`, `🔴 CRITICAL`).
- **System Integrations**: ML predictions for simulation time slots, dynamic rerouting, and disruption scenario interactions (holding/delaying trains on closed segments, updating resilience).
- **REST APIs**: Operations endpoints under `/api/operations/*`.

See [`docs/operations_simulation.md`](docs/operations_simulation.md) for complete OCC system documentation.






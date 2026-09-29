# Phase 5 — Disruption Simulation & Network Resilience Engine

## Overview

Phase 5 introduces a reproducible, scenario-based **Disruption Simulation & Network Resilience Engine** for Namma Pulse. It enables real-time simulation of operational disruptions—such as station closures, line suspensions, track segment blockages, severe delays, interchange platform closures, and demand surges—without modifying or rebuilding the canonical 5-line NetworkX graph topology.

All simulation outputs and resilience calculations are explicitly tagged with `SIMULATED_SCENARIO` and `DERIVED_SIMULATION_OUTPUT`.

---

## 1. Disruption Architecture & Zero-Mutation Overlay

```
Canonical Graph Topology (nx.Graph — 100% Immutable)
        │
        ├── NetworkState Base (scheduled & ML predictions)
        │
        ├── Disruption Scenario Activation
        │      └─ Applies Edge Overlay Dict to NetworkStateService
        │
        ├── Phase 4 Intelligent Dynamic Router
        │      └─ Evaluates effective_active, effective_travel_time, effective_congestion
        │
        ├── Impact Analysis (Before vs After Single OD Journey Delta)
        │
        ├── Resilience Evaluator (Representative OD Sampling & Cascading Demand Redistribution)
        │
        └── Scenario Recovery (Deactivate → Clears Overlay → 100% Base State Restored)
```

---

## 2. Disruption Types & Severity Calibration

| Disruption Type | Description | Operational Effect |
|---|---|---|
| `STATION_CLOSURE` | Station platform closed | Incident track segments & station platform edges disabled (`active=false`). |
| `LINE_CLOSURE` | Full corridor suspension | All track segments belonging to that line disabled (`active=false`). |
| `EDGE_CLOSURE` | Specific track segment blocked | Targeted edge set disabled (`active=false`). |
| `INTERCHANGE_CLOSURE` | Transfer platform disabled | Transfer edges between lines (`line == "TRANSFER"`) disabled; through-train line track segments remain operational. |
| `SEVERE_DELAY` | Signal failure or speed restriction | Travel time multiplier applied to affected edges. |
| `CONGESTION_SURGE` | Overcrowding / platform surge | Congestion percentage multiplier applied to affected edges. |
| `DEMAND_SURGE` | Influx of passenger demand | Derived demand multiplier applied to incident station edges. |

### Severity Levels (`src/config/simulation_settings.py`)
- `LOW`: $1.25\times$ delay, $1.20\times$ congestion
- `MEDIUM`: $1.50\times$ delay, $1.40\times$ congestion
- `HIGH`: $2.00\times$ delay, $1.75\times$ congestion
- `CRITICAL`: Closure (`active=false`) or $3.50\times$ delay

---

## 3. Pre-Packaged Scenario Library (8 Deterministic Scenarios)

1. `majestic_closure`: Majestic Station Closure (`STATION_CLOSURE`, CRITICAL)
2. `rv_road_closure`: RV Road Interchange Closure (`INTERCHANGE_CLOSURE`, HIGH)
3. `purple_closure`: Purple Line Closure (`LINE_CLOSURE`, CRITICAL)
4. `blue_closure`: Blue Line Closure (`LINE_CLOSURE`, CRITICAL)
5. `majestic_congestion`: Severe Congestion at Majestic (`CONGESTION_SURGE`, HIGH)
6. `silk_board_surge`: Passenger Surge at Central Silk Board (`DEMAND_SURGE`, HIGH, multiplier $1.75\times$)
7. `kr_pura_track_closure`: Track Closure near KR Pura (`EDGE_CLOSURE`, CRITICAL)
8. `nagawara_delay`: Major Delay near Nagawara (`SEVERE_DELAY`, MEDIUM)

---

## 4. Representative OD Resilience Evaluation & Composite Score

### OD Sampling
- Evaluates a deterministic sample of OD station pairs (default 50 for fast API/tests, configurable up to 500 for full resilience analysis) generated with fixed seed `42`.

### Targeted Cascading Demand Redistribution
- Disrupted OD journeys re-route via Phase 4 candidate paths.
- Rerouted load is aggregated **only on alternative edges** actually traversed by rerouted passengers.
- Base synthetic datasets are never mutated.

### Composite Resilience Score Formula (0 to 100)
$$\text{ResilienceScore} = 0.40 \cdot S_{\text{avail}} + 0.30 \cdot S_{\text{time}} + 0.20 \cdot S_{\text{unreach}} + 0.10 \cdot S_{\text{reroute}}$$

Where:
- $S_{\text{avail}} = \text{RouteAvailability}\%$
- $S_{\text{time}} = \max(0, 100 - 2 \cdot \text{AvgTimeImpact}\%)$
- $S_{\text{unreach}} = \max(0, 100 - 3 \cdot \text{UnreachableRate}\%)$
- $S_{\text{reroute}} = \text{ReroutingSuccess}\%$

---

## 5. API Endpoints

- `GET /api/simulation/scenarios`: List all pre-packaged scenarios.
- `GET /api/simulation/scenarios/{scenario_id}`: Retrieve scenario details.
- `POST /api/simulation/scenarios/{scenario_id}/activate`: Activate disruption scenario overlay.
- `POST /api/simulation/scenarios/{scenario_id}/deactivate`: Deactivate scenario & restore exact base state.
- `GET /api/simulation/state`: Query active simulation state.
- `GET /api/simulation/impact`: Compare baseline vs disrupted route for single OD pair.
- `GET /api/simulation/resilience`: Evaluate network resilience metrics & composite score across representative OD sample.

---

## 6. Provenance Taxonomy

All simulation responses embed structured provenance tags:
```json
{
  "topology": "STATIC_TOPOLOGY_REAL_SOURCE_NETWORK",
  "demand": "SYNTHETIC",
  "prediction": "SIMULATED_SCENARIO",
  "scenario": "SIMULATED_SCENARIO",
  "impact": "DERIVED_SIMULATION_OUTPUT",
  "route": "DERIVED"
}
```

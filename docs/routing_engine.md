# Phase 4 — Intelligent Dynamic Rerouting Engine

## Overview

Phase 4 turns Namma Pulse from a static shortest-path router into an **Intelligent Dynamic Routing System**. It evaluates multiple candidate paths on the single canonical 5-line network using dynamic travel times, predicted congestion percentages, delay risks, and platform transfer penalties across five distinct user route preference profiles.

---

## Architecture & Flow

```
Origin + Destination
        │
        ├── candidate generation (Yen's K-shortest simple paths, K=5)
        │
        ├── NetworkState evaluation (travel time, congestion, delay risk, transfers)
        │
        ├── RouteScorer (apply profile weight table)
        │
        ├── Pareto dominance filter (eliminate strictly inferior options)
        │
        ├── Explanation generator (data-driven metric delta text)
        │
        └── DynamicRouteResult (Recommended Route + Non-dominated Alternatives)
```

---

## 1. Candidate Route Generation (Yen's Algorithm)

- **Algorithm**: Yen's K-Shortest Simple Paths algorithm via NetworkX `shortest_simple_paths`.
- **K value**: 5.
- **Topology preservation**: Does NOT duplicate or rebuild the graph. Operates on the single canonical 5-line graph (`nx.Graph`).
- **Line & Edge Eligibility**: Inactive lines (Pink/Blue by default) or edges marked `active=false` return infinite cost and cannot be traversed.

---

## 2. Dynamic Edge Cost Model

Every edge $e$ is evaluated using normalized minute-equivalent components:

$$\text{dynamic\_cost}(e) = w_t \cdot T_{\text{travel}} + w_c \cdot C_{\text{penalty}} + w_d \cdot D_{\text{penalty}} + w_r \cdot R_{\text{penalty}}$$

Where:
- $T_{\text{travel}} = \text{predicted\_travel\_time\_min}$ (fallback: `scheduled_time_min` or 2.5 min)
- $C_{\text{penalty}} = (\text{predicted\_congestion\_pct} / 100.0) \times 5.0\text{ min}$
- $D_{\text{penalty}} = \text{delay\_risk\_prob} \times 10.0\text{ min}$
- $R_{\text{penalty}} = 3.0\text{ min}$ (on `TRANSFER` platform edges only)

---

## 3. Route Preference Profiles & Weight Tables

| Profile | Travel Time ($w_t$) | Congestion ($w_c$) | Delay Risk ($w_d$) | Transfer ($w_r$) |
|---|---|---|---|---|
| **BALANCED** (default) | 1.0 | 0.25 | 0.20 | 2.0 |
| **FASTEST** | 2.5 | 0.05 | 0.05 | 0.3 |
| **LEAST_CONGESTED** | 0.8 | 2.5 | 0.50 | 1.0 |
| **MOST_RELIABLE** | 0.8 | 0.50 | 3.00 | 1.0 |
| **FEWEST_TRANSFERS** | 0.8 | 0.10 | 0.10 | 6.0 |

All weights live in `src/config/routing_weights.py` and can be re-calibrated without changing code.

---

## 4. Pareto Dominance Filtering

To prevent displaying obviously inferior alternative routes in the UI, candidate routes undergo a strict Pareto dominance check across 4 dimensions:
1. Travel time
2. Congestion %
3. Delay risk probability
4. Transfer count

A candidate route $B$ is filtered out if another candidate route $A$ is **no worse** in all 4 dimensions and **strictly better** in at least one.

---

## 5. "Why This Route?" Explanation Generator

Explanations are generated dynamically from actual metric deltas between the recommended route and alternative candidate routes. No explanations are hardcoded.

**Examples**:
- *"Recommended because it offers 3.2 minutes faster travel time and 18.5% lower predicted congestion."*
- *"Recommended for fewest transfers: 0 transfer(s) vs 1 on alternative route."*
- *"Recommended as the fastest route: 4.5 min faster than alternative option."*

---

## 6. Fallback Behavior & Data Provenance

- **Fallback**: If ML prediction models are unavailable or unindexed, edge costs fall back to scheduled times (2.5 min/segment, 3.0 min/transfer) and historical baseline congestion. The prediction source is explicitly flagged as `FALLBACK`.
- **Provenance**: Every response includes metadata:
  ```json
  "data_provenance": {
    "topology": "STATIC_TOPOLOGY_REAL_SOURCE_NETWORK",
    "demand": "SYNTHETIC",
    "prediction": "SYNTHETIC_MODEL_OUTPUT",
    "route": "DERIVED",
    "network_state_date": "2024-01-08",
    "network_state_time_slot": "36"
  }
  ```

---

## 7. API Endpoints

- `GET /api/route?origin=...&destination=...&profile=BALANCED&date=...&time_slot=...`
  Returns single recommended `RouteResponse` with Phase 4 metric extensions. If `profile` is omitted, preserves backward-compatible Phase 1 Dijkstra/A* output.

- `GET /api/routes/compare?origin=...&destination=...&profile=BALANCED&date=...&time_slot=...`
  Returns `DynamicRouteCompareResponse` containing recommended route, ranked non-dominated alternative routes, profile, state timestamp, and provenance.

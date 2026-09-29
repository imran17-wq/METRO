# Namma Pulse — Metro Operations Control Simulation (Phase 6.1)

## 1. Overview

Namma Pulse Phase 6.1 repositions the platform as a simulated **Bengaluru Metro Operations Control Center (OCC)**.

The system simulates time-based railway operations across the single canonical 5-line NetworkX graph topology. OCC operators can track moving train services in real time, monitor station platform conditions, respond to operational alerts, execute simulation control commands (`HOLD`/`RELEASE`), and observe the systemic cascading effects of Phase 5 disruption scenarios.

> [!IMPORTANT]
> **Simulated Operations Disclosure**:
> This platform is a SIMULATED operations control environment built for demonstration and analysis. It is **NOT** a live BMRCL feed, GTFS-RT feed, or real railway signaling system.

---

## 2. Core Operational Components

### 2.1 Simulation Clock Engine
- **Simulated Time**: Operates deterministically in seconds from midnight (default start: `08:00:00` AM / 28,800 sec).
- **Controls**: `PLAY`, `PAUSE`, `RESET`.
- **Speed Multipliers**: `1x`, `2x`, `5x`, `10x`.
- **Data Label**: `SIMULATED OPERATIONS`.

### 2.2 Synthetic Timetable Generator
- **Reproducible Schedule**: Generated with fixed random seed 42.
- **Active Operational Lines**: `Purple`, `Green`, and `Yellow` lines operate peak 6-minute headway passenger services starting at `08:00:00`.
- **Inactive Lines**: `Pink` and `Blue` lines default to `UNDER_CONSTRUCTION` / `INACTIVE` (0 scheduled passenger services) unless explicitly activated by line-state configuration.
- **Data Label**: `SYNTHETIC OPERATIONS SCHEDULE`.

### 2.3 Train Entity & Movement Model
- **Train Attributes**: `train_id`, `line`, `direction`, `origin_station`, `destination_station`, `current_station`, `next_station`, `current_segment`, `scheduled_departure`, `scheduled_arrival_next`, `expected_arrival_next`, `delay_seconds`, `status`, `progress_pct`, `is_held`, `hold_reason`.
- **Status Classification**:
  - $0 - 60$ sec delay: `ON_TIME`
  - $61 - 180$ sec delay: `MINOR_DELAY`
  - $181 - 300$ sec delay: `DELAYED`
  - $> 300$ sec delay: `CRITICAL_DELAY`
  - Operator / Disruption Held: `STOPPED`
  - Journey Completed: `COMPLETED`
- **Position Calculation**: Positions are computed deterministically from simulation time, timetable schedules, and segment progress percentage ($0.0 \to 1.0$). Frontend renders backend simulation state directly with zero fake frontend animations.

### 2.4 Station Dwell & Segment Running Time
- **Segment Running Time**: Derived from canonical graph edge travel times (default 150 sec / 2.5 min per station segment).
- **Station Dwell Time**:
  - Base Dwell: 30 seconds
  - High Demand ($> 60\%$ station/edge congestion): $+10$ seconds penalty
  - Critical Crowding ($> 80\%$ congestion): $+20$ seconds penalty

### 2.5 Downstream Delay Propagation
When a train experiences delay at a station or segment (e.g. held by an operator or delayed by crowding), subsequent downstream arrival and departure expectations adjust dynamically (`expected_arrival_next = scheduled_arrival_next + delay_seconds`).

### 2.6 Operator Controls (`SIMULATION CONTROL`)
- `HOLD TRAIN`: Holds selected train at current station (`status = STOPPED`), accumulating delay until released.
- `RELEASE TRAIN`: Releases held train, allowing it to resume normal deterministic movement along line sequence.

### 2.7 Control Room Alert Engine
Generates real-time OCC alert feed:
- 🟢 `INFO`: Network operating normally
- 🟡 `WARNING`: Minor train delay ($> 60$ sec)
- 🟠 `CONGESTION`: High track/platform crowding ($> 60\%$)
- 🔴 `CRITICAL`: Critical delay ($> 300$ sec), train held, or active disruption scenario

---

## 3. System Integrations (Phases 3, 4, 5)

### Phase 3 ML Predictions
Station inspection panels fetch 15-minute slot ML congestion predictions (`predicted_congestion_15min_pct`) from LightGBM regressors trained on synthetic demand datasets (`SYNTHETIC MODEL OUTPUT`).

### Phase 4 Dynamic Rerouting
When disruption scenarios alter network conditions, dynamic route recommendations (`/api/routes/compare`) evaluate current effective edge costs and Pareto dominance.

### Phase 5 Disruption Simulation
Activating a scenario (e.g. `majestic_closure`):
1. Trains approaching or traversing affected disruption targets are automatically held or delayed (`status = STOPPED` / `CRITICAL_DELAY`).
2. Control room alert engine emits `🔴 ACTIVE SIMULATED INCIDENT` alerts.
3. Network operation status updates dynamically to `🚨 CRITICAL` / `DISRUPTED`.
4. Deactivating the scenario clears disruption holds and restores normal train movement.

---

## 4. REST API Reference (`/api/operations/*`)

| Endpoint | Method | Description |
|---|---|---|
| `/api/operations/state` | GET | Returns full OCC state (clock, KPIs, trains, alerts). |
| `/api/operations/trains` | GET | Returns active train pool. |
| `/api/operations/trains/{train_id}` | GET | Returns train inspection details. |
| `/api/operations/stations/{station_id}` | GET | Returns OCC station inspection data. |
| `/api/operations/simulation/start` | POST | Starts simulation clock (`PLAY`). |
| `/api/operations/simulation/pause` | POST | Pauses simulation clock (`PAUSE`). |
| `/api/operations/simulation/reset` | POST | Resets clock to 08:00:00 AM and reinstantiates trains. |
| `/api/operations/simulation/tick` | POST | Advances clock by N seconds. |
| `/api/operations/simulation/speed` | POST | Sets speed multiplier (1x, 2x, 5x, 10x). |
| `/api/operations/trains/{train_id}/hold` | POST | Simulated operator hold command. |
| `/api/operations/trains/{train_id}/release` | POST | Simulated operator release command. |

---

## 5. System Limitations & Non-Goals

1. **Simulated Environment**: Not a real railway control system or live BMRCL feed.
2. **Simplified Signaling**: Uses deterministic segment travel and dwell time calculations without full moving-block CBTC signaling simulation.
3. **No WebSockets**: Uses periodic HTTP polling and simulation tick updates.

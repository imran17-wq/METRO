/**
 * CommandCenterPage.tsx — Namma Pulse Bengaluru Metro Operations Control Center (OCC).
 *
 * Repositioned as a Simulated Operations Control Room featuring:
 * - Deterministic Simulation Clock (Play, Pause, Reset, Speed 1x/2x/5x/10x)
 * - Dynamic OCC KPIs & Network Status (NORMAL, DEGRADED, DISRUPTED, CRITICAL)
 * - Moving Train Markers on locked solid 5-Line MetroMap
 * - Train Inspection Panel with Operator Hold/Release controls
 * - Station Inspection Panel with Incoming/Outgoing trains & ML congestion predictions
 * - Live Operational Alert Engine
 * - 1-Click End-to-End Acceptance Workflow Runner
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchNetwork,
  fetchOperationsState,
  startOperationsSimulation,
  pauseOperationsSimulation,
  resetOperationsSimulation,
  tickOperationsSimulation,
  setOperationsSimulationSpeed,
  holdTrain,
  releaseTrain,
  fetchStationInspection,
  activateSimulationScenario,
  deactivateSimulationScenario,
  fetchRouteComparison,
  fetchNetworkResilience,
} from "../services/api";
import { useStore } from "../store/useStore";
import MetroMap from "../components/MetroMap/MetroMap";
import type {
  DynamicRouteCompareResponse,
  ResilienceMetricsResponse,
} from "../types";

const CommandCenterPage: React.FC = () => {
  const {
    network,
    setNetwork,
    setNetworkLoading,
    setNetworkError,
    operationsState,
    setOperationsState,
    selectedTrain,
    setSelectedTrain,
    selectedStationInspection,
    setSelectedStationInspection,
    setActiveScenario,
    hoveredStation,
    selectedStation,
    setHoveredStation,
    setSelectedStation,
  } = useStore();

  const [simRunning, setSimRunning] = useState<boolean>(false);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(1.0);

  // Acceptance Demo Runner state
  const [demoStep, setDemoStep] = useState<number>(0);
  const [demoRunning, setDemoRunning] = useState<boolean>(false);
  const [demoLogs, setDemoLogs] = useState<string[]>([]);
  const [demoBaselineRoute, setDemoBaselineRoute] = useState<DynamicRouteCompareResponse | null>(null);
  const [demoDisruptedRoute, setDemoDisruptedRoute] = useState<DynamicRouteCompareResponse | null>(null);
  const [demoResilience, setDemoResilience] = useState<ResilienceMetricsResponse | null>(null);

  const tickIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);


  // 1. Fetch initial network topology
  useEffect(() => {
    if (!network) {
      setNetworkLoading(true);
      fetchNetwork()
        .then(setNetwork)
        .catch((e) => setNetworkError(e.message));
    }
  }, [network, setNetwork, setNetworkLoading, setNetworkError]);

  const selectedTrainRef = useRef(selectedTrain);
  useEffect(() => {
    selectedTrainRef.current = selectedTrain;
  }, [selectedTrain]);

  // 2. Poll / Refresh operations state
  const refreshOpsState = useCallback(async () => {
    try {
      const ops = await fetchOperationsState();
      setOperationsState(ops);
      setSimRunning(ops.clock.is_running);
      setSpeedMultiplier(ops.clock.speed_multiplier);
      setActiveScenario(ops.active_scenario);

      if (selectedTrainRef.current) {
        const updated = ops.trains.find((t) => t.train_id === selectedTrainRef.current?.train_id);
        if (updated) setSelectedTrain(updated);
      }
    } catch (err) {
      console.error("Failed to fetch operations state:", err);
    }
  }, [setOperationsState, setActiveScenario, setSelectedTrain]);

  useEffect(() => {
    refreshOpsState();
  }, [refreshOpsState]);

  // 3. Ticking loop when simulation is playing
  useEffect(() => {
    if (simRunning) {
      tickIntervalRef.current = setInterval(async () => {
        try {
          const ops = await tickOperationsSimulation(1.0);
          setOperationsState(ops);
          setSimRunning(ops.clock.is_running);
          setSpeedMultiplier(ops.clock.speed_multiplier);
          if (selectedTrainRef.current) {
            const updated = ops.trains.find((t) => t.train_id === selectedTrainRef.current?.train_id);
            if (updated) setSelectedTrain(updated);
          }
        } catch (err) {
          console.error("Failed simulation tick:", err);
        }
      }, 1000 / speedMultiplier);
    } else {
      if (tickIntervalRef.current) clearInterval(tickIntervalRef.current);
    }

    return () => {
      if (tickIntervalRef.current) clearInterval(tickIntervalRef.current);
    };
  }, [simRunning, speedMultiplier, setOperationsState, setSelectedTrain]);

  // Clock Control Handlers
  const handlePlay = async () => {
    try {
      const ops = await startOperationsSimulation();
      setOperationsState(ops);
      setSimRunning(ops.clock.is_running);
      setSpeedMultiplier(ops.clock.speed_multiplier);
    } catch (err) {
      console.error("Failed to start simulation:", err);
    }
  };

  const handlePause = async () => {
    try {
      const ops = await pauseOperationsSimulation();
      setOperationsState(ops);
      setSimRunning(ops.clock.is_running);
    } catch (err) {
      console.error("Failed to pause simulation:", err);
    }
  };

  const handleReset = async () => {
    try {
      const ops = await resetOperationsSimulation();
      setOperationsState(ops);
      setSimRunning(ops.clock.is_running);
      setSpeedMultiplier(ops.clock.speed_multiplier);
      setSelectedTrain(null);
      setSelectedStationInspection(null);
    } catch (err) {
      console.error("Failed to reset simulation:", err);
    }
  };

  const handleSpeedChange = async (speed: number) => {
    try {
      const ops = await setOperationsSimulationSpeed(speed);
      setOperationsState(ops);
      setSpeedMultiplier(ops.clock.speed_multiplier);
    } catch (err) {
      console.error("Failed to change speed:", err);
    }
  };


  // Train Inspection Handler
  const handleTrainClick = useCallback(
    (trainId: string) => {
      if (operationsState) {
        const t = operationsState.trains.find((item) => item.train_id === trainId);
        if (t) {
          setSelectedTrain(t);
          setSelectedStationInspection(null);
        }
      }
    },
    [operationsState, setSelectedTrain, setSelectedStationInspection]
  );

  // Station Inspection Handler
  const handleStationClick = useCallback(
    async (stId: string, stName: string) => {
      setSelectedStation(stId === selectedStation ? null : stId);
      setSelectedTrain(null);
      try {
        const inspection = await fetchStationInspection(stName);
        setSelectedStationInspection(inspection);
      } catch (_) {
      }
    },
    [selectedStation, setSelectedStation, setSelectedTrain, setSelectedStationInspection]
  );


  // Hold / Release Operator Actions
  const handleHoldTrain = async (trainId: string) => {
    await holdTrain(trainId);
    refreshOpsState();
  };

  const handleReleaseTrain = async (trainId: string) => {
    await releaseTrain(trainId);
    refreshOpsState();
  };

  // Acceptance Workflow Demo Runner
  const runAcceptanceWorkflow = async () => {
    setDemoRunning(true);
    setDemoStep(1);
    setDemoLogs(["🚀 STARTING ACCEPTANCE DEMO WORKFLOW..."]);

    try {
      // Step 1: Start Simulation
      setDemoLogs((prev) => [...prev, "[Step 1] Starting Simulation Clock at 08:00:00 AM"]);
      await handlePlay();
      await new Promise((r) => setTimeout(r, 1200));

      // Step 2: Tick Simulation & Observe Moving Trains
      setDemoStep(2);
      setDemoLogs((prev) => [...prev, "[Step 2] Ticking Simulation Engine (5x Speed) — Trains Moving along Line Geometry"]);
      await handleSpeedChange(5.0);
      await tickOperationsSimulation(30.0);
      await refreshOpsState();
      await new Promise((r) => setTimeout(r, 1500));

      // Step 3: Inspect First Train
      setDemoStep(3);
      if (operationsState && operationsState.trains.length > 0) {
        const t = operationsState.trains[0];
        setSelectedTrain(t);
        setDemoLogs((prev) => [...prev, `[Step 3] Inspected Train ${t.train_id} (${t.line} Line: ${t.current_station} → ${t.next_station})`]);
      }
      await new Promise((r) => setTimeout(r, 1500));

      // Step 4: Operator Hold Train
      setDemoStep(4);
      if (operationsState && operationsState.trains.length > 0) {
        const tId = operationsState.trains[0].train_id;
        setDemoLogs((prev) => [...prev, `[Step 4] Executing SIMULATION CONTROL: HOLD TRAIN ${tId}`]);
        await handleHoldTrain(tId);
        await new Promise((r) => setTimeout(r, 1500));

        // Step 5: Operator Release Train
        setDemoStep(5);
        setDemoLogs((prev) => [...prev, `[Step 5] Executing SIMULATION CONTROL: RELEASE TRAIN ${tId}`]);
        await handleReleaseTrain(tId);
        await new Promise((r) => setTimeout(r, 1200));
      }

      // Step 6: Inspect Station (Majestic)
      setDemoStep(6);
      setDemoLogs((prev) => [...prev, "[Step 6] Inspecting Station 'Kempegowda Stn., Majestic'"]);
      await handleStationClick("HUB_MAJESTIC", "Kempegowda Stn., Majestic");
      await new Promise((r) => setTimeout(r, 1500));

      // Step 7: Request Baseline Route
      setDemoStep(7);
      setDemoLogs((prev) => [...prev, "[Step 7] Calculating Phase 4 Baseline Route: Whitefield → Silk Institute"]);
      const baseRoute = await fetchRouteComparison("Whitefield (Kadugodi)", "Silk Institute", "BALANCED");
      setDemoBaselineRoute(baseRoute);

      // Step 8: Activate Majestic Closure
      setDemoStep(8);
      setDemoLogs((prev) => [...prev, "[Step 8] Activating Disruption Scenario: Majestic Station Closure"]);
      await activateSimulationScenario("majestic_closure");
      await refreshOpsState();
      await new Promise((r) => setTimeout(r, 1500));

      // Step 9: Recalculate Disrupted Route & Resilience
      setDemoStep(9);
      setDemoLogs((prev) => [...prev, "[Step 9] Phase 4 Dynamic Rerouting & Phase 5 Resilience Evaluation Response"]);
      const disRoute = await fetchRouteComparison("Whitefield (Kadugodi)", "Silk Institute", "BALANCED");
      setDemoDisruptedRoute(disRoute);
      const resMetrics = await fetchNetworkResilience("majestic_closure", 50, "BALANCED");
      setDemoResilience(resMetrics);
      await new Promise((r) => setTimeout(r, 2000));

      // Step 10: Deactivate Scenario & Restore Normal State
      setDemoStep(10);
      setDemoLogs((prev) => [...prev, "[Step 10] Deactivating Scenario — Exact Base Network State Restored"]);
      await deactivateSimulationScenario("majestic_closure");
      await refreshOpsState();
      await handleSpeedChange(1.0);

      setDemoLogs((prev) => [...prev, "🎉 ACCEPTANCE WORKFLOW COMPLETED SUCCESSFULLY!"]);
    } catch (e: unknown) {
      setDemoLogs((prev) => [...prev, `❌ Acceptance Error: ${(e as Error).message}`]);
    } finally {
      setDemoRunning(false);
    }
  };

  const ops = operationsState;

  return (
    <div className="flex flex-col min-h-[calc(100vh-53px)] bg-dark-bg text-cream">
      {/* ── Top OCC Header ────────────────────────────────────────── */}
      <header className="px-6 py-4 border-b border-dark-border bg-dark-surface/60 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="badge-real text-[9px]">SIMULATED OPERATIONS CONTROL CENTER</span>
            <span className="text-cream/40 text-xs font-data">BMRCL CANONICAL TOPOLOGY</span>
          </div>
          <h1 className="font-heading text-2xl tracking-tight text-cream uppercase">
            NAMMA PULSE — METRO OPERATIONS CONTROL CENTER
          </h1>
        </div>

        {/* Dynamic Network Status Badge */}
        <div className="flex items-center gap-3 bg-dark-card border border-dark-border px-4 py-2 rounded-lg">
          <div className={`w-3.5 h-3.5 rounded-full ${
            ops?.network_status === "CRITICAL" ? "bg-rust animate-pulse" :
            ops?.network_status === "DISRUPTED" ? "bg-amber-500 animate-pulse" :
            ops?.network_status === "DEGRADED" ? "bg-mustard animate-pulse-soft" : "bg-green-400 animate-pulse-soft"
          }`} />
          <div>
            <div className="text-[10px] font-data text-cream/40 uppercase tracking-widest">Network Operation Status</div>
            <div className="text-sm font-data font-bold text-cream">
              {ops?.network_status_badge ?? "🟢 NORMAL"}
            </div>
          </div>
        </div>
      </header>

      {/* ── Simulation Clock & Control Toolbar ────────────────────── */}
      <div className="px-6 py-3 bg-dark-card border-b border-dark-border flex flex-wrap items-center justify-between gap-4 font-data">
        {/* Clock Display */}
        <div className="flex items-center gap-4">
          <div className="bg-dark-surface border border-mustard/40 px-4 py-2 rounded font-mono text-xl font-bold text-mustard tracking-wider shadow-inner">
            🕒 {ops?.clock.formatted_time ?? "08:00:00"}
          </div>
          <div>
            <div className="text-[10px] text-cream/40 uppercase">Clock Status</div>
            <div className="text-xs font-bold">
              {simRunning ? <span className="text-green-400">● RUNNING ({speedMultiplier}x)</span> : <span className="text-cream/50">⏸ PAUSED</span>}
            </div>
          </div>
        </div>

        {/* Clock Actions */}
        <div className="flex items-center gap-2">
          {!simRunning ? (
            <button
              onClick={handlePlay}
              className="px-4 py-2 bg-green-600 hover:bg-green-500 text-cream text-xs font-bold uppercase rounded shadow transition-all flex items-center gap-1.5"
            >
              ▶ PLAY
            </button>
          ) : (
            <button
              onClick={handlePause}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-cream text-xs font-bold uppercase rounded shadow transition-all flex items-center gap-1.5"
            >
              ⏸ PAUSE
            </button>
          )}

          <button
            onClick={handleReset}
            className="px-3 py-2 bg-dark-surface hover:bg-dark-border text-cream/70 text-xs font-bold uppercase rounded border border-dark-border transition-all"
          >
            ↺ RESET
          </button>

          {/* Speed Multipliers */}
          <div className="flex items-center gap-1 bg-dark-surface p-1 rounded border border-dark-border ml-2">
            <span className="text-[10px] text-cream/40 px-1.5 uppercase">Speed:</span>
            {[1.0, 2.0, 5.0, 10.0].map((spd) => (
              <button
                key={spd}
                onClick={() => handleSpeedChange(spd)}
                className={`px-2 py-0.5 text-xs font-bold rounded ${
                  speedMultiplier === spd ? "bg-mustard text-dark-bg" : "text-cream/60 hover:text-cream"
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Dynamic Operations KPI Cards ───────────────────────────── */}
      <div className="px-6 py-4 grid grid-cols-2 md:grid-cols-6 gap-3 font-data text-center">
        <div className="bg-dark-card border border-dark-border rounded-lg p-3">
          <div className="text-cream/40 text-[10px] uppercase tracking-wider">Total Active Trains</div>
          <div className="text-cream text-2xl font-bold mt-0.5">{ops?.kpis.total_trains ?? 0}</div>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-lg p-3">
          <div className="text-cream/40 text-[10px] uppercase tracking-wider">On Time</div>
          <div className="text-green-400 text-2xl font-bold mt-0.5">{ops?.kpis.on_time ?? 0}</div>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-lg p-3">
          <div className="text-cream/40 text-[10px] uppercase tracking-wider">Delayed Services</div>
          <div className="text-mustard text-2xl font-bold mt-0.5">{ops?.kpis.delayed ?? 0}</div>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-lg p-3">
          <div className="text-cream/40 text-[10px] uppercase tracking-wider">Stopped / Held</div>
          <div className="text-rust text-2xl font-bold mt-0.5">{ops?.kpis.stopped ?? 0}</div>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-lg p-3">
          <div className="text-cream/40 text-[10px] uppercase tracking-wider">Active Incidents</div>
          <div className="text-cream text-2xl font-bold mt-0.5">{ops?.kpis.active_incidents ?? 0}</div>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-lg p-3">
          <div className="text-cream/40 text-[10px] uppercase tracking-wider">High Congestion</div>
          <div className="text-amber-400 text-2xl font-bold mt-0.5">{ops?.kpis.high_congestion_areas ?? 0}</div>
        </div>
      </div>

      {/* ── Main OCC Control Room Grid ────────────────────────────── */}
      <div className="flex-1 px-6 pb-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Metro Map with Moving Trains */}
        <div className="lg:col-span-8 flex flex-col space-y-4">
          <div className="bg-dark-card border border-dark-border rounded-lg p-4 flex-1 flex flex-col min-h-[460px] relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="text-xs font-data text-cream/50 uppercase tracking-widest">
                  Live Operations Map Overlay
                </span>
                <p className="text-[10px] text-cream/40 font-body">
                  Moving train positions derived deterministically from backend state
                </p>
              </div>
              <div className="text-[10px] font-data text-cream/40">
                Click any train marker or station node to inspect
              </div>
            </div>

            {network && (
              <div className="flex-1 relative rounded overflow-hidden border border-dark-border/40 min-h-[400px]">
                <MetroMap
                  network={network}
                  route={null}
                  trains={ops?.trains}
                  selectedTrainId={selectedTrain?.train_id}
                  hoveredStation={hoveredStation}
                  selectedStation={selectedStation}
                  onStationClick={handleStationClick}
                  onTrainClick={handleTrainClick}
                  onStationHover={setHoveredStation}
                  className="absolute inset-0"
                />
              </div>
            )}
          </div>

          {/* 1-Click Acceptance Workflow Runner */}
          <div className="bg-dark-card border border-mustard/40 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-dark-border/60 pb-2">
              <div>
                <span className="badge-synthetic text-[9px]">ACCEPTANCE TEST SUITE</span>
                <h3 className="font-heading text-sm text-cream uppercase">Full OCC Operations Acceptance Workflow</h3>
              </div>
              <button
                onClick={runAcceptanceWorkflow}
                disabled={demoRunning}
                className="px-4 py-2 bg-rust hover:bg-rust/80 text-cream text-xs font-data font-bold uppercase rounded shadow transition-all"
              >
                {demoRunning ? "RUNNING ACCEPTANCE..." : "EXECUTE FULL ACCEPTANCE DEMO"}
              </button>
            </div>

            {/* Workflow Step Indicator */}
            <div className="grid grid-cols-5 md:grid-cols-10 gap-1 text-center font-data text-[9px]">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((step) => (
                <div
                  key={step}
                  className={`p-1 rounded border ${
                    demoStep >= step ? "bg-mustard/20 text-mustard border-mustard" : "bg-dark-surface text-cream/30 border-dark-border"
                  }`}
                >
                  Step {step}
                </div>
              ))}
            </div>

            {/* Demo Outputs Comparison */}
            {demoBaselineRoute && demoDisruptedRoute && (
              <div className="grid grid-cols-2 gap-3 bg-dark-surface p-3 rounded border border-dark-border/60 text-xs font-data">
                <div>
                  <div className="text-cream/40 text-[9px] uppercase">Baseline Route</div>
                  <div className="text-cream font-bold mt-0.5">
                    {demoBaselineRoute.recommended.predicted_travel_time?.toFixed(1) || demoBaselineRoute.recommended.total_time_min} min
                  </div>
                  <div className="text-cream/60 text-[10px]">{demoBaselineRoute.recommended.interchange_count} transfer(s)</div>
                </div>
                <div>
                  <div className="text-cream/40 text-[9px] uppercase">Rerouted & Resilience Evaluation</div>
                  <div className="text-mustard font-bold mt-0.5">
                    {demoDisruptedRoute.recommended.predicted_travel_time?.toFixed(1) || demoDisruptedRoute.recommended.total_time_min} min
                  </div>
                  <div className="text-rust text-[10px] font-bold">
                    Resilience Score: {demoResilience?.resilience_score} / 100
                  </div>
                </div>
              </div>
            )}

            {/* Console Log */}
            {demoLogs.length > 0 && (
              <div className="bg-black/70 p-2.5 rounded font-mono text-[11px] text-green-400 space-y-1 max-h-28 overflow-y-auto border border-dark-border/40">
                {demoLogs.map((log, idx) => (
                  <div key={idx}>{log}</div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Inspection Panels & Live Alert Feed */}
        <div className="lg:col-span-4 space-y-4">
          {/* 1. Selected Train Inspection Panel */}
          {selectedTrain ? (
            <section className="bg-dark-card border border-mustard rounded-lg p-4 space-y-3 animate-fade-in">
              <div className="flex items-center justify-between border-b border-dark-border/60 pb-2">
                <span className="text-xs font-data text-mustard font-bold uppercase tracking-widest">
                  TRAIN INSPECTION PANEL
                </span>
                <button
                  onClick={() => setSelectedTrain(null)}
                  className="text-cream/40 hover:text-cream text-xs font-bold"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-2 font-data text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-heading text-lg text-cream">{selectedTrain.train_id}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    selectedTrain.status === "ON_TIME" ? "bg-green-500/20 text-green-400" :
                    selectedTrain.status === "STOPPED" ? "bg-rust/20 text-rust" : "bg-mustard/20 text-mustard"
                  }`}>
                    {selectedTrain.status}
                  </span>
                </div>

                <div className="bg-dark-surface p-2.5 rounded space-y-1">
                  <div className="text-cream/60">Line: <span className="text-cream font-bold">{selectedTrain.line} Line</span></div>
                  <div className="text-cream/60">Route: <span className="text-cream font-bold">{selectedTrain.origin_station} → {selectedTrain.destination_station}</span></div>
                  <div className="text-cream/60">Current Station: <span className="text-mustard font-bold">{selectedTrain.current_station}</span></div>
                  <div className="text-cream/60">Next Stop: <span className="text-cream font-bold">{selectedTrain.next_station}</span></div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="bg-dark-surface p-2 rounded">
                    <div className="text-cream/40 text-[9px] uppercase">Scheduled Arrival</div>
                    <div className="text-cream font-mono font-bold mt-0.5">{selectedTrain.scheduled_arrival_next}</div>
                  </div>
                  <div className="bg-dark-surface p-2 rounded">
                    <div className="text-cream/40 text-[9px] uppercase">Expected Arrival</div>
                    <div className="text-mustard font-mono font-bold mt-0.5">{selectedTrain.expected_arrival_next}</div>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-1 pt-1">
                  <div className="flex justify-between text-[10px] text-cream/50">
                    <span>Segment Progress</span>
                    <span>{Math.round(selectedTrain.progress_pct * 100)}%</span>
                  </div>
                  <div className="w-full bg-dark-surface h-2 rounded-full overflow-hidden border border-dark-border">
                    <div className="bg-mustard h-full transition-all duration-300" style={{ width: `${selectedTrain.progress_pct * 100}%` }} />
                  </div>
                </div>

                {/* Operator Actions */}
                <div className="pt-2 space-y-1.5">
                  <div className="text-[10px] text-cream/40 uppercase tracking-widest">SIMULATION CONTROL ACTIONS</div>
                  <div className="flex gap-2">
                    {!selectedTrain.is_held ? (
                      <button
                        onClick={() => handleHoldTrain(selectedTrain.train_id)}
                        className="flex-1 py-2 bg-rust hover:bg-rust/80 text-cream font-bold rounded text-xs uppercase shadow"
                      >
                        ✋ HOLD TRAIN
                      </button>
                    ) : (
                      <button
                        onClick={() => handleReleaseTrain(selectedTrain.train_id)}
                        className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-cream font-bold rounded text-xs uppercase shadow"
                      >
                        ▶ RELEASE TRAIN
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </section>
          ) : selectedStationInspection ? (
            /* 2. Selected Station Inspection Panel */
            <section className="bg-dark-card border border-mustard rounded-lg p-4 space-y-3 animate-fade-in">
              <div className="flex items-center justify-between border-b border-dark-border/60 pb-2">
                <span className="text-xs font-data text-mustard font-bold uppercase tracking-widest">
                  STATION INSPECTION
                </span>
                <button
                  onClick={() => setSelectedStationInspection(null)}
                  className="text-cream/40 hover:text-cream text-xs font-bold"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-2 font-data text-xs">
                <div className="font-heading text-lg text-cream">{selectedStationInspection.station_name}</div>

                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="bg-dark-surface p-2 rounded">
                    <div className="text-cream/40 text-[9px] uppercase">Current Congestion</div>
                    <div className="text-mustard font-bold text-base mt-0.5">{selectedStationInspection.current_congestion_pct}%</div>
                  </div>
                  <div className="bg-dark-surface p-2 rounded">
                    <div className="text-cream/40 text-[9px] uppercase">Predicted (15m)</div>
                    <div className="text-rust font-bold text-base mt-0.5">{selectedStationInspection.predicted_congestion_15min_pct}%</div>
                  </div>
                </div>

                <div className="bg-dark-surface p-2.5 rounded space-y-1">
                  <div className="text-cream/60">Platform Demand: <span className="text-cream font-bold">{selectedStationInspection.platform_demand}</span></div>
                  <div className="text-cream/60">Next Train ETA: <span className="text-green-400 font-mono font-bold">{selectedStationInspection.next_train_eta}</span></div>
                  <div className="text-cream/60">Active Incidents: <span className="text-rust font-bold">{selectedStationInspection.active_incidents.length > 0 ? selectedStationInspection.active_incidents.join(", ") : "None"}</span></div>
                </div>

                <div className="text-[10px] text-cream/40 italic">
                  Data Source: SYNTHETIC & SYNTHETIC MODEL OUTPUT
                </div>
              </div>
            </section>
          ) : (
            <div className="bg-dark-card/50 border border-dark-border rounded-lg p-5 text-center text-cream/40 text-xs font-body">
              Click any train marker or station node to inspect real-time operational state.
            </div>
          )}

          {/* 3. Operational Alert Engine Feed */}
          <section className="bg-dark-card border border-dark-border rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-dark-border/60 pb-2">
              <span className="text-xs font-data text-cream/50 uppercase tracking-widest">
                Control Room Alert Feed
              </span>
              <span className="badge-synthetic text-[9px]">LIVE ENGINE</span>
            </div>

            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {ops?.alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-2.5 rounded border text-xs font-data space-y-0.5 ${
                    alert.severity === "CRITICAL" ? "bg-rust/20 border-rust/60 text-cream" :
                    alert.severity === "CONGESTION" ? "bg-amber-500/20 border-amber-500/50 text-cream" :
                    alert.severity === "WARNING" ? "bg-mustard/20 border-mustard/50 text-cream" : "bg-dark-surface border-dark-border text-cream/80"
                  }`}
                >
                  <div className="flex items-center justify-between font-bold">
                    <span>{alert.icon} {alert.title}</span>
                    <span className="text-[9px] text-cream/40">{alert.timestamp}</span>
                  </div>
                  <p className="text-[11px] text-cream/70 font-body">{alert.message}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default CommandCenterPage;

/**
 * SimulationPage.tsx — Phase 5 Disruption Simulation & Network Resilience Page.
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  fetchNetwork,
  fetchSimulationScenarios,
  fetchSimulationState,
  activateSimulationScenario,
  activateCustomScenario,
  deactivateSimulationScenario,
  resetSimulation,
  fetchRouteImpact,
  fetchNetworkResilience,
} from "../services/api";
import { useStore } from "../store/useStore";
import MetroMap from "../components/MetroMap/MetroMap";
import StationSearch from "../components/StationSearch/StationSearch";
import type {
  ScenarioOut,
  RouteImpactResponse,
  ResilienceMetricsResponse,
  RouteResponse,
} from "../types";

const SimulationPage: React.FC = () => {
  const {
    network, setNetwork, setNetworkLoading, setNetworkError,
    origin, destination, setOrigin, setDestination,
    hoveredStation, selectedStation, setHoveredStation, setSelectedStation,
  } = useStore();

  const [scenarios, setScenarios] = useState<ScenarioOut[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("expanded_5_line");
  const [activeScenario, setActiveScenario] = useState<ScenarioOut | null>(null);

  const [sampleSize, setSampleSize] = useState<number>(50);
  const [impactResult, setImpactResult] = useState<RouteImpactResponse | null>(null);
  const [resilienceMetrics, setResilienceMetrics] = useState<ResilienceMetricsResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Custom Scenario Builder state
  const [showCustomBuilder, setShowCustomBuilder] = useState<boolean>(false);
  const [customName, setCustomName] = useState<string>("Custom Network Scenario");
  const [customLines, setCustomLines] = useState<Record<string, boolean>>({
    Purple: true,
    Green: true,
    Yellow: true,
    Pink: true,
    Blue: true,
  });
  const [customHeadway, setCustomHeadway] = useState<number>(360);
  const [customDemandMult, setCustomDemandMult] = useState<number>(1.0);

  // Warning Modal state (Requirement 4)
  const [warningModalMessage, setWarningModalMessage] = useState<string | null>(null);

  // Load network topology
  useEffect(() => {
    if (!network) {
      setNetworkLoading(true);
      fetchNetwork()
        .then(setNetwork)
        .catch((e) => setNetworkError(e.message));
    }
  }, [network, setNetwork, setNetworkLoading, setNetworkError]);

  // Load available scenarios & initial active state
  const refreshSimulationData = useCallback(async () => {
    try {
      const [scList, stState] = await Promise.all([
        fetchSimulationScenarios(),
        fetchSimulationState(),
      ]);
      setScenarios(scList);
      setActiveScenario(stState.active_scenario);
      if (stState.active_scenario) {
        setSelectedScenarioId(stState.active_scenario.id);
      }
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refreshSimulationData();
  }, [refreshSimulationData]);

  // Set default sample OD pair if empty
  useEffect(() => {
    if (!origin) setOrigin("Whitefield (Kadugodi)");
    if (!destination) setDestination("Silk Institute");
  }, [origin, destination, setOrigin, setDestination]);

  // Run impact & resilience evaluations
  const runEvaluation = useCallback(async (scenarioId: string, sz: number) => {
    if (!origin || !destination) return;
    setLoading(true);
    setError(null);
    try {
      const [imp, res] = await Promise.all([
        fetchRouteImpact(origin, destination, "BALANCED", scenarioId),
        fetchNetworkResilience(scenarioId, sz, "BALANCED"),
      ]);
      setImpactResult(imp);
      setResilienceMetrics(res);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [origin, destination]);

  useEffect(() => {
    if (selectedScenarioId) {
      runEvaluation(selectedScenarioId, sampleSize);
    }
  }, [selectedScenarioId, sampleSize, origin, destination, runEvaluation]);

  // Handle scenario activation / deactivation
  const handleToggleScenario = async () => {
    if (!selectedScenarioId) return;
    setLoading(true);
    setError(null);
    try {
      if (activeScenario && activeScenario.id === selectedScenarioId) {
        await deactivateSimulationScenario(selectedScenarioId);
      } else {
        await activateSimulationScenario(selectedScenarioId);
      }
      await refreshSimulationData();
      await fetchNetwork().then(setNetwork);
      await runEvaluation(selectedScenarioId, sampleSize);
    } catch (e: unknown) {
      const msg = (e as Error).message;
      if (msg.includes("At least one metro line")) {
        setWarningModalMessage(msg);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle Custom Scenario activation with Zero Active Lines Validation
  const handleApplyCustomScenario = async () => {
    const selectedActiveLines = Object.keys(customLines).filter((k) => customLines[k]);
    if (selectedActiveLines.length === 0) {
      // Requirement 4: Frontend warning modal for zero active lines
      setWarningModalMessage("At least one metro line must remain active in the simulation.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await activateCustomScenario({
        name: customName,
        active_lines: selectedActiveLines,
        headway_sec: customHeadway,
        demand_multiplier: customDemandMult,
      });
      setShowCustomBuilder(false);
      await refreshSimulationData();
      await fetchNetwork().then(setNetwork);
      if (selectedScenarioId) await runEvaluation(selectedScenarioId, sampleSize);
    } catch (e: unknown) {
      const msg = (e as Error).message;
      if (msg.includes("At least one metro line")) {
        setWarningModalMessage(msg);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle Full Atomic Reset (Requirement 5)
  const handleResetSimulationState = async () => {
    setLoading(true);
    setError(null);
    try {
      await resetSimulation();
      setSelectedScenarioId("current_operations");
      await refreshSimulationData();
      await fetchNetwork().then(setNetwork);
      await runEvaluation("current_operations", sampleSize);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const currentSc = scenarios.find((s) => s.id === selectedScenarioId);
  const isActive = activeScenario !== null && activeScenario.id === selectedScenarioId;

  // Selected map route to highlight
  const displayRoute: RouteResponse | null = impactResult
    ? (impactResult.disrupted_route || impactResult.baseline_route)
    : null;

  return (
    <div className="flex h-[calc(100vh-53px)] relative">
      {/* ── All-Lines-Off Warning Modal (Requirement 4) ──────────── */}
      {warningModalMessage && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-dark-card border-2 border-rust rounded-xl max-w-md w-full p-6 space-y-4 text-center shadow-2xl">
            <div className="w-14 h-14 bg-rust/20 border border-rust text-rust rounded-full flex items-center justify-center text-3xl mx-auto font-bold">
              ⚠️
            </div>
            <div>
              <h2 className="font-heading text-lg text-cream uppercase tracking-tight">
                Invalid Scenario Configuration
              </h2>
              <p className="text-cream/80 text-xs font-body leading-relaxed mt-2 bg-dark-surface p-3 rounded border border-dark-border">
                {warningModalMessage}
              </p>
            </div>
            <p className="text-[10px] text-cream/40 font-data">
              The OCC controller safety protocol requires at least one operational line to run simulation routes.
            </p>
            <button
              onClick={() => setWarningModalMessage(null)}
              className="w-full py-2.5 bg-rust hover:bg-rust/80 text-cream font-data font-bold text-xs uppercase rounded transition-all shadow-lg"
            >
              OK, UNDERSTOOD
            </button>
          </div>
        </div>
      )}

      {/* ── Left Sidebar Control Panel ──────────────────────────── */}
      <aside className="w-96 flex-shrink-0 border-r border-dark-border overflow-y-auto flex flex-col bg-dark-bg">
        {/* Header */}
        <div className="p-5 border-b border-dark-border">
          <div className="badge-synthetic text-[9px] mb-1">NETWORK SCENARIO CONTROLLER</div>
          <h1 className="section-title text-lg tracking-tight">DISRUPTION & RESILIENCE</h1>
          <p className="text-cream/40 text-xs font-body mt-0.5">
            Backend-Authoritative Line Activation & Dynamic Routing
          </p>
        </div>

        <div className="p-5 space-y-4 flex-1">
          {/* 1. Scenario Selector & Controls */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-data text-cream/50 uppercase tracking-widest">
                Select Disruption Scenario
              </label>
              <button
                onClick={handleResetSimulationState}
                className="text-[10px] font-data text-mustard hover:underline uppercase"
              >
                ↺ RESET
              </button>
            </div>

            <select
              value={selectedScenarioId}
              onChange={(e) => setSelectedScenarioId(e.target.value)}
              className="w-full bg-dark-surface border border-dark-border text-cream text-xs rounded-md p-2.5 font-body focus:outline-none focus:border-mustard"
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.severity})
                </option>
              ))}
            </select>

            {currentSc && (
              <div className="bg-dark-surface p-3 rounded-md border border-dark-border space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-data font-bold text-cream uppercase">{currentSc.type}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold font-data ${
                      currentSc.severity === "CRITICAL"
                        ? "bg-rust/20 text-rust"
                        : currentSc.severity === "HIGH"
                        ? "bg-mustard/20 text-mustard"
                        : "bg-green-500/20 text-green-400"
                    }`}
                  >
                    {currentSc.severity}
                  </span>
                </div>
                <p className="text-cream/70 font-body leading-relaxed">{currentSc.description}</p>
                <div className="text-cream/40 font-data text-[10px] space-y-0.5">
                  <div>Target: {currentSc.target}</div>
                  <div>
                    Active Lines: {currentSc.active_lines ? currentSc.active_lines.join(", ") : "Purple, Green, Yellow"}
                  </div>
                  <div>
                    Headway: {currentSc.headway_sec ?? 360}s | Demand Mult: {currentSc.demand_multiplier ?? 1.0}x
                  </div>
                </div>
              </div>
            )}

            {/* Line Status Badges (Requirement 6) */}
            <div className="bg-dark-card p-2.5 rounded border border-dark-border text-[11px] font-data space-y-1">
              <div className="text-cream/40 text-[9px] uppercase tracking-wider">Line Operational Status</div>
              <div className="flex flex-wrap gap-1.5 pt-0.5">
                {["Purple", "Green", "Yellow"].map((l) => (
                  <span key={l} className="px-2 py-0.5 rounded bg-green-500/15 text-green-400 border border-green-500/30 text-[10px]">
                    {l}: OPERATIONAL
                  </span>
                ))}
                {["Pink", "Blue"].map((l) => {
                  const lineIsActive = activeScenario?.active_lines?.includes(l);
                  return (
                    <span
                      key={l}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        lineIsActive
                          ? "bg-mustard/20 text-mustard border border-mustard/40"
                          : "bg-dark-surface text-cream/40 border border-dark-border"
                      }`}
                    >
                      {l}: {lineIsActive ? "SIMULATED SERVICE" : "UNDER_CONSTRUCTION"}
                    </span>
                  );
                })}
              </div>
            </div>

            {/* Activate / Deactivate Button */}
            <div className="space-y-2">
              <button
                onClick={handleToggleScenario}
                disabled={loading}
                className={`w-full py-2.5 rounded-md text-xs font-data font-bold uppercase tracking-wider transition-all ${
                  isActive
                    ? "bg-rust hover:bg-rust/80 text-cream shadow-lg"
                    : "bg-mustard hover:bg-mustard/80 text-dark-bg font-bold shadow-lg"
                }`}
              >
                {loading
                  ? "Processing…"
                  : isActive
                  ? "DEACTIVATE SCENARIO (Restore Base State)"
                  : "ACTIVATE SCENARIO OVERLAY"}
              </button>

              <button
                onClick={() => setShowCustomBuilder(!showCustomBuilder)}
                className="w-full py-2 rounded-md text-xs font-data border border-dark-border bg-dark-surface hover:bg-dark-card text-cream/80 uppercase"
              >
                {showCustomBuilder ? "Hide Custom Builder" : "+ Custom Scenario Builder"}
              </button>
            </div>

            {/* Custom Scenario Builder Modal/Panel */}
            {showCustomBuilder && (
              <div className="bg-dark-card p-3 rounded-md border border-mustard/50 space-y-3 animate-fade-in text-xs font-data">
                <div className="text-mustard font-bold uppercase text-[11px]">Build Custom Scenario</div>
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="Scenario Name"
                  className="w-full bg-dark-surface border border-dark-border p-2 rounded text-cream"
                />
                <div>
                  <div className="text-cream/50 text-[10px] uppercase mb-1">Active Metro Lines:</div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {["Purple", "Green", "Yellow", "Pink", "Blue"].map((l) => (
                      <label key={l} className="flex items-center gap-1.5 cursor-pointer text-cream/80">
                        <input
                          type="checkbox"
                          checked={customLines[l] ?? false}
                          onChange={(e) =>
                            setCustomLines({ ...customLines, [l]: e.target.checked })
                          }
                          className="accent-mustard"
                        />
                        <span>{l} Line</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-cream/50 text-[10px] uppercase">Headway (sec):</label>
                    <input
                      type="number"
                      value={customHeadway}
                      onChange={(e) => setCustomHeadway(Number(e.target.value))}
                      className="w-full bg-dark-surface border border-dark-border p-1.5 rounded text-cream mt-0.5"
                    />
                  </div>
                  <div>
                    <label className="text-cream/50 text-[10px] uppercase">Demand Mult:</label>
                    <input
                      type="number"
                      step="0.1"
                      value={customDemandMult}
                      onChange={(e) => setCustomDemandMult(Number(e.target.value))}
                      className="w-full bg-dark-surface border border-dark-border p-1.5 rounded text-cream mt-0.5"
                    />
                  </div>
                </div>

                <button
                  onClick={handleApplyCustomScenario}
                  className="w-full py-2 bg-green-600 hover:bg-green-500 text-cream font-bold uppercase rounded text-xs"
                >
                  APPLY CUSTOM SCENARIO
                </button>
              </div>
            )}
          </div>

          {/* Error display */}
          {error && (
            <div className="bg-red-900/30 border border-red-800/50 rounded-md p-3 text-red-300 text-xs">
              {error}
            </div>
          )}

          {/* 2. Before vs After Route Impact Card */}
          <div className="border-t border-dark-border pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-data text-cream/50 uppercase tracking-widest">
                OD Journey Impact
              </span>
              <span className="text-[10px] font-data text-cream/30">Single Route Delta</span>
            </div>

            <div className="space-y-2">
              <StationSearch
                id="sim-origin"
                label="From"
                value={origin}
                onSelect={setOrigin}
                placeholder="Origin station"
              />
              <StationSearch
                id="sim-destination"
                label="To"
                value={destination}
                onSelect={setDestination}
                placeholder="Destination station"
              />
            </div>

            {impactResult && (
              <div className="bg-dark-card p-3 rounded-md border border-dark-border space-y-2 text-xs">
                {impactResult.unreachable ? (
                  <div className="bg-rust/20 border border-rust/40 rounded p-2 text-rust font-body text-xs">
                    ⚠ JOURNEY UNREACHABLE DURING THIS DISRUPTION
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-2 text-center font-data">
                      <div className="bg-dark-surface p-2 rounded">
                        <div className="text-cream/40 text-[9px] uppercase">Before</div>
                        <div className="text-cream text-base font-bold">
                          {impactResult.baseline_time_min} min
                        </div>
                        <div className="text-cream/40 text-[9px]">
                          {impactResult.baseline_transfers} transfer(s)
                        </div>
                      </div>
                      <div className="bg-dark-surface p-2 rounded">
                        <div className="text-cream/40 text-[9px] uppercase">After</div>
                        <div className="text-mustard text-base font-bold">
                          {impactResult.disrupted_time_min} min
                        </div>
                        <div className="text-cream/40 text-[9px]">
                          {impactResult.disrupted_transfers} transfer(s)
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-xs font-data pt-1 border-t border-dark-border/50">
                      <span className="text-cream/60">Time Delta:</span>
                      <span className={impactResult.travel_time_change_min && impactResult.travel_time_change_min > 0 ? "text-rust font-bold" : "text-green-400 font-bold"}>
                        {impactResult.travel_time_change_min && impactResult.travel_time_change_min > 0 ? `+${impactResult.travel_time_change_min}` : impactResult.travel_time_change_min} min ({impactResult.travel_time_change_pct && impactResult.travel_time_change_pct > 0 ? `+${impactResult.travel_time_change_pct}` : impactResult.travel_time_change_pct}%)
                      </span>
                    </div>

                    <p className="text-[11px] text-cream/70 font-body leading-relaxed bg-dark-surface/50 p-2 rounded border border-dark-border/30">
                      {impactResult.recommendation}
                    </p>
                  </>
                )}
              </div>
            )}
          </div>

          {/* 3. Network Resilience Metrics & Score Card */}
          <div className="border-t border-dark-border pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-data text-cream/50 uppercase tracking-widest">
                Network Resilience
              </span>
              <div className="flex items-center gap-1">
                <span className="text-[10px] font-data text-cream/40">Sample:</span>
                <select
                  value={sampleSize}
                  onChange={(e) => setSampleSize(Number(e.target.value))}
                  className="bg-dark-surface border border-dark-border text-cream text-[10px] rounded px-1 py-0.5 font-data"
                >
                  <option value={50}>50 ODs</option>
                  <option value={100}>100 ODs</option>
                  <option value={200}>200 ODs</option>
                  <option value={500}>500 ODs</option>
                </select>
              </div>
            </div>

            {resilienceMetrics && (
              <div className="bg-dark-card p-3 rounded-md border border-dark-border space-y-3">
                {/* Composite Resilience Score */}
                <div className="flex items-center justify-between p-2.5 bg-dark-surface rounded border border-mustard/30">
                  <div>
                    <div className="font-heading text-sm text-cream uppercase">RESILIENCE SCORE</div>
                    <div className="text-cream/40 text-[9px] font-data">Composite Network Rating</div>
                  </div>
                  <div className="text-right">
                    <span className="font-data text-2xl font-bold text-mustard">
                      {resilienceMetrics.resilience_score}
                    </span>
                    <span className="text-cream/40 text-xs font-data"> / 100</span>
                  </div>
                </div>

                {/* Metrics List */}
                <div className="space-y-1.5 font-data text-xs">
                  <div className="flex justify-between">
                    <span className="text-cream/60">Route Availability:</span>
                    <span className="text-cream font-bold">{resilienceMetrics.route_availability_pct}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-cream/60">Avg Travel-Time Impact:</span>
                    <span className="text-rust font-bold">+{resilienceMetrics.avg_travel_time_impact_pct}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-cream/60">Unreachable OD Rate:</span>
                    <span className="text-cream font-bold">{resilienceMetrics.unreachable_od_rate_pct}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-cream/60">Rerouting Success:</span>
                    <span className="text-green-400 font-bold">{resilienceMetrics.rerouting_success_rate_pct}%</span>
                  </div>
                </div>

                {/* Cascading Congestion Edge List */}
                {resilienceMetrics.cascading_congestion_edges.length > 0 && (
                  <div className="border-t border-dark-border/50 pt-2 space-y-1">
                    <div className="text-[10px] font-data text-cream/40 uppercase">
                      Top Rerouted Edges (Targeted Load)
                    </div>
                    <div className="space-y-1 max-h-24 overflow-y-auto text-[10px] font-data">
                      {resilienceMetrics.cascading_congestion_edges.map((e, idx) => (
                        <div key={idx} className="flex justify-between bg-dark-surface/60 px-2 py-0.5 rounded">
                          <span className="text-cream/70">{e.edge}</span>
                          <span className="text-mustard">+{e.derived_congestion_increase_pct}% cong</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main Map Area ────────────────────────────────────────── */}
      <main className="flex-1 relative overflow-hidden">
        {network && (
          <MetroMap
            network={network}
            route={displayRoute}
            hoveredStation={hoveredStation}
            selectedStation={selectedStation}
            onStationClick={(stId, stName) => {
              if (!origin) setOrigin(stName);
              else if (!destination) setDestination(stName);
              else setSelectedStation(stId === selectedStation ? null : stId);
            }}
            onStationHover={setHoveredStation}
            className="absolute inset-0"
          />
        )}

        {/* Provenance Footer Badge */}
        <div className="absolute bottom-4 right-4 flex flex-col items-end gap-1.5 pointer-events-none z-10">
          <div className="badge-real text-[9px]">NAMMA PULSE — BMRCL Canonical 5-Line Topology</div>
          <div className="badge-synthetic text-[9px]">
            {isActive ? `SIMULATED SCENARIO: ${activeScenario?.name}` : "BASE NETWORK STATE"}
          </div>
        </div>
      </main>
    </div>
  );
};

export default SimulationPage;

/**
 * ResiliencePage.tsx — Dedicated Network Resilience Analysis Page for Namma Pulse.
 * Real backend API calculations & zero hardcoded metrics.
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  fetchSimulationScenarios,
  fetchSimulationState,
  activateSimulationScenario,
  deactivateSimulationScenario,
  fetchNetworkResilience,
} from "../services/api";
import { useStore } from "../store/useStore";
import type { ScenarioOut, ResilienceMetricsResponse } from "../types";

const ResiliencePage: React.FC = () => {
  const { setActiveScenario } = useStore();

  const [scenarios, setScenarios] = useState<ScenarioOut[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("majestic_closure");
  const [activeScenario, setLocalActiveScenario] = useState<ScenarioOut | null>(null);

  const [sampleSize, setSampleSize] = useState<number>(50);
  const [resilienceMetrics, setResilienceMetrics] = useState<ResilienceMetricsResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const refreshData = useCallback(async () => {
    try {
      const [scList, stState] = await Promise.all([
        fetchSimulationScenarios(),
        fetchSimulationState(),
      ]);
      setScenarios(scList);
      setLocalActiveScenario(stState.active_scenario);
      setActiveScenario(stState.active_scenario);
      if (stState.active_scenario) {
        setSelectedScenarioId(stState.active_scenario.id);
      }
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  }, [setActiveScenario]);

  const loadResilienceMetrics = useCallback(async (scId: string, sz: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchNetworkResilience(scId, sz, "BALANCED");
      setResilienceMetrics(res);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  useEffect(() => {
    if (selectedScenarioId) {
      loadResilienceMetrics(selectedScenarioId, sampleSize);
    }
  }, [selectedScenarioId, sampleSize, loadResilienceMetrics]);

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
      await refreshData();
      await loadResilienceMetrics(selectedScenarioId, sampleSize);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const currentSc = scenarios.find((s) => s.id === selectedScenarioId);
  const isActive = activeScenario !== null && activeScenario.id === selectedScenarioId;

  return (
    <div className="flex flex-col min-h-[calc(100vh-53px)] bg-dark-bg text-cream p-6 space-y-6">
      {/* ── Page Header ───────────────────────────────────────────── */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <div className="badge-synthetic text-[9px] mb-1">SIMULATED SCENARIO EVALUATOR</div>
          <h1 className="font-heading text-2xl tracking-tight text-cream">NETWORK RESILIENCE ANALYSIS</h1>
          <p className="text-cream/40 text-xs font-body mt-0.5">
            Representative OD Journey Sampling & Targeted Cascading Congestion Assessment
          </p>
        </div>

        {/* Active Scenario Indicator Banner */}
        <div className="flex items-center gap-3 bg-dark-card border border-dark-border px-4 py-2.5 rounded-lg">
          <div className={`w-3 h-3 rounded-full ${isActive ? "bg-rust animate-pulse" : "bg-green-400 animate-pulse-soft"}`} />
          <div>
            <div className="text-[10px] font-data text-cream/40 uppercase tracking-widest">Scenario Overlay Status</div>
            <div className="text-xs font-data font-bold">
              {isActive ? (
                <span className="text-rust">🚨 SIMULATED SCENARIO ACTIVE: {activeScenario?.name}</span>
              ) : (
                <span className="text-green-400">● Base Network State (No Active Scenario Overlay)</span>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Error state */}
      {error && (
        <div className="bg-red-900/30 border border-red-800/50 rounded-md p-4 text-red-300 text-xs">
          Simulation Error: {error}
        </div>
      )}

      {/* ── Top Controls Grid ────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Left: Scenario Selector & Details Card */}
        <div className="md:col-span-6 bg-dark-card border border-dark-border rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-dark-border/60 pb-2">
            <span className="text-xs font-data text-cream/50 uppercase tracking-widest">Select Disruption Scenario</span>
            <span className="badge-synthetic text-[9px]">8 Scenarios</span>
          </div>

          <div className="space-y-3">
            <select
              value={selectedScenarioId}
              onChange={(e) => setSelectedScenarioId(e.target.value)}
              className="w-full bg-dark-surface border border-dark-border text-cream text-xs rounded-md p-3 font-body focus:outline-none focus:border-mustard"
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.severity})
                </option>
              ))}
            </select>

            {currentSc && (
              <div className="bg-dark-surface p-3.5 rounded border border-dark-border/60 space-y-2 text-xs">
                <div className="flex items-center justify-between font-data">
                  <span className="font-bold text-cream uppercase">{currentSc.name}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    currentSc.severity === "CRITICAL" ? "bg-rust/20 text-rust" : "bg-mustard/20 text-mustard"
                  }`}>
                    {currentSc.severity}
                  </span>
                </div>
                <p className="text-cream/70 font-body leading-relaxed">{currentSc.description}</p>
                <div className="text-cream/40 font-data text-[10px]">
                  Disruption Target: {currentSc.target} | Duration: {currentSc.duration_min} min
                </div>
              </div>
            )}

            <button
              onClick={handleToggleScenario}
              disabled={loading}
              className={`w-full py-3 rounded-md text-xs font-data font-bold uppercase tracking-wider transition-all ${
                isActive
                  ? "bg-rust hover:bg-rust/80 text-cream shadow-lg"
                  : "bg-mustard hover:bg-mustard/80 text-dark-bg font-bold shadow-lg"
              }`}
            >
              {loading
                ? "Evaluating API..."
                : isActive
                ? "DEACTIVATE SCENARIO (Restore Base State)"
                : "ACTIVATE SCENARIO OVERLAY"}
            </button>
          </div>
        </div>

        {/* Right: Sample Config & Composite Resilience Score Gauge */}
        <div className="md:col-span-6 bg-dark-card border border-dark-border rounded-lg p-5 flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between border-b border-dark-border/60 pb-2">
            <span className="text-xs font-data text-cream/50 uppercase tracking-widest">Composite Resilience Score</span>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-data text-cream/40">OD Sample Size:</span>
              <select
                value={sampleSize}
                onChange={(e) => setSampleSize(Number(e.target.value))}
                className="bg-dark-surface border border-dark-border text-cream text-xs rounded px-2 py-1 font-data"
              >
                <option value={50}>50 OD Pairs (Fast)</option>
                <option value={100}>100 OD Pairs</option>
                <option value={200}>200 OD Pairs</option>
                <option value={500}>500 OD Pairs (Full Analysis)</option>
              </select>
            </div>
          </div>

          {resilienceMetrics && (
            <div className="flex-1 flex flex-col items-center justify-center p-4 bg-dark-surface/60 rounded border border-mustard/30 space-y-2">
              <div className="text-cream/50 font-data text-xs uppercase tracking-widest">Network Resilience Score</div>
              <div className="text-5xl font-data font-bold text-mustard">{resilienceMetrics.resilience_score}</div>
              <div className="text-cream/40 text-xs font-data">out of 100 maximum rating</div>
              <div className="text-[10px] text-cream/40 font-body">Deterministic Seed 42 | {resilienceMetrics.sample_size} OD Pairs Tested</div>
            </div>
          )}
        </div>
      </div>

      {/* ── Resilience Metrics Grid ───────────────────────────────── */}
      {resilienceMetrics && (
        <section className="space-y-4">
          <h2 className="section-title text-base tracking-tight">SYSTEMIC RESILIENCE METRICS</h2>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center font-data">
            <div className="bg-dark-card border border-dark-border rounded-lg p-4">
              <div className="text-cream/40 text-xs uppercase">Route Availability</div>
              <div className="text-cream text-2xl font-bold mt-1">{resilienceMetrics.route_availability_pct}%</div>
              <div className="text-cream/30 text-[9px] mt-0.5">{resilienceMetrics.reachable_count} / {resilienceMetrics.sample_size} Reachable</div>
            </div>

            <div className="bg-dark-card border border-dark-border rounded-lg p-4">
              <div className="text-cream/40 text-xs uppercase">Avg Travel-Time Impact</div>
              <div className="text-rust text-2xl font-bold mt-1">+{resilienceMetrics.avg_travel_time_impact_pct}%</div>
              <div className="text-cream/30 text-[9px] mt-0.5">Mean Time Increase</div>
            </div>

            <div className="bg-dark-card border border-dark-border rounded-lg p-4">
              <div className="text-cream/40 text-xs uppercase">Unreachable OD Rate</div>
              <div className="text-cream text-2xl font-bold mt-1">{resilienceMetrics.unreachable_od_rate_pct}%</div>
              <div className="text-cream/30 text-[9px] mt-0.5">{resilienceMetrics.unreachable_count} Disconnected Pairs</div>
            </div>

            <div className="bg-dark-card border border-dark-border rounded-lg p-4">
              <div className="text-cream/40 text-xs uppercase">Rerouting Success</div>
              <div className="text-green-400 text-2xl font-bold mt-1">{resilienceMetrics.rerouting_success_rate_pct}%</div>
              <div className="text-cream/30 text-[9px] mt-0.5">{resilienceMetrics.rerouted_count} / {resilienceMetrics.disrupted_count} Rerouted</div>
            </div>

            <div className="bg-dark-card border border-dark-border rounded-lg p-4">
              <div className="text-cream/40 text-xs uppercase">Avg Transfer Change</div>
              <div className="text-mustard text-2xl font-bold mt-1">
                {resilienceMetrics.avg_transfer_change >= 0 ? `+${resilienceMetrics.avg_transfer_change}` : resilienceMetrics.avg_transfer_change}
              </div>
              <div className="text-cream/30 text-[9px] mt-0.5">Mean Transfer Delta</div>
            </div>
          </div>

          {/* ── Top Cascading Congestion Edges Table ───────────────────── */}
          <div className="bg-dark-card border border-dark-border rounded-lg p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-dark-border/60 pb-2">
              <div>
                <span className="text-xs font-data text-cream/50 uppercase tracking-widest">Top Affected Edges (Targeted Rerouted Load)</span>
                <p className="text-[10px] text-cream/40 font-body">Cascading congestion aggregated only on alternative edges traversed by rerouted passengers</p>
              </div>
              <span className="badge-derived text-[9px]">DERIVED_SIMULATION_OUTPUT</span>
            </div>

            {resilienceMetrics.cascading_congestion_edges.length === 0 ? (
              <div className="text-center py-6 text-cream/40 text-xs font-body">
                No rerouted traffic load on alternative edges for this scenario.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left font-data text-xs">
                  <thead className="bg-dark-surface text-cream/40 uppercase text-[10px] border-b border-dark-border">
                    <tr>
                      <th className="py-2.5 px-3">Track Segment / Edge</th>
                      <th className="py-2.5 px-3 text-center">Rerouted Passengers Load</th>
                      <th className="py-2.5 px-3 text-right">Derived Congestion Increase (%)</th>
                      <th className="py-2.5 px-3 text-right">Data Provenance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-border/40 text-cream/80">
                    {resilienceMetrics.cascading_congestion_edges.map((row, idx) => (
                      <tr key={idx} className="hover:bg-dark-surface/50">
                        <td className="py-2.5 px-3 font-mono font-bold text-cream">{row.edge}</td>
                        <td className="py-2.5 px-3 text-center font-bold text-mustard">{row.rerouted_passengers_load} journeys</td>
                        <td className="py-2.5 px-3 text-right font-bold text-rust">+{row.derived_congestion_increase_pct}%</td>
                        <td className="py-2.5 px-3 text-right text-[10px] font-mono text-cream/40">{row.data_provenance}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
};

export default ResiliencePage;

/**
 * NetworkOverviewPage.tsx — Canonical 5-Line Metro Network Overview.
 */
import React, { useEffect, useState } from "react";
import { fetchNetwork } from "../services/api";
import { useStore } from "../store/useStore";
import MetroMap from "../components/MetroMap/MetroMap";
import type { StationTopology } from "../types";
import { LINE_COLORS } from "../types";

const NetworkOverviewPage: React.FC = () => {
  const {
    network, networkLoading,
    setNetwork, setNetworkLoading, setNetworkError,
    hoveredStation, selectedStation,
    setHoveredStation, setSelectedStation,
  } = useStore();

  const [filter, setFilter] = useState<string>("All");

  useEffect(() => {
    if (network) return;
    setNetworkLoading(true);
    fetchNetwork()
      .then(setNetwork)
      .catch((e) => setNetworkError(e.message));
  }, [network, setNetwork, setNetworkLoading, setNetworkError]);

  const lineFilterOptions = ["All", "Purple", "Green", "Yellow", "Pink", "Blue"];

  const filteredStations: StationTopology[] =
    !network
      ? []
      : filter === "All"
      ? network.stations
      : network.stations.filter((s) => s.line === filter);

  const selectedStn = network?.stations.find((s) => s.id === selectedStation);

  return (
    <div className="flex h-[calc(100vh-53px)]">
      {/* Side panel */}
      <aside className="w-80 flex-shrink-0 border-r border-dark-border flex flex-col overflow-hidden bg-dark-bg">
        <div className="p-5 border-b border-dark-border">
          <h1 className="section-title text-lg mb-1 tracking-tight">NAMMA PULSE — BENGALURU METRO</h1>
          <p className="text-cream/40 text-xs">
            {network
              ? `${network.stations.filter(s => s.line !== "TRANSFER").length} stations · ${network.lines.length} lines`
              : "Loading…"}
          </p>
        </div>

        {/* Line filter */}
        <div className="p-3 flex gap-1 border-b border-dark-border flex-wrap">
          {lineFilterOptions.map((l) => {
            const color = l === "All" ? undefined : (LINE_COLORS as Record<string, string>)[l];
            return (
              <button
                key={l}
                id={`filter-${l.toLowerCase()}`}
                onClick={() => setFilter(l)}
                className={`py-1 px-2.5 rounded text-[10px] font-data uppercase tracking-wider transition-all border ${
                  filter === l
                    ? "border-transparent text-dark-bg font-bold"
                    : "border-dark-border text-cream/40 hover:text-cream"
                }`}
                style={filter === l && color ? { backgroundColor: color } : undefined}
              >
                {l}
              </button>
            );
          })}
        </div>

        {/* Selected station detail */}
        {selectedStn && (
          <div className="p-4 border-b border-dark-border bg-dark-hover animate-fade-in">
            <div className="flex items-start gap-2 mb-2">
              <div
                className="w-3 h-3 rounded-full mt-0.5 flex-shrink-0"
                style={{ backgroundColor: (LINE_COLORS as Record<string, string>)[selectedStn.line] ?? "#888" }}
              />
              <div>
                <div className="text-cream text-sm font-body font-semibold leading-tight">
                  {selectedStn.name}
                </div>
                <div className="text-cream/40 text-[10px] font-data mt-0.5">
                  {selectedStn.line} Line · Node {selectedStn.id} · Status: {selectedStn.line_status || "OPERATIONAL"}
                </div>
              </div>
            </div>
            {selectedStn.is_interchange && (
              <div className="text-mustard text-[10px] font-data">
                INTERCHANGE HUB: {selectedStn.interchange_lines.join(" ↔ ")}
              </div>
            )}
            <button
              className="mt-2 text-cream/30 text-[10px] hover:text-cream/60 transition-colors"
              onClick={() => setSelectedStation(null)}
            >
              ✕ clear selection
            </button>
          </div>
        )}

        {/* Station list */}
        <div className="overflow-y-auto flex-1">
          {filteredStations
            .filter((s) => s.line !== "TRANSFER")
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((s) => {
              const color = (LINE_COLORS as Record<string, string>)[s.line] ?? "#888";
              const isActive = selectedStation === s.id || hoveredStation === s.id;
              return (
                <button
                  key={`${s.id}-${s.line}`}
                  className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-left transition-colors border-b border-dark-border/50 ${
                    isActive ? "bg-dark-hover" : "hover:bg-dark-hover"
                  }`}
                  onClick={() => setSelectedStation(s.id === selectedStation ? null : s.id)}
                  onMouseEnter={() => setHoveredStation(s.id)}
                  onMouseLeave={() => setHoveredStation(null)}
                >
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                  <span className="text-cream/80 text-xs flex-1 truncate">{s.name}</span>
                  <span className="text-cream/30 text-[9px] font-mono">{s.line}</span>
                  {s.is_interchange && (
                    <span className="text-mustard text-[9px] font-data flex-shrink-0">HUB</span>
                  )}
                </button>
              );
            })}
        </div>
      </aside>

      {/* Map */}
      <main className="flex-1 relative overflow-hidden">
        {networkLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-bg z-30">
            <div className="w-8 h-8 border-2 border-cream/20 border-t-rust rounded-full animate-spin" />
          </div>
        )}
        {network && (
          <MetroMap
            network={network}
            hoveredStation={hoveredStation}
            selectedStation={selectedStation}
            onStationClick={(id) => setSelectedStation(id === selectedStation ? null : id)}
            onStationHover={setHoveredStation}
            className="absolute inset-0"
          />
        )}
        <div className="absolute bottom-4 right-4 badge-real text-[9px] pointer-events-none z-10">
          NAMMA PULSE — Canonical 5-Line Network
        </div>
      </main>
    </div>
  );
};

export default NetworkOverviewPage;

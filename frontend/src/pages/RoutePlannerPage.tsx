import React, { useCallback, useEffect } from "react";
import { fetchNetwork, fetchRouteComparison } from "../services/api";
import { useStore } from "../store/useStore";
import MetroMap from "../components/MetroMap/MetroMap";
import StationSearch from "../components/StationSearch/StationSearch";
import RouteComparePanel from "../components/RoutePanel/RouteComparePanel";
import type { RouteProfile } from "../types";

const PROFILES: { id: RouteProfile; label: string }[] = [
  { id: "BALANCED", label: "Balanced" },
  { id: "FASTEST", label: "Fastest" },
  { id: "LEAST_CONGESTED", label: "Least Congested" },
  { id: "MOST_RELIABLE", label: "Most Reliable" },
  { id: "FEWEST_TRANSFERS", label: "Fewest Transfers" },
];

const RoutePlannerPage: React.FC = () => {
  const {
    network, networkLoading, networkError,
    setNetwork, setNetworkLoading, setNetworkError,
    origin, destination, routeProfile,
    setOrigin, setDestination, setRouteProfile,
    routeResult, compareResult, selectedAlternative,
    routeLoading, routeError,
    setCompareResult, setSelectedAlternative, setRouteLoading, setRouteError,
    hoveredStation, selectedStation,
    setHoveredStation, setSelectedStation,
  } = useStore();

  const loadNetworkData = useCallback(() => {
    setNetworkLoading(true);
    fetchNetwork()
      .then(setNetwork)
      .catch((e) => setNetworkError(e.message));
  }, [setNetwork, setNetworkLoading, setNetworkError]);

  useEffect(() => {
    if (!network) {
      loadNetworkData();
    }
  }, [network, loadNetworkData]);

  const handleFindRouteWithProfile = useCallback(async (prof: RouteProfile) => {
    if (!origin || !destination) return;
    setRouteLoading(true);
    try {
      const result = await fetchRouteComparison(origin, destination, prof);
      setCompareResult(result);
    } catch (e: unknown) {
      setRouteError((e as Error).message);
    }
  }, [origin, destination, setRouteLoading, setCompareResult, setRouteError]);

  const handleProfileChange = useCallback((prof: RouteProfile) => {
    setRouteProfile(prof);
    if (origin && destination) {
      handleFindRouteWithProfile(prof);
    }
  }, [origin, destination, setRouteProfile, handleFindRouteWithProfile]);

  const handleFindRoute = useCallback(() => {
    handleFindRouteWithProfile(routeProfile);
  }, [routeProfile, handleFindRouteWithProfile]);

  const handleSwap = useCallback(() => {
    const tmp = origin;
    setOrigin(destination);
    setDestination(tmp);
  }, [origin, destination, setOrigin, setDestination]);

  const handleMapStationClick = useCallback(
    (stationId: string, stationName: string) => {
      if (!origin) {
        setOrigin(stationName);
      } else if (!destination) {
        setDestination(stationName);
      } else {
        setSelectedStation(stationId === selectedStation ? null : stationId);
      }
    },
    [origin, destination, selectedStation, setOrigin, setDestination, setSelectedStation]
  );

  return (
    <div className="flex h-[calc(100vh-53px)]">
      {/* ── Left panel ────────────────────────────────────────── */}
      <aside className="w-80 flex-shrink-0 border-r border-dark-border overflow-y-auto flex flex-col bg-dark-bg">
        {/* Header */}
        <div className="p-5 border-b border-dark-border">
          <h1 className="section-title text-lg mb-1 tracking-tight">NAMMA PULSE — BENGALURU METRO</h1>
          <p className="text-cream/40 text-xs font-body">
            Dynamic Route Planning
          </p>
        </div>

        {/* Form */}
        <div className="p-5 space-y-4 flex-1">
          <StationSearch
            id="origin-search"
            label="From"
            value={origin}
            onSelect={setOrigin}
            placeholder="e.g. Whitefield (Kadugodi)"
          />

          {/* Swap */}
          <div className="flex items-center gap-2">
            <div className="flex-1 h-px bg-dark-border" />
            <button
              id="swap-stations"
              onClick={handleSwap}
              className="p-1.5 rounded border border-dark-border text-cream/40 hover:text-cream hover:border-cream/30 transition-all"
              title="Swap origin and destination"
              aria-label="Swap origin and destination"
            >
              ⇅
            </button>
            <div className="flex-1 h-px bg-dark-border" />
          </div>

          <StationSearch
            id="destination-search"
            label="To"
            value={destination}
            onSelect={setDestination}
            placeholder="e.g. Silk Institute"
          />

          {/* Route Preference Selector */}
          <div>
            <label className="block text-xs font-data text-cream/50 mb-1.5 uppercase tracking-widest">
              Route Preference
            </label>
            <div className="space-y-1 bg-dark-surface p-2 rounded-md border border-dark-border">
              {PROFILES.map((p) => (
                <label
                  key={p.id}
                  className={`flex items-center gap-2 px-2 py-1 rounded cursor-pointer text-xs font-body transition-colors ${
                    routeProfile === p.id
                      ? "text-mustard font-semibold bg-mustard/10"
                      : "text-cream/60 hover:text-cream hover:bg-cream/5"
                  }`}
                >
                  <input
                    type="radio"
                    name="route-profile"
                    value={p.id}
                    checked={routeProfile === p.id}
                    onChange={() => handleProfileChange(p.id)}
                    className="accent-mustard"
                  />
                  <span>{p.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Find route button */}
          <button
            id="find-route-button"
            className="btn-primary w-full"
            onClick={handleFindRoute}
            disabled={!origin || !destination || routeLoading}
          >
            {routeLoading ? "Calculating Routes…" : "Find Dynamic Route"}
          </button>

          {/* Tip */}
          <p className="text-cream/25 text-[10px] font-body leading-relaxed">
            Tip: click any station on the map to set as origin or destination.
          </p>

          {/* Error */}
          {routeError && (
            <div className="bg-red-900/30 border border-red-800/50 rounded-md p-3 text-red-300 text-xs animate-fade-in">
              {routeError}
            </div>
          )}

          {/* Route comparison panel */}
          {compareResult && (
            <RouteComparePanel
              compareResult={compareResult}
              selectedAlternative={selectedAlternative}
              onSelectAlternative={setSelectedAlternative}
            />
          )}
        </div>
      </aside>

      {/* ── Main map area ──────────────────────────────────────── */}
      <main className="flex-1 relative overflow-hidden">
        {networkLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-bg z-30">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-cream/20 border-t-rust rounded-full animate-spin" />
              <p className="text-cream/40 text-sm font-body">Loading network…</p>
            </div>
          </div>
        )}

        {networkError && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-bg z-30">
            <div className="text-center space-y-3">
              <div className="text-red-400 text-4xl">⚠</div>
              <p className="text-cream/60 text-sm font-body">Cannot connect to API</p>
              <p className="text-cream/30 text-xs font-data">{networkError}</p>
            </div>
          </div>
        )}

        {network && (
          <MetroMap
            network={network}
            route={selectedAlternative || routeResult}
            hoveredStation={hoveredStation}
            selectedStation={selectedStation}
            onStationClick={handleMapStationClick}
            onStationHover={setHoveredStation}
            className="absolute inset-0"
          />
        )}

        {/* Data provenance overlay */}
        <div className="absolute bottom-4 right-4 flex flex-col items-end gap-1.5 pointer-events-none z-10">
          <div className="badge-real text-[9px]">NAMMA PULSE — BMRCL Canonical 5-Line Topology</div>
          {routeResult && (
            <div className="badge-synthetic text-[9px]">
              {selectedAlternative ? "ALTERNATIVE ROUTE OVERLAY" : "RECOMMENDED ROUTE OVERLAY"}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default RoutePlannerPage;


/**
 * RoutePanel.tsx — Displays the route result below the planner form.
 */

import React from "react";
import type { RouteResponse } from "../../types";
import { LINE_COLORS } from "../../types";

interface RoutePanelProps {
  route: RouteResponse;
}

function LineChip({ line }: { line: string }) {
  const color = (LINE_COLORS as Record<string, string>)[line] ?? "#888";
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-body font-medium text-dark-bg"
      style={{ backgroundColor: color }}
    >
      {line}
    </span>
  );
}

const RoutePanel: React.FC<RoutePanelProps> = ({ route }) => {
  const timeMin = Math.round(route.total_time_min);
  const h = Math.floor(timeMin / 60);
  const m = timeMin % 60;
  const timeLabel = h > 0 ? `${h}h ${m}min` : `${m} min`;

  return (
    <div className="card p-4 space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <h3 className="font-heading text-xl text-cream uppercase tracking-wide">
            {route.origin}
          </h3>
          <span className="text-cream/30 font-data text-xs">{route.algorithm.toUpperCase()}</span>
        </div>
        <div className="text-cream/40 text-xs mb-1">↓</div>
        <h3 className="font-heading text-xl text-cream uppercase tracking-wide">
          {route.destination}
        </h3>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-dark-surface rounded-md p-2.5 text-center">
          <div className="font-data text-lg text-cream font-bold">{timeLabel}</div>
          <div className="text-cream/40 text-[10px] uppercase tracking-wider mt-0.5">Travel time</div>
        </div>
        <div className="bg-dark-surface rounded-md p-2.5 text-center">
          <div className="font-data text-lg text-cream font-bold">{route.hop_count}</div>
          <div className="text-cream/40 text-[10px] uppercase tracking-wider mt-0.5">Stations</div>
        </div>
        <div className="bg-dark-surface rounded-md p-2.5 text-center">
          <div className="font-data text-lg text-cream font-bold">{route.interchange_count}</div>
          <div className="text-cream/40 text-[10px] uppercase tracking-wider mt-0.5">Changes</div>
        </div>
      </div>

      {/* Lines */}
      <div className="flex items-center gap-2 flex-wrap">
        {route.lines.map((l) => <LineChip key={l} line={l} />)}
        {route.interchange_stations.map((s) => (
          <span key={s} className="text-mustard text-[10px] font-data">
            ↔ {s.replace(/\(.*?\)/g, "").trim()}
          </span>
        ))}
      </div>

      {/* Station list by segment */}
      <div className="space-y-3">
        {route.segments.map((seg, i) => {
          const color = (LINE_COLORS as Record<string, string>)[seg.line] ?? "#888";
          return (
            <div key={i}>
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                <span className="text-xs font-body text-cream/50 font-medium">{seg.line} Line</span>
                <span className="text-cream/25 text-[10px] font-data">{Math.round(seg.segment_time_min)} min</span>
              </div>
              <div className="ml-5 space-y-0.5 border-l-2 pl-3" style={{ borderColor: color + "40" }}>
                {seg.station_names.map((name, j) => (
                  <div
                    key={j}
                    className={`text-xs py-0.5 ${
                      j === 0 || j === seg.station_names.length - 1
                        ? "text-cream font-medium"
                        : "text-cream/55"
                    }`}
                  >
                    {j === 0 && "◉ "}
                    {j !== 0 && j !== seg.station_names.length - 1 && "· "}
                    {j === seg.station_names.length - 1 && j !== 0 && "◉ "}
                    {name}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Provenance notice */}
      <div className="border-t border-dark-border pt-3">
        <div className="badge-synthetic text-[9px] mb-1">APPROXIMATE</div>
        <p className="text-cream/30 text-[10px] leading-relaxed">
          Travel times use a 2.5 min/segment fallback. Source data contains no measured per-segment times.
        </p>
      </div>
    </div>
  );
};

export default RoutePanel;

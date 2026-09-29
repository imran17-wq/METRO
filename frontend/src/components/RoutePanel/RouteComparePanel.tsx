/**
 * RouteComparePanel.tsx — Phase 4 Route Cards & Candidate Comparison Panel.
 *
 * Displays the Recommended Route Card, Recommendation Explanation,
 * Alternative Route Cards, and Score Breakdowns.
 */

import React from "react";
import type { DynamicRouteCompareResponse, RouteResponse } from "../../types";
import { LINE_COLORS } from "../../types";

interface RouteComparePanelProps {
  compareResult: DynamicRouteCompareResponse;
  selectedAlternative: RouteResponse | null;
  onSelectAlternative: (alt: RouteResponse | null) => void;
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

const RouteComparePanel: React.FC<RouteComparePanelProps> = ({
  compareResult,
  selectedAlternative,
  onSelectAlternative,
}) => {
  const rec = compareResult.recommended;
  const alts = compareResult.alternatives;

  const timeMin = Math.round(rec.predicted_travel_time ?? rec.total_time_min);
  const h = Math.floor(timeMin / 60);
  const m = timeMin % 60;
  const timeLabel = h > 0 ? `${h}h ${m}min` : `${m} min`;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* ── 1. Recommended Route Card ── */}
      <div className="card p-4 space-y-3.5 border-l-4 border-l-mustard bg-dark-card shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-mustard/20 text-mustard font-data text-xs font-bold uppercase tracking-wider">
            ★ RECOMMENDED ({compareResult.profile})
          </span>
          <span className="text-cream/40 font-data text-[10px] uppercase">
            {rec.prediction_source ?? "ML MODEL"}
          </span>
        </div>

        {/* Origin → Dest */}
        <div>
          <div className="font-heading text-lg text-cream uppercase tracking-wide">
            {rec.origin}
          </div>
          <div className="text-cream/40 text-xs my-0.5">↓</div>
          <div className="font-heading text-lg text-cream uppercase tracking-wide">
            {rec.destination}
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-4 gap-2">
          <div className="bg-dark-surface rounded-md p-2 text-center">
            <div className="font-data text-base text-cream font-bold">{timeLabel}</div>
            <div className="text-cream/40 text-[9px] uppercase tracking-wider mt-0.5">Time</div>
          </div>
          <div className="bg-dark-surface rounded-md p-2 text-center">
            <div className="font-data text-base text-cream font-bold">{rec.transfer_count ?? rec.interchange_count}</div>
            <div className="text-cream/40 text-[9px] uppercase tracking-wider mt-0.5">Xfers</div>
          </div>
          <div className="bg-dark-surface rounded-md p-2 text-center">
            <div className="font-data text-base text-cream font-bold">
              {rec.predicted_congestion !== undefined && rec.predicted_congestion !== null
                ? `${Math.round(rec.predicted_congestion)}%`
                : "N/A"}
            </div>
            <div className="text-cream/40 text-[9px] uppercase tracking-wider mt-0.5">Congestion</div>
          </div>
          <div className="bg-dark-surface rounded-md p-2 text-center">
            <div className="font-data text-base text-cream font-bold">
              {rec.reliability_score !== undefined && rec.reliability_score !== null
                ? `${Math.round(rec.reliability_score * 100)}%`
                : "N/A"}
            </div>
            <div className="text-cream/40 text-[9px] uppercase tracking-wider mt-0.5">Reliability</div>
          </div>
        </div>

        {/* Recommendation Reason / Explanation */}
        {rec.recommendation_reason && (
          <div className="bg-dark-surface/60 border border-mustard/30 rounded-md p-2.5 text-xs text-cream/90 font-body leading-relaxed">
            <span className="font-semibold text-mustard mr-1">Why this route?</span>
            {rec.recommendation_reason}
          </div>
        )}

        {/* Line Chips & Interchanges */}
        <div className="flex items-center gap-2 flex-wrap pt-1">
          {rec.lines.map((l) => (
            <LineChip key={l} line={l} />
          ))}
          {rec.interchange_stations.map((s) => (
            <span key={s} className="text-mustard text-[10px] font-data">
              ↔ {s.replace(/\(.*?\)/g, "").trim()}
            </span>
          ))}
        </div>

        {/* Detailed Station Sequence */}
        <div className="space-y-2.5 pt-2 border-t border-dark-border">
          {rec.segments.map((seg, i) => {
            const color = (LINE_COLORS as Record<string, string>)[seg.line] ?? "#888";
            return (
              <div key={i}>
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                  <span className="text-xs font-body text-cream/70 font-medium">{seg.line} Line</span>
                  <span className="text-cream/30 text-[10px] font-data">
                    {Math.round(seg.segment_time_min)} min
                  </span>
                </div>
                <div className="ml-4 space-y-0.5 border-l-2 pl-2.5" style={{ borderColor: color + "40" }}>
                  {seg.station_names.map((name, j) => (
                    <div
                      key={j}
                      className={`text-xs ${
                        j === 0 || j === seg.station_names.length - 1
                          ? "text-cream font-medium"
                          : "text-cream/50"
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

        {/* Score Breakdown Accordion / Details */}
        {rec.score_breakdown && (
          <div className="border-t border-dark-border pt-2 text-[10px] font-data text-cream/40 grid grid-cols-2 gap-x-4 gap-y-0.5">
            <div>Travel time score: {rec.score_breakdown.travel_time}</div>
            <div>Congestion penalty: {rec.score_breakdown.congestion_penalty}</div>
            <div>Delay penalty: {rec.score_breakdown.delay_penalty}</div>
            <div>Transfer penalty: {rec.score_breakdown.transfer_penalty}</div>
          </div>
        )}
      </div>

      {/* ── 2. Alternative Route Cards ── */}
      {alts.length > 0 ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-data uppercase text-cream/50 tracking-wider">
            <span>Alternative Routes ({alts.length})</span>
            {selectedAlternative && (
              <button
                onClick={() => onSelectAlternative(null)}
                className="text-rust hover:underline text-[10px]"
              >
                Clear overlay selection
              </button>
            )}
          </div>

          {alts.map((alt, idx) => {
            const isSelected = selectedAlternative === alt;
            const altTime = Math.round(alt.predicted_travel_time ?? alt.total_time_min);

            return (
              <div
                key={idx}
                onClick={() => onSelectAlternative(isSelected ? null : alt)}
                className={`card p-3 cursor-pointer transition-all border ${
                  isSelected
                    ? "border-rust bg-rust/10 shadow-md"
                    : "border-dark-border hover:border-cream/30 bg-dark-card"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-data text-xs font-bold text-cream/80 uppercase">
                    Alternative {idx + 1}
                  </span>
                  <span className="text-[10px] font-data text-cream/40">
                    {isSelected ? "● Overlay Active" : "Click to view map overlay"}
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs text-cream/90 font-body">
                  <div>
                    <span className="font-bold text-cream mr-2">{altTime} min</span>
                    <span className="text-cream/50 mr-2">
                      {alt.transfer_count ?? alt.interchange_count} transfer(s)
                    </span>
                    {alt.predicted_congestion !== undefined && alt.predicted_congestion !== null && (
                      <span className="text-cream/50">
                        {Math.round(alt.predicted_congestion)}% cong
                      </span>
                    )}
                  </div>
                  <div className="flex gap-1">
                    {alt.lines.map((l) => (
                      <LineChip key={l} line={l} />
                    ))}
                  </div>
                </div>

                {alt.recommendation_reason && (
                  <p className="text-[11px] text-cream/50 mt-1.5 font-body">
                    {alt.recommendation_reason}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card p-3 bg-dark-card/60 border border-dark-border text-center text-xs text-cream/50 font-body">
          No materially better alternative routes were found.
        </div>
      )}


      {/* ── 3. Data Provenance Notice ── */}
      <div className="border-t border-dark-border pt-3 space-y-1 text-[10px] text-cream/30 font-body">
        <div className="flex items-center gap-2">
          <span className="badge-synthetic text-[9px]">DYNAMIC ROUTING ENGINE</span>
          <span>State: {compareResult.network_state_timestamp}</span>
        </div>
        <p>
          Candidates scored using Yen's K=5 shortest simple paths algorithm and Pareto dominance filtering.
        </p>
      </div>
    </div>
  );
};

export default RouteComparePanel;

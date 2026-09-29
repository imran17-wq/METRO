import { useEffect, useState } from "react";
import { fetchCongestionPredictions } from "../services/api";
import type { CongestionPrediction, LineColor } from "../types";
import { LINE_COLORS } from "../types";

const TIME_SLOTS = Array.from({ length: 66 }, (_, i) => {
  const slot = i + 24;
  const hour = Math.floor((slot * 15) / 60);
  const min = (slot * 15) % 60;
  const label = `${hour.toString().padStart(2, "0")}:${min.toString().padStart(2, "0")}`;
  return { slot, label };
});

export default function CongestionPage() {
  const [selectedSlot, setSelectedSlot] = useState<number>(36); // 09:00
  const [selectedLine, setSelectedLine] = useState<string>("All");
  const [predictions, setPredictions] = useState<CongestionPrediction[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const lineFilter = selectedLine === "All" ? undefined : selectedLine;
    fetchCongestionPredictions("2024-01-08", selectedSlot, lineFilter)
      .then((data) => setPredictions(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedSlot, selectedLine]);

  const getBandBadgeClass = (band: string | null) => {
    switch (band) {
      case "LOW":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "MEDIUM":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "HIGH":
        return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      case "CRITICAL":
        return "bg-rose-500/10 text-rose-400 border-rose-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  return (
    <div className="flex-1 p-6 space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cream/10 pb-4">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold tracking-tight text-cream">
              Congestion Predictions
            </h1>
            <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-rust/20 text-rust border border-rust/30">
              SYNTHETIC MODEL OUTPUT
            </span>
          </div>
          <p className="text-sm text-cream/60 mt-1">
            Edge-level 15-minute regression predictions from LightGBM model.
          </p>
        </div>

        {/* Time Slot & Line Selectors */}
        <div className="flex items-center space-x-3">
          <div>
            <label className="block text-xs text-cream/50 mb-1 font-medium">Time Slot</label>
            <select
              value={selectedSlot}
              onChange={(e) => setSelectedSlot(Number(e.target.value))}
              className="bg-dark-surface border border-cream/20 rounded px-3 py-1.5 text-sm text-cream focus:outline-none focus:border-rust"
            >
              {TIME_SLOTS.map((t) => (
                <option key={t.slot} value={t.slot}>
                  {t.label} (Slot {t.slot})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-cream/50 mb-1 font-medium">Line Filter</label>
            <select
              value={selectedLine}
              onChange={(e) => setSelectedLine(e.target.value)}
              className="bg-dark-surface border border-cream/20 rounded px-3 py-1.5 text-sm text-cream focus:outline-none focus:border-rust"
            >
              <option value="All">All Lines</option>
              <option value="Purple">Purple Line</option>
              <option value="Green">Green Line</option>
              <option value="Yellow">Yellow Line</option>
              <option value="Pink">Pink Line</option>
              <option value="Blue">Blue Line</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Table */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="w-8 h-8 border-2 border-cream/20 border-t-rust rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
          Failed to load predictions: {error}
        </div>
      ) : (
        <div className="bg-dark-surface border border-cream/10 rounded-xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-cream/80">
              <thead className="bg-dark-bg/60 border-b border-cream/10 text-xs uppercase tracking-wider text-cream/50">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Edge ID</th>
                  <th className="py-3.5 px-4 font-semibold">Line</th>
                  <th className="py-3.5 px-4 font-semibold">Time Slot</th>
                  <th className="py-3.5 px-4 font-semibold">Predicted Congestion %</th>
                  <th className="py-3.5 px-4 font-semibold">Congestion Band</th>
                  <th className="py-3.5 px-4 font-semibold">Data Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cream/5">
                {predictions.map((p) => {
                  const lineColor = (LINE_COLORS[p.line as LineColor] ?? "#888888");
                  const isNullPred = p.predicted_congestion_pct === null;

                  return (
                    <tr key={p.edge_id} className="hover:bg-cream/[0.02] transition-colors">
                      <td className="py-3 px-4 font-mono text-xs text-cream font-medium">
                        {p.edge_id}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          <span
                            className="w-2.5 h-2.5 rounded-full"
                            style={{ backgroundColor: lineColor }}
                          />
                          <span className="font-medium text-cream">{p.line}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-cream/70">
                        {p.slot_start} (Slot {p.time_slot})
                      </td>
                      <td className="py-3 px-4 font-mono font-medium">
                        {isNullPred ? (
                          <span className="text-cream/40 italic">N/A</span>
                        ) : (
                          <span className="text-cream">
                            {p.predicted_congestion_pct?.toFixed(1)}%
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {isNullPred ? (
                          <span className="px-2 py-0.5 rounded text-xs border bg-slate-500/10 text-slate-400 border-slate-500/20">
                            Under Construction
                          </span>
                        ) : (
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-semibold border ${getBandBadgeClass(
                              p.congestion_band
                            )}`}
                          >
                            {p.congestion_band}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs font-mono text-cream/50">
                        {p.data_provenance}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

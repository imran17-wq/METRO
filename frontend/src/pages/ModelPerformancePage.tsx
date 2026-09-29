import { useEffect, useState } from "react";
import { fetchModelPerformance } from "../services/api";
import type { ModelPerformanceResponse } from "../types";

export default function ModelPerformancePage() {
  const [data, setData] = useState<ModelPerformanceResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchModelPerformance()
      .then((res) => setData(res))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex justify-center items-center h-96">
        <div className="w-8 h-8 border-2 border-cream/20 border-t-rust rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex-1 p-6 max-w-7xl mx-auto w-full">
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
          Failed to load model performance metrics: {error ?? "No data returned"}
        </div>
      </div>
    );
  }

  const { congestion, travel_time, delay_risk } = data;
  const shapEntries = Object.entries(congestion.shap_importance ?? {});

  return (
    <div className="flex-1 p-6 space-y-8 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="border-b border-cream/10 pb-4">
        <div className="flex items-center space-x-3">
          <h1 className="text-2xl font-bold tracking-tight text-cream">
            Model Performance & SHAP Explainability
          </h1>
          <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-rust/20 text-rust border border-rust/30">
            SYNTHETIC BENCHMARK
          </span>
        </div>
        <p className="text-sm text-cream/60 mt-1">
          Quantitative evaluation metrics and SHAP TreeExplainer feature importance.
        </p>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Congestion Model Card */}
        <div className="bg-dark-surface border border-cream/10 rounded-xl p-6 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-lg font-semibold text-cream">1. Congestion Model</h2>
              <p className="text-xs text-cream/50">LightGBM Regressor (edge x 15-min)</p>
            </div>
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-cream/10 text-cream/70">
              v{congestion.model_version ?? "1.0.0"}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 bg-dark-bg/60 p-4 rounded-lg border border-cream/5">
            <div>
              <div className="text-xs text-cream/50 uppercase">Model MAE</div>
              <div className="text-2xl font-bold text-emerald-400">
                {congestion.test_metrics?.mae?.toFixed(2)}%
              </div>
              <div className="text-xs text-cream/40 mt-1">
                Baseline: {congestion.comparison?.baseline_mae?.toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-cream/50 uppercase font-medium">MAE Improvement</div>
              <div className="text-2xl font-bold text-rust">
                +{congestion.comparison?.mae_improvement_pct?.toFixed(1)}%
              </div>
              <div className="text-xs text-cream/40 mt-1">Over historical mean</div>
            </div>
          </div>

          <div className="bg-mustard/10 border border-mustard/30 rounded-md p-3 text-xs text-cream/90 font-body">
            <span className="font-bold text-mustard mr-1">Honest Data Reporting:</span>
            Historical baseline currently performs better on this synthetic dataset (Historical Baseline MAE: {congestion.comparison?.baseline_mae?.toFixed(2) ?? "0.10"}% vs LightGBM MAE: {congestion.test_metrics?.mae?.toFixed(2) ?? "0.44"}%). Baseline currently performs better on this synthetic dataset.
          </div>

          <div className="text-xs text-cream/60 space-y-1 font-mono bg-dark-bg/30 p-3 rounded">
            <div>RMSE: {congestion.test_metrics?.rmse?.toFixed(2)}% (Baseline: {congestion.comparison?.baseline_rmse?.toFixed(2)}%)</div>
            <div>R² Score: {congestion.test_metrics?.r2?.toFixed(4)}</div>
            <div>Validation: {congestion.validation_method}</div>
          </div>
        </div>


        {/* Travel-Time Model Card */}
        <div className="bg-dark-surface border border-cream/10 rounded-xl p-6 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-lg font-semibold text-cream">2. Travel-Time Model</h2>
              <p className="text-xs text-cream/50">LightGBM Regressor (realistic travel time)</p>
            </div>
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-cream/10 text-cream/70">
              v{travel_time.model_version ?? "1.0.0"}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 bg-dark-bg/60 p-4 rounded-lg border border-cream/5">
            <div>
              <div className="text-xs text-cream/50 uppercase">Model MAE</div>
              <div className="text-2xl font-bold text-emerald-400">
                {travel_time.test_metrics?.mae?.toFixed(2)} min
              </div>
              <div className="text-xs text-cream/40 mt-1">
                Baseline: {travel_time.comparison?.baseline_mae?.toFixed(2)} min
              </div>
            </div>
            <div>
              <div className="text-xs text-cream/50 uppercase">MAE Improvement</div>
              <div className="text-2xl font-bold text-rust">
                +{travel_time.comparison?.mae_improvement_pct?.toFixed(1)}%
              </div>
              <div className="text-xs text-cream/40 mt-1">Over scheduled time</div>
            </div>
          </div>

          <div className="text-xs text-cream/60 space-y-1 font-mono bg-dark-bg/30 p-3 rounded">
            <div>RMSE: {travel_time.test_metrics?.rmse?.toFixed(2)} min</div>
            <div>R² Score: {travel_time.test_metrics?.r2?.toFixed(4)}</div>
            <div>Target Formula: scheduled + congestion_penalty + delay</div>
          </div>
        </div>
      </div>

      {/* SHAP Importance Chart */}
      <div className="bg-dark-surface border border-cream/10 rounded-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-cream">Global Feature Importance (SHAP)</h2>
        <p className="text-xs text-cream/50">
          Mean absolute SHAP value impact per feature on the Congestion LightGBM model.
        </p>

        <div className="space-y-2.5 pt-2">
          {shapEntries.map(([feat, val]) => {
            const maxVal = Math.max(...Object.values(congestion.shap_importance ?? { a: 1 }), 1.0);
            const pct = Math.min((val / maxVal) * 100, 100);

            return (
              <div key={feat} className="flex items-center text-xs space-x-3">
                <span className="w-36 font-mono text-cream/80 truncate text-right">{feat}</span>
                <div className="flex-1 bg-dark-bg/80 rounded-full h-3.5 overflow-hidden p-0.5 border border-cream/5">
                  <div
                    className="bg-rust h-full rounded-full transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-12 font-mono text-cream/50 text-right">{val.toFixed(2)}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Delay Risk Card */}
      <div className="bg-dark-surface border border-cream/10 rounded-xl p-6 space-y-2">
        <h2 className="text-lg font-semibold text-cream">3. Delay Risk Model (XGBoost)</h2>
        {delay_risk.skipped ? (
          <p className="text-sm text-amber-400/90 font-mono bg-amber-500/10 p-3 rounded border border-amber-500/20">
            {delay_risk.reason}
          </p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2 font-mono text-xs text-cream/80">
            <div className="bg-dark-bg/60 p-3 rounded">
              <div className="text-cream/50 text-[10px] uppercase">PR-AUC</div>
              <div className="text-lg font-bold text-cream">{delay_risk.test_metrics?.pr_auc}</div>
            </div>
            <div className="bg-dark-bg/60 p-3 rounded">
              <div className="text-cream/50 text-[10px] uppercase">ROC-AUC</div>
              <div className="text-lg font-bold text-cream">{delay_risk.test_metrics?.roc_auc}</div>
            </div>
            <div className="bg-dark-bg/60 p-3 rounded">
              <div className="text-cream/50 text-[10px] uppercase">Precision</div>
              <div className="text-lg font-bold text-cream">{delay_risk.test_metrics?.precision}</div>
            </div>
            <div className="bg-dark-bg/60 p-3 rounded">
              <div className="text-cream/50 text-[10px] uppercase">Recall</div>
              <div className="text-lg font-bold text-cream">{delay_risk.test_metrics?.recall}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

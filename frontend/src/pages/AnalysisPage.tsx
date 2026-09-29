/**
 * AnalysisPage.tsx — Consolidated Deep Analysis Hub for Namma Pulse.
 * Merges Network Overview, Congestion Analysis, Resilience Analysis, and Model Performance into a single tabbed interface.
 */
import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import NetworkOverviewPage from "./NetworkOverviewPage";
import CongestionPage from "./CongestionPage";
import ResiliencePage from "./ResiliencePage";
import ModelPerformancePage from "./ModelPerformancePage";

type AnalysisTab = "network" | "congestion" | "resilience" | "predictions";

const AnalysisPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get("tab") as AnalysisTab) || "network";
  const [activeTab, setActiveTab] = useState<AnalysisTab>(initialTab);

  const handleTabChange = (tab: AnalysisTab) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const tabs: { id: AnalysisTab; label: string; icon: string; desc: string }[] = [
    { id: "network", label: "NETWORK TOPOLOGY", icon: "🌐", desc: "Canonical 5-Line Metro Network" },
    { id: "congestion", label: "CONGESTION HEATMAP", icon: "📊", desc: "Edge-Level Passenger Flow & Demand" },
    { id: "resilience", label: "RESILIENCE METRICS", icon: "🛡️", desc: "Network Availability & Rerouting Impact" },
    { id: "predictions", label: "ML MODEL PERFORMANCE", icon: "🤖", desc: "LightGBM & SHAP Importance" },
  ];

  return (
    <div className="flex flex-col flex-1 min-h-[calc(100vh-53px)] bg-dark-bg">
      {/* Sub-header tab navigation */}
      <div className="border-b border-dark-border bg-dark-surface/60 px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-cream text-base uppercase tracking-wider">
            Deep Network Analysis
          </h1>
          <p className="text-cream/40 text-xs mt-0.5">
            Operational topology, passenger flow heatmaps, resilience metrics, and ML model performance.
          </p>
        </div>

        {/* Tab selector buttons */}
        <div className="flex items-center gap-1.5 bg-dark-bg p-1 rounded-lg border border-dark-border">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => handleTabChange(t.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-data transition-all ${
                activeTab === t.id
                  ? "bg-rust text-cream font-semibold shadow-sm"
                  : "text-cream/60 hover:text-cream hover:bg-dark-surface"
              }`}
            >
              <span>{t.icon}</span>
              <span>{t.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 flex flex-col">
        {activeTab === "network" && <NetworkOverviewPage />}
        {activeTab === "congestion" && <CongestionPage />}
        {activeTab === "resilience" && <ResiliencePage />}
        {activeTab === "predictions" && <ModelPerformancePage />}
      </div>
    </div>
  );
};

export default AnalysisPage;

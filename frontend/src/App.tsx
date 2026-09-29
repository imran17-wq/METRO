import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import NavBar from "./components/NavBar/NavBar";

// Lazy-load consolidated pages for code splitting
const CommandCenterPage = lazy(() => import("./pages/CommandCenterPage"));
const RoutePlannerPage = lazy(() => import("./pages/RoutePlannerPage"));
const SimulationPage = lazy(() => import("./pages/SimulationPage"));
const AnalysisPage = lazy(() => import("./pages/AnalysisPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-screen bg-dark-bg">
      <div className="w-8 h-8 border-2 border-cream/20 border-t-rust rounded-full animate-spin" />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen bg-dark-bg text-cream font-sans">
        <NavBar />
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            {/* Primary Navigation Routes */}
            <Route path="/" element={<CommandCenterPage />} />
            <Route path="/routes" element={<RoutePlannerPage />} />
            <Route path="/planner" element={<RoutePlannerPage />} />
            <Route path="/incidents" element={<SimulationPage />} />
            <Route path="/simulation" element={<SimulationPage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/about" element={<AboutPage />} />

            {/* Backwards compatibility redirects for old deep analysis routes */}
            <Route path="/network" element={<Navigate to="/analysis?tab=network" replace />} />
            <Route path="/congestion" element={<Navigate to="/analysis?tab=congestion" replace />} />
            <Route path="/resilience" element={<Navigate to="/analysis?tab=resilience" replace />} />
            <Route path="/model-performance" element={<Navigate to="/analysis?tab=predictions" replace />} />

            {/* Catch-all fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </div>
    </BrowserRouter>
  );
}

export default App;

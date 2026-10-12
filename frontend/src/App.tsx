import { Suspense, lazy } from "react";
import { Route, Routes, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { SwarmRunsPage } from "./pages/SwarmRunsPage";

const AlphaPoolPage = lazy(() =>
  import("./pages/AlphaPoolPage").then((module) => ({
    default: module.AlphaPoolPage,
  })),
);
const ManualBacktestPage = lazy(() =>
  import("./pages/ManualBacktestPage").then((module) => ({
    default: module.ManualBacktestPage,
  })),
);
const StrategyBacktestPage = lazy(() =>
  import("./pages/StrategyBacktestPage").then((module) => ({
    default: module.StrategyBacktestPage,
  })),
);
const SwarmRunDetailPage = lazy(() =>
  import("./pages/SwarmRunDetailPage").then((module) => ({
    default: module.SwarmRunDetailPage,
  })),
);
const WikiPage = lazy(() =>
  import("./pages/WikiPage").then((module) => ({
    default: module.WikiPage,
  })),
);
const AdminPage = lazy(() =>
  import("./pages/AdminPage").then((module) => ({
    default: module.AdminPage,
  })),
);

export default function App() {
  return (
    <ErrorBoundary fallbackTitle="Application Error">
      <Suspense fallback={<div className="page-grid" style={{ padding: "32px" }}><p className="muted">Loading workstation...</p></div>}>
        <Routes>
          <Route element={<Layout />}>
            {/* Main Alpha Miner Core Routes */}
            <Route path="/" element={<ErrorBoundary><AlphaPoolPage /></ErrorBoundary>} />
            <Route path="/pool" element={<ErrorBoundary><AlphaPoolPage /></ErrorBoundary>} />
            <Route path="/runs" element={<ErrorBoundary><SwarmRunsPage /></ErrorBoundary>} />
            <Route path="/runs/:runId" element={<ErrorBoundary><SwarmRunDetailPage /></ErrorBoundary>} />
            <Route path="/manual" element={<ErrorBoundary fallbackTitle="Manual Backtest Lab Error"><ManualBacktestPage /></ErrorBoundary>} />
            <Route path="/strategy" element={<ErrorBoundary fallbackTitle="Strategy Backtester Error"><StrategyBacktestPage /></ErrorBoundary>} />
            <Route path="/wiki" element={<ErrorBoundary fallbackTitle="Wiki Obsidian Error"><WikiPage /></ErrorBoundary>} />
            <Route path="/ops" element={<ErrorBoundary fallbackTitle="Ops Admin Error"><AdminPage /></ErrorBoundary>} />

            {/* Catch-all redirect to Alpha Pool */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}

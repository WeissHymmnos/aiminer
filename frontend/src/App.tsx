import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AlphaPoolPage } from "./pages/AlphaPoolPage";
import { ManualBacktestPage } from "./pages/ManualBacktestPage";
import { StrategyBacktestPage } from "./pages/StrategyBacktestPage";
import { SwarmRunDetailPage } from "./pages/SwarmRunDetailPage";
import { SwarmRunsPage } from "./pages/SwarmRunsPage";

const WikiPage = lazy(() =>
  import("./pages/WikiPage").then((module) => ({
    default: module.WikiPage,
  })),
);

export default function App() {
  return (
    <Suspense fallback={<div className="page-grid"><p className="muted">Loading page...</p></div>}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<SwarmRunsPage />} />
          <Route path="/runs/:runId" element={<SwarmRunDetailPage />} />
          <Route path="/pool" element={<AlphaPoolPage />} />
          <Route path="/manual" element={<ManualBacktestPage />} />
          <Route path="/strategy" element={<StrategyBacktestPage />} />
          <Route path="/wiki" element={<WikiPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

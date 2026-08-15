import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
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
const CatalogPage = lazy(() =>
  import("./pages/CatalogPage").then((module) => ({
    default: module.CatalogPage,
  })),
);
const ReviewPage = lazy(() =>
  import("./pages/ReviewPage").then((module) => ({
    default: module.ReviewPage,
  })),
);
const ReproducePage = lazy(() =>
  import("./pages/ReproducePage").then((module) => ({
    default: module.ReproducePage,
  })),
);
const AgentPage = lazy(() =>
  import("./pages/AgentPage").then((module) => ({
    default: module.AgentPage,
  })),
);

export default function App() {
  return (
    <Suspense fallback={<div className="page-grid"><p className="muted">Loading page...</p></div>}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/catalog/:id" element={<CatalogPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/reproduce" element={<ReproducePage />} />
          <Route path="/agent" element={<AgentPage />} />
          <Route path="/runs" element={<SwarmRunsPage />} />
          <Route path="/runs/:runId" element={<SwarmRunDetailPage />} />
          <Route path="/pool" element={<AlphaPoolPage />} />
          <Route path="/manual" element={<ManualBacktestPage />} />
          <Route path="/strategy" element={<StrategyBacktestPage />} />
          <Route path="/wiki" element={<WikiPage />} />
          <Route path="/ops" element={<AdminPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Panel, Group, type PanelImperativeHandle } from "react-resizable-panels";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ResizeHandle } from "../components/ResizeHandle";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { Sparkline } from "../components/Sparkline";
import { api, getErrorMessage } from "../lib/api";
import type { FactorSummary } from "../types";

const FACTOR_PAGE_SIZE = 50;

export function AlphaPoolPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"ic" | "rank_ic" | "time">("ic");
  const [filterRole, setFilterRole] = useState<string>("all");
  const [detailTab, setDetailTab] = useState<"overview" | "chart" | "report" | "json">("overview");
  const [copiedFormula, setCopiedFormula] = useState(false);
  const [detailCollapsed, setDetailCollapsed] = useState(false);
  const detailPanelRef = useRef<PanelImperativeHandle | null>(null);

  const factorsOffset = page * FACTOR_PAGE_SIZE;
  const factors = useQuery({
    queryKey: ["factors", factorsOffset, FACTOR_PAGE_SIZE],
    queryFn: () => api.listFactors({ offset: factorsOffset, limit: FACTOR_PAGE_SIZE }),
    placeholderData: keepPreviousData,
    refetchInterval: 10000,
  });

  const factorDetail = useQuery({
    queryKey: ["factor", selectedId],
    queryFn: () => api.getFactor(selectedId!),
    enabled: Boolean(selectedId),
  });

  const factorReport = useQuery({
    queryKey: ["factor-report", selectedId],
    queryFn: () => api.getFactorReport(selectedId!),
    enabled: Boolean(selectedId && detailTab === "report"),
  });

  const rawItems = Array.isArray(factors.data?.items)
    ? factors.data.items
    : Array.isArray(factors.data)
      ? (factors.data as FactorSummary[])
      : [];

  // Extract unique roles for the filter dropdown
  const uniqueRoles = useMemo(() => {
    const roles = new Set<string>();
    for (const item of rawItems) {
      const role = (item as any).role;
      if (role && typeof role === "string") {
        roles.add(role.slice(0, 30));
      }
    }
    return Array.from(roles);
  }, [rawItems]);

  // Filter and sort items
  const filteredItems = useMemo(() => {
    let result = [...rawItems];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter((item) => {
        const idMatch = item.id.toLowerCase().includes(q);
        const hypMatch = (item.hypothesis ?? "").toLowerCase().includes(q);
        const codeMatch = ((item as any).code ?? "").toLowerCase().includes(q);
        const roleMatch = ((item as any).role ?? "").toLowerCase().includes(q);
        return idMatch || hypMatch || codeMatch || roleMatch;
      });
    }

    if (filterRole !== "all") {
      result = result.filter((item) => ((item as any).role ?? "").startsWith(filterRole));
    }

    result.sort((a, b) => {
      if (sortBy === "ic") {
        const valA = a.ic ?? (a.metrics?.information_coefficient as number) ?? 0;
        const valB = b.ic ?? (b.metrics?.information_coefficient as number) ?? 0;
        return valB - valA;
      }
      if (sortBy === "rank_ic") {
        const valA = (a.metrics?.rank_ic as number) ?? 0;
        const valB = (b.metrics?.rank_ic as number) ?? 0;
        return valB - valA;
      }
      return 0; // Natural order (timestamp DESC)
    });

    return result;
  }, [rawItems, searchQuery, filterRole, sortBy]);

  const hasNextPage = (factors.data?.next_offset ?? 0) < (factors.data?.total ?? 0);

  const selectedData = factorDetail.data as any;

  const handleCopyFormula = (code: string) => {
    if (!code) return;
    navigator.clipboard.writeText(code).then(() => {
      setCopiedFormula(true);
      setTimeout(() => setCopiedFormula(false), 2000);
    });
  };

  const handleSendToManualLab = (code: string) => {
    if (!code) return;
    localStorage.setItem("aiminer_pending_formula", code);
    navigate("/manual");
  };

  return (
    <Group orientation="horizontal" className="panel-container">
      {/* Left Panel: Factor Pool Table & Filter Bar */}
      <Panel id="pool-list-panel" defaultSize={38} minSize={25}>
        <SectionCard
          title="Alpha Factor Pool"
          actions={
            <div className="button-group">
              <span className="badge-pill">
                {factors.data?.total ?? rawItems.length} Factors
              </span>
              <button
                type="button"
                className="button button-text-sm"
                onClick={() => {
                  if (detailCollapsed) {
                    detailPanelRef.current?.expand();
                    setDetailCollapsed(false);
                  } else {
                    detailPanelRef.current?.collapse();
                    setDetailCollapsed(true);
                  }
                }}
              >
                {detailCollapsed ? "Show Detail" : "Hide Detail"}
              </button>
            </div>
          }
        >
          {/* Search and Filters */}
          <div className="filter-toolbar">
            <input
              type="text"
              className="search-input"
              placeholder="🔍 Search factor ID, formula, or hypothesis..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <div className="filter-controls-row">
              <select
                className="select-sm"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
              >
                <option value="ic">Sort by IC (High → Low)</option>
                <option value="rank_ic">Sort by Rank IC</option>
                <option value="time">Sort by Latest</option>
              </select>

              {uniqueRoles.length > 0 && (
                <select
                  className="select-sm"
                  value={filterRole}
                  onChange={(e) => setFilterRole(e.target.value)}
                >
                  <option value="all">All Agent Roles</option>
                  {uniqueRoles.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {factors.isPending && !factors.data ? (
            <div className="status-block loading">Loading alpha pool factors...</div>
          ) : null}
          {factors.isError ? (
            <div className="status-block error">{getErrorMessage(factors.error)}</div>
          ) : null}

          {/* Factor List */}
          <div className="list">
            {filteredItems.map((factor: FactorSummary) => {
              const icVal = factor.ic ?? ((factor as any).perf_metric as number) ?? (factor.metrics?.information_coefficient as number) ?? 0;
              const rankIcVal = factor.metrics?.rank_ic as number | undefined;
              const isEffective = (factor as any).is_effective !== false;
              const roleTag = (factor as any).role ? String((factor as any).role).slice(0, 24) : null;

              return (
                <button
                  type="button"
                  key={factor.id}
                  className={`list-row button-reset factor-card-row ${selectedId === factor.id ? "selected" : ""}`}
                  onClick={() => {
                    setSelectedId(factor.id);
                    if (detailCollapsed) {
                      detailPanelRef.current?.expand();
                      setDetailCollapsed(false);
                    }
                  }}
                >
                  <div className="factor-row-content">
                    <div className="factor-header-line">
                      <strong className="factor-id">{factor.id}</strong>
                      {roleTag && <span className="tag-role-pill">{roleTag}</span>}
                      {isEffective && <span className="tag-effective-pill">Effective</span>}
                    </div>
                    <p className="factor-hypothesis-preview">{factor.hypothesis || "No hypothesis summary"}</p>
                    <div className="factor-badges-line">
                      <span className={`badge-metric ${icVal >= 0.03 ? "highlight" : ""}`}>
                        IC: {typeof icVal === "number" ? icVal.toFixed(4) : "--"}
                      </span>
                      {rankIcVal !== undefined && (
                        <span className="badge-metric-muted">
                          RankIC: {rankIcVal.toFixed(4)}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
            {!factors.isPending && !filteredItems.length ? (
              <p className="muted empty-state">No factors match the current filter or search criteria.</p>
            ) : null}
          </div>

          {/* Pagination */}
          <div className="pagination-bar">
            <button
              className="button"
              disabled={page === 0}
              onClick={() => setPage((current) => Math.max(0, current - 1))}
            >
              Prev
            </button>
            <span className="pagination-summary">
              Page {page + 1}
              {typeof factors.data?.total === "number" ? ` · ${factors.data.total} factors` : ""}
            </span>
            <button
              className="button"
              disabled={!hasNextPage}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </div>
        </SectionCard>
      </Panel>

      <ResizeHandle />

      {/* Right Panel: Factor Inspector */}
      <Panel
        id="pool-detail-panel"
        defaultSize={62}
        minSize={30}
        collapsible
        collapsedSize={0}
        panelRef={detailPanelRef}
        onResize={(size) => setDetailCollapsed(size.asPercentage <= 0.1)}
      >
        <SectionCard
          title={selectedData ? `Factor Detail: ${selectedData.id}` : "Factor Detail"}
          actions={
            selectedData ? (
              <div className="button-group">
                <button
                  type="button"
                  className="button button-accent-sm"
                  onClick={() => handleSendToManualLab(selectedData.code)}
                >
                  🧪 Test in Manual Lab
                </button>
                <button
                  type="button"
                  className="button button-sm"
                  onClick={() => handleCopyFormula(selectedData.code)}
                >
                  {copiedFormula ? "✓ Copied" : "📋 Copy Formula"}
                </button>
              </div>
            ) : null
          }
        >
          {factorDetail.isError ? (
            <div className="status-block error">{getErrorMessage(factorDetail.error)}</div>
          ) : null}
          {factorDetail.isPending && selectedId ? (
            <div className="status-block loading">Loading comprehensive factor telemetry...</div>
          ) : null}

          {selectedData ? (
            <div className="stack factor-detail-stack">
              {/* Formula & Hypothesis Banner */}
              <div className="detail-banner-card">
                <div className="detail-meta-line">
                  <span className="factor-detail-id">{selectedData.id}</span>
                  {selectedData.role && (
                    <span className="tag-role-pill large">{selectedData.role}</span>
                  )}
                  {selectedData.is_effective !== false && (
                    <span className="tag-effective-pill large">Verified Alpha</span>
                  )}
                </div>

                {selectedData.code && (
                  <div className="formula-box">
                    <span className="formula-label">Qlib Factor Formula:</span>
                    <pre className="formula-code"><code>{selectedData.code}</code></pre>
                  </div>
                )}

                <div className="hypothesis-box">
                  <span className="box-label">Economic Hypothesis:</span>
                  <p className="hypothesis-text">{selectedData.hypothesis || "No hypothesis provided."}</p>
                </div>
              </div>

              {/* Navigation Tabs for Detail View */}
              <div className="tab-bar">
                <button
                  type="button"
                  className={`tab-btn ${detailTab === "overview" ? "active" : ""}`}
                  onClick={() => setDetailTab("overview")}
                >
                  📊 Performance & Returns
                </button>
                <button
                  type="button"
                  className={`tab-btn ${detailTab === "chart" ? "active" : ""}`}
                  onClick={() => setDetailTab("chart")}
                >
                  📈 High-Res Equity Curve
                </button>
                <button
                  type="button"
                  className={`tab-btn ${detailTab === "report" ? "active" : ""}`}
                  onClick={() => setDetailTab("report")}
                >
                  📑 Research Report
                </button>
                <button
                  type="button"
                  className={`tab-btn ${detailTab === "json" ? "active" : ""}`}
                  onClick={() => setDetailTab("json")}
                >
                  {`{ }`} Raw Telemetry
                </button>
              </div>

              {/* Tab 1: Overview */}
              {detailTab === "overview" && (
                <div className="tab-content stack">
                  <MetricGrid metrics={(selectedData.metrics as Record<string, unknown>) ?? {}} />
                  <Sparkline
                    title="Cumulative Returns (Out-of-Sample Backtest)"
                    returns={(selectedData.returns as Record<string, number>) ?? {}}
                  />
                </div>
              )}

              {/* Tab 2: High-Res Static Chart */}
              {detailTab === "chart" && (
                <div className="tab-content">
                  {selectedData.chart_url ? (
                    <div className="chart-preview-card">
                      <img
                        src={selectedData.chart_url}
                        alt={`Cumulative Returns for ${selectedData.id}`}
                        className="equity-curve-img"
                      />
                    </div>
                  ) : (
                    <div className="status-block empty">
                      No standalone chart PNG found on disk for this factor. Check the interactive curve under the Performance tab.
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Markdown Research Report */}
              {detailTab === "report" && (
                <div className="tab-content report-card">
                  {factorReport.isPending ? (
                    <div className="status-block loading">Loading Markdown report...</div>
                  ) : factorReport.isError ? (
                    <div className="status-block error">{getErrorMessage(factorReport.error)}</div>
                  ) : factorReport.data ? (
                    <div className="markdown-prose">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {factorReport.data}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="status-block empty">No markdown report generated yet for this factor.</div>
                  )}
                </div>
              )}

              {/* Tab 4: Raw JSON */}
              {detailTab === "json" && (
                <div className="tab-content">
                  <JsonView value={selectedData} maxLines={100} />
                </div>
              )}
            </div>
          ) : (
            <div className="empty-selection-placeholder">
              <div className="empty-icon">📈</div>
              <h3>Select a factor to inspect</h3>
              <p className="muted">
                Choose any discovered Alpha factor from the list on the left to analyze its formula,
                IC metrics, cumulative returns, and AI quantitative research report.
              </p>
            </div>
          )}
        </SectionCard>
      </Panel>
    </Group>
  );
}

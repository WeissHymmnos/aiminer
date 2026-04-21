import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Panel, Group, type PanelImperativeHandle } from "react-resizable-panels";
import { ResizeHandle } from "../components/ResizeHandle";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { Sparkline } from "../components/Sparkline";
import { api, getErrorMessage } from "../lib/api";
import type { FactorSummary } from "../types";

const FACTOR_PAGE_SIZE = 50;

export function AlphaPoolPage() {
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
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
  const factorItems = factors.data?.items ?? [];
  const hasNextPage = (factors.data?.next_offset ?? 0) < (factors.data?.total ?? 0);

  return (
    <Group orientation="horizontal" className="panel-container">
      <Panel id="pool-list-panel" defaultSize={35} minSize={20}>
        <SectionCard
          title="Alpha Pool"
          actions={
            <button
              type="button"
              className="button"
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
          }
        >
          {factors.isPending && !factors.data ? <div className="status-block loading">Loading alpha pool...</div> : null}
          {factors.isError ? <div className="status-block error">{getErrorMessage(factors.error)}</div> : null}
          <div className="list">
            {factorItems.map((factor: FactorSummary) => (
              <button
                type="button"
                key={factor.id}
                className={`list-row button-reset ${selectedId === factor.id ? "selected" : ""}`}
                onClick={() => {
                  setSelectedId(factor.id);
                  if (detailCollapsed) {
                    detailPanelRef.current?.expand();
                    setDetailCollapsed(false);
                  }
                }}
              >
                <div>
                  <strong>{factor.id}</strong>
                  <p className="muted">{factor.hypothesis}</p>
                </div>
                <span>{factor.ic?.toFixed?.(4) ?? "-"}</span>
              </button>
            ))}
            {!factors.isPending && !factorItems.length ? <p className="muted">No factors on this page.</p> : null}
          </div>
          <div className="pagination-bar">
            <button className="button" disabled={page === 0} onClick={() => setPage((current) => Math.max(0, current - 1))}>
              Prev
            </button>
            <span className="pagination-summary">
              Page {page + 1}
              {typeof factors.data?.total === "number" ? ` · ${factors.data.total} factors` : ""}
            </span>
            <button className="button" disabled={!hasNextPage} onClick={() => setPage((current) => current + 1)}>
              Next
            </button>
          </div>
        </SectionCard>
      </Panel>
      <ResizeHandle />
      <Panel
        id="pool-detail-panel"
        defaultSize={65}
        minSize={30}
        collapsible
        collapsedSize={0}
        panelRef={detailPanelRef}
        onResize={(size) => setDetailCollapsed(size.asPercentage <= 0.1)}
      >
        <SectionCard
          title="Factor Detail"
          actions={
            <button
              type="button"
              className="button"
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
              {detailCollapsed ? "Expand" : "Collapse"}
            </button>
          }
        >
          {factorDetail.isError ? <div className="status-block error">{getErrorMessage(factorDetail.error)}</div> : null}
          {factorDetail.isPending && selectedId ? <div className="status-block loading">Loading factor detail...</div> : null}
          {factorDetail.data ? (
            <div className="stack">
              <MetricGrid metrics={(factorDetail.data.metrics as Record<string, unknown>) ?? {}} />
              <Sparkline
                title="Cumulative Returns"
                returns={(factorDetail.data.returns as Record<string, number>) ?? {}}
              />
              <JsonView value={factorDetail.data} />
            </div>
          ) : (
            <p className="muted">Select a factor to inspect it.</p>
          )}
        </SectionCard>
      </Panel>
    </Group>
  );
}

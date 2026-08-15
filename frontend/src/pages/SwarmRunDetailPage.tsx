import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Panel, Group } from "react-resizable-panels";
import { ResizeHandle } from "../components/ResizeHandle";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { api, getErrorMessage, getRunStatusView } from "../lib/api";
import { useSocketFeed } from "../lib/ws";

const LOG_PAGE_SIZE = 200;
const OUTPUT_PAGE_SIZE = 40;

function logKey(entry: Record<string, unknown>) {
  return `${String(entry.timestamp ?? "")}-${String(entry.message ?? entry.event ?? "")}-${String(entry.level ?? entry.type ?? "")}`;
}

function mergeLogEntries(existing: Record<string, unknown>[], incoming: Record<string, unknown>[]) {
  const merged = new Map<string, Record<string, unknown>>();
  for (const entry of [...existing, ...incoming]) {
    merged.set(logKey(entry), entry);
  }
  return [...merged.values()];
}

export function SwarmRunDetailPage() {
  const { runId = "" } = useParams();
  const queryClient = useQueryClient();
  const { events: socketEvents, status: socketStatus } = useSocketFeed();
  const [logOffset, setLogOffset] = useState(0);
  const [logTailBootstrap, setLogTailBootstrap] = useState(true);
  const [storedLogs, setStoredLogs] = useState<Record<string, unknown>[]>([]);
  const [factorPage, setFactorPage] = useState(0);
  const [strategyPage, setStrategyPage] = useState(0);
  const [stopRequested, setStopRequested] = useState(false);

  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
    enabled: Boolean(runId),
    refetchInterval: 5000,
  });
  const deskTrace = useQuery({
    queryKey: ["desk-trace", runId],
    queryFn: () => api.listTrace(20),
    refetchInterval: 15000,
  });
  const logs = useQuery({
    queryKey: ["run-logs", runId, logOffset, logTailBootstrap],
    queryFn: () =>
      api.getRunLogs(runId, { offset: logOffset, limit: LOG_PAGE_SIZE, tail: logTailBootstrap }),
    enabled: Boolean(runId),
    placeholderData: keepPreviousData,
    refetchInterval: run.data?.is_active ? 3000 : false,
  });
  const factors = useQuery({
    queryKey: ["run-factors", runId, factorPage],
    queryFn: () =>
      api.listFactors({ runId, offset: factorPage * OUTPUT_PAGE_SIZE, limit: OUTPUT_PAGE_SIZE }),
    enabled: Boolean(runId),
    placeholderData: keepPreviousData,
    refetchInterval: run.data?.is_active ? 8000 : false,
  });
  const strategies = useQuery({
    queryKey: ["run-strategies", runId, strategyPage],
    queryFn: () =>
      api.getStrategies({ runId, offset: strategyPage * OUTPUT_PAGE_SIZE, limit: OUTPUT_PAGE_SIZE }),
    enabled: Boolean(runId),
    placeholderData: keepPreviousData,
    refetchInterval: run.data?.is_active ? 8000 : false,
  });
  const stopMutation = useMutation({
    mutationFn: () => api.stopRun(runId),
    onMutate: () => {
      setStopRequested(true);
    },
    onError: () => {
      setStopRequested(false);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["run", runId] });
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void queryClient.invalidateQueries({ queryKey: ["run-logs", runId] });
    },
  });

  useEffect(() => {
    setLogOffset(0);
    setLogTailBootstrap(true);
    setStoredLogs([]);
    setFactorPage(0);
    setStrategyPage(0);
    setStopRequested(false);
  }, [runId]);

  useEffect(() => {
    if (!stopRequested || !run.data) {
      return;
    }
    const rawStatus = String(run.data.status ?? "").toLowerCase();
    if (["completed", "failed", "stopped"].includes(rawStatus) && !run.data.is_active) {
      setStopRequested(false);
    }
  }, [run.data, stopRequested]);

  useEffect(() => {
    if (!logs.data) {
      return;
    }
    setStoredLogs((current) => mergeLogEntries(logTailBootstrap ? [] : current, logs.data.items ?? []));
    setLogOffset((current) => {
      const nextOffset = typeof logs.data.next_offset === "number" ? logs.data.next_offset : current;
      return nextOffset > current ? nextOffset : current;
    });
    if (logTailBootstrap) {
      setLogTailBootstrap(false);
    }
  }, [logs.data, logTailBootstrap]);

  const liveEvents = useMemo(
    () => socketEvents.filter((event) => event.run_id === runId) as Record<string, unknown>[],
    [socketEvents, runId],
  );
  const mergedLogs = useMemo(() => {
    return mergeLogEntries(storedLogs, liveEvents)
      .sort((a, b) => String(a.timestamp || "").localeCompare(String(b.timestamp || "")))
      .slice(-500);
  }, [storedLogs, liveEvents]);
  const runStatus = getRunStatusView(run.data, { stopRequested });
  const factorItems = factors.data?.items ?? [];
  const strategyItems = strategies.data?.items ?? [];
  const hasNextFactorPage = (factors.data?.next_offset ?? 0) < (factors.data?.total ?? 0);
  const hasNextStrategyPage = (strategies.data?.next_offset ?? 0) < (strategies.data?.total ?? 0);
  const stopButtonLabel = stopMutation.isPending ? "Sending Stop..." : runStatus.isStopping ? "Stopping..." : runStatus.canStop ? "Stop Run" : runStatus.label;

  const logContainerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [mergedLogs]);

  return (
    <div className="page-grid">
      <SectionCard
        title={`Run Detail · ${runId}`}
        actions={
          <button
            className="button button-danger"
            onClick={() => stopMutation.mutate()}
            disabled={!runStatus.canStop || stopMutation.isPending || runStatus.isStopping}
          >
            {stopButtonLabel}
          </button>
        }
      >
        {run.isError ? <div className="status-block error">{getErrorMessage(run.error)}</div> : null}
        {stopMutation.error ? <div className="status-block error">{getErrorMessage(stopMutation.error)}</div> : null}
        {runStatus.isStopping ? (
          <div className="status-block loading">Stop requested. Waiting for the swarm worker to exit...</div>
        ) : null}
        <MetricGrid
          metrics={{
            status: runStatus.label,
            active: String(run.data?.is_active ?? false),
            factors: run.data?.result_counts?.factor_count ?? 0,
            strategies: run.data?.result_counts?.strategy_count ?? 0,
          }}
        />
        <JsonView value={run.data?.config ?? {}} maxLines={20} />
      </SectionCard>
      <SectionCard title="Research trace">
        <p className="muted">Causal chain from /api/v1/trace. Later rows cite the previous id.</p>
        {(deskTrace.data?.items ?? []).map((item) => (
          <div key={String(item.id)} className="list-row">
            <span>
              {String(item.action ?? "")} · {String(item.id ?? "").slice(0, 8)}
              {item.cites ? ` cites ${String(item.cites).slice(0, 8)}` : ""}
            </span>
            <span className="muted">{String(item.summary ?? item.error ?? "")}</span>
          </div>
        ))}
      </SectionCard>

      <Group orientation="horizontal" className="panel-container" style={{ flex: 1, minHeight: 450 }}>
        <Panel id="left-panel" defaultSize={50} minSize={20}>
          <SectionCard title="Live Logs" actions={<span className={`socket-status ${socketStatus}`}>Socket: {socketStatus}</span>}>
            {logs.isError ? <div className="status-block error">{getErrorMessage(logs.error)}</div> : null}
            {logs.isPending && !mergedLogs.length ? (
              <div className="status-block loading">Loading recent logs...</div>
            ) : null}
            <div className="log-panel" ref={logContainerRef}>
              {mergedLogs.map((entry, index) => (
                <div key={`${index}-${String(entry.timestamp ?? "")}`} className="log-line">
                  <span className="muted">{String(entry.timestamp ?? "--")}</span>
                  <strong className={`log-level-${String(entry.level ?? entry.type ?? "info").toLowerCase()}`}>
                    {String(entry.level ?? entry.type ?? "info")}
                  </strong>
                  <span>{String(entry.message ?? entry.event ?? "")}</span>
                </div>
              ))}
              {mergedLogs.length === 0 && <p className="muted">Waiting for logs...</p>}
            </div>
          </SectionCard>
        </Panel>

        <ResizeHandle />

        <Panel id="right-panel" defaultSize={50} minSize={20}>
          <SectionCard title="Run Output">
            <div className="stack">
              <div>
                <div className="panel-heading-row">
                  <h3>Factors</h3>
                  <div className="pagination-bar compact">
                    <button className="button" disabled={factorPage === 0} onClick={() => setFactorPage((page) => Math.max(0, page - 1))}>
                      Prev
                    </button>
                    <span className="pagination-summary">
                      Page {factorPage + 1}
                      {typeof factors.data?.total === "number" ? ` · ${factors.data.total}` : ""}
                    </span>
                    <button className="button" disabled={!hasNextFactorPage} onClick={() => setFactorPage((page) => page + 1)}>
                      Next
                    </button>
                  </div>
                </div>
                {factors.isError ? <div className="status-block error">{getErrorMessage(factors.error)}</div> : null}
                {factors.isPending && !factors.data ? <div className="status-block loading">Loading factor output...</div> : null}
                <div className="list compact">
                  {factorItems.map((factor) => (
                    <div key={factor.id} className="list-row">
                      <div>
                        <strong>{factor.id}</strong>
                        <p className="muted">{factor.hypothesis}</p>
                      </div>
                      <span>{factor.ic?.toFixed?.(4) ?? "-"}</span>
                    </div>
                  ))}
                  {!factors.isPending && !factorItems.length ? <p className="muted">No factors on this page.</p> : null}
                </div>
              </div>
              <div>
                <div className="panel-heading-row">
                  <h3>Strategies</h3>
                  <div className="pagination-bar compact">
                    <button className="button" disabled={strategyPage === 0} onClick={() => setStrategyPage((page) => Math.max(0, page - 1))}>
                      Prev
                    </button>
                    <span className="pagination-summary">
                      Page {strategyPage + 1}
                      {typeof strategies.data?.total === "number" ? ` · ${strategies.data.total}` : ""}
                    </span>
                    <button className="button" disabled={!hasNextStrategyPage} onClick={() => setStrategyPage((page) => page + 1)}>
                      Next
                    </button>
                  </div>
                </div>
                {strategies.isError ? <div className="status-block error">{getErrorMessage(strategies.error)}</div> : null}
                {strategies.isPending && !strategies.data ? (
                  <div className="status-block loading">Loading strategy output...</div>
                ) : null}
                <div className="list compact">
                  {strategyItems.map((strategy) => (
                    <div key={strategy.strategy_id} className="list-row">
                      <div>
                        <strong>{strategy.label ?? strategy.strategy_id}</strong>
                        <p className="muted">{strategy.strategy_mode}</p>
                      </div>
                      <span>{Number(strategy.metrics?.sharpe ?? 0).toFixed(4)}</span>
                    </div>
                  ))}
                  {!strategies.isPending && !strategyItems.length ? <p className="muted">No strategies on this page.</p> : null}
                </div>
              </div>
            </div>
          </SectionCard>
        </Panel>
      </Group>
    </div>
  );
}

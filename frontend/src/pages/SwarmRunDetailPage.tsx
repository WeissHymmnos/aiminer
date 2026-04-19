import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Panel, Group } from "react-resizable-panels";
import { ResizeHandle } from "../components/ResizeHandle";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import { useSocketFeed } from "../lib/ws";

export function SwarmRunDetailPage() {
  const { runId = "" } = useParams();
  const queryClient = useQueryClient();
  const { events: socketEvents } = useSocketFeed();
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
    enabled: Boolean(runId),
    refetchInterval: 5000,
  });
  const logs = useQuery({
    queryKey: ["run-logs", runId],
    queryFn: () => api.getRunLogs(runId, 0, 200, true),
    enabled: Boolean(runId),
    refetchInterval: 5000,
  });
  const factors = useQuery({
    queryKey: ["run-factors", runId],
    queryFn: () => api.listAllFactors(runId),
    enabled: Boolean(runId),
    refetchInterval: 8000,
  });
  const strategies = useQuery({
    queryKey: ["run-strategies", runId],
    queryFn: () => api.listAllStrategies(runId),
    enabled: Boolean(runId),
    refetchInterval: 8000,
  });
  const stopMutation = useMutation({
    mutationFn: () => api.stopRun(runId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["run", runId] });
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });

  const liveEvents = useMemo(
    () => socketEvents.filter((event) => event.run_id === runId),
    [socketEvents, runId],
  );
  const mergedLogs = useMemo(() => {
    const existingKeys = new Set<string>();
    const merged = [...(logs.data?.items ?? []), ...liveEvents].filter((entry) => {
      // Use a more efficient key than JSON.stringify
      const key = `${entry.timestamp}-${entry.message || entry.event}-${entry.level || entry.type}`;
      if (existingKeys.has(key)) {
        return false;
      }
      existingKeys.add(key);
      return true;
    });
    // Sort by timestamp if available to ensure order
    return merged.sort((a, b) => String(a.timestamp || "").localeCompare(String(b.timestamp || ""))).slice(-500);
  }, [logs.data?.items, liveEvents]);

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
          <button className="button button-danger" onClick={() => stopMutation.mutate()}>
            Stop Run
          </button>
        }
      >
        <MetricGrid
          metrics={{
            status: run.data?.status ?? "loading",
            active: String(run.data?.is_active ?? false),
            factors: run.data?.result_counts?.factor_count ?? 0,
            strategies: run.data?.result_counts?.strategy_count ?? 0,
          }}
        />
        <JsonView value={run.data?.config ?? {}} maxLines={20} />
      </SectionCard>

      <Group orientation="horizontal" className="panel-container" style={{ flex: 1, minHeight: 450 }}>
        <Panel id="left-panel" defaultSize={50} minSize={20}>
          <SectionCard title="Live Logs">
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
                <h3>Factors</h3>
                <div className="list compact">
                  {(factors.data ?? []).map((factor) => (
                    <div key={factor.id} className="list-row">
                      <div>
                        <strong>{factor.id}</strong>
                        <p className="muted">{factor.hypothesis}</p>
                      </div>
                      <span>{factor.ic?.toFixed?.(4) ?? "-"}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3>Strategies</h3>
                <div className="list compact">
                  {(strategies.data ?? []).map((strategy) => (
                    <div key={strategy.strategy_id} className="list-row">
                      <div>
                        <strong>{strategy.label ?? strategy.strategy_id}</strong>
                        <p className="muted">{strategy.strategy_mode}</p>
                      </div>
                      <span>{Number(strategy.metrics?.sharpe ?? 0).toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </SectionCard>
        </Panel>
      </Group>
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import { useSocketFeed } from "../lib/ws";

export function SwarmRunDetailPage() {
  const { runId = "" } = useParams();
  const queryClient = useQueryClient();
  const socketEvents = useSocketFeed();
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
    enabled: Boolean(runId),
    refetchInterval: 5000,
  });
  const logs = useQuery({
    queryKey: ["run-logs", runId],
    queryFn: () => api.getRunLogs(runId, 0, 200),
    enabled: Boolean(runId),
    refetchInterval: 5000,
  });
  const factors = useQuery({
    queryKey: ["run-factors", runId],
    queryFn: () => api.listFactors(runId),
    enabled: Boolean(runId),
    refetchInterval: 8000,
  });
  const strategies = useQuery({
    queryKey: ["run-strategies", runId],
    queryFn: () => api.getStrategies(runId),
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
    const existing = new Set<string>();
    const merged = [...(logs.data?.items ?? []), ...liveEvents].filter((entry) => {
      const key = JSON.stringify(entry);
      if (existing.has(key)) {
        return false;
      }
      existing.add(key);
      return true;
    });
    return merged.slice(-200);
  }, [logs.data?.items, liveEvents]);

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
        <JsonView value={run.data?.config ?? {}} />
      </SectionCard>

      <div className="page-grid two-col">
        <SectionCard title="Live Logs">
          <div className="log-panel">
            {mergedLogs.map((entry, index) => (
              <div key={`${index}-${String(entry.timestamp ?? "")}`} className="log-line">
                <span className="muted">{String(entry.timestamp ?? "--")}</span>
                <strong>{String(entry.level ?? entry.type ?? "info")}</strong>
                <span>{String(entry.message ?? entry.event ?? "")}</span>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Run Output">
          <div className="stack">
            <div>
              <h3>Factors</h3>
              <div className="list compact">
                {(factors.data?.items ?? []).map((factor) => (
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
                {(strategies.data?.items ?? []).map((strategy) => (
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
      </div>
    </div>
  );
}

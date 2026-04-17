import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import type { SwarmRunSummary } from "../types";

const defaultRoles = [
  "专注Hurst指数与分形维度的动量专家",
  "利用高频量价相关性挖掘的量价专家",
  "基于宏观周期切换的行业中性专家",
];

export function SwarmRunsPage() {
  const [form, setForm] = useState({
    iterations: "8",
    mode: "ricequant",
    data_backend: "ricequant",
    engine: "polars",
    llm_provider: "kimi",
    llm_model: "kimi-k2-turbo-preview",
    llm_base_url: "",
    embedding_provider: "openai",
    market_mode: "single",
    market_profile: "cn_stock",
    market_profiles: "cn_stock",
    local_data_path: "",
    local_data_layout: "auto",
    market_start: "2017-01-01",
    market_end: "2020-10-31",
    parallel: true,
    roles: defaultRoles.join("\n"),
  });
  const queryClient = useQueryClient();
  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: api.listRuns,
    refetchInterval: 5000,
  });
  const swarmStatus = useQuery({
    queryKey: ["swarm-status"],
    queryFn: api.swarmStatus,
    refetchInterval: 5000,
  });
  const startMutation = useMutation({
    mutationFn: api.startRun,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void queryClient.invalidateQueries({ queryKey: ["swarm-status"] });
    },
  });

  const payload = useMemo(
    () => ({
      iterations: Number(form.iterations || 1),
      mode: form.mode,
      data_backend: form.data_backend,
      engine: form.engine,
      llm_provider: form.llm_provider,
      llm_model: form.llm_model,
      llm_base_url: form.llm_base_url || null,
      embedding_provider: form.embedding_provider || null,
      market_mode: form.market_mode,
      market_profile: form.market_profile,
      market_profiles: form.market_profiles
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      local_data_path: form.local_data_path || null,
      local_data_layout: form.local_data_layout,
      market_start: form.market_start,
      market_end: form.market_end,
      parallel: form.parallel,
      roles: form.roles
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean),
    }),
    [form],
  );

  return (
    <div className="page-grid two-col">
      <SectionCard
        title="Run Launcher"
        actions={
          <button
            className="button"
            onClick={() => startMutation.mutate(payload)}
            disabled={startMutation.isPending}
          >
            Start Run
          </button>
        }
      >
        <div className="metric-grid">
          <div className="metric">
            <span>Running</span>
            <strong>{swarmStatus.data?.running_count ?? 0}</strong>
          </div>
          <div className="metric">
            <span>Concurrency Limit</span>
            <strong>{swarmStatus.data?.max_concurrent ?? "-"}</strong>
          </div>
        </div>
        <div className="page-grid two-col">
          <label className="field">
            Iterations
            <input value={form.iterations} onChange={(event) => setForm({ ...form, iterations: event.target.value })} />
          </label>
          <label className="field">
            Engine
            <input value={form.engine} onChange={(event) => setForm({ ...form, engine: event.target.value })} />
          </label>
          <label className="field">
            LLM Provider
            <input value={form.llm_provider} onChange={(event) => setForm({ ...form, llm_provider: event.target.value })} />
          </label>
          <label className="field">
            LLM Model
            <input value={form.llm_model} onChange={(event) => setForm({ ...form, llm_model: event.target.value })} />
          </label>
          <label className="field">
            Market Profile
            <input value={form.market_profile} onChange={(event) => setForm({ ...form, market_profile: event.target.value })} />
          </label>
          <label className="field">
            Market Profiles
            <input value={form.market_profiles} onChange={(event) => setForm({ ...form, market_profiles: event.target.value })} />
          </label>
        </div>
        <label className="field">
          Roles
          <textarea rows={10} value={form.roles} onChange={(event) => setForm({ ...form, roles: event.target.value })} />
        </label>
        <label className="field">
          <span>Parallel Execution</span>
          <input
            type="checkbox"
            checked={form.parallel}
            onChange={(event) => setForm({ ...form, parallel: event.target.checked })}
          />
        </label>
        {startMutation.error ? (
          <p className="error-text">{(startMutation.error as Error).message}</p>
        ) : null}
      </SectionCard>

      <SectionCard title="Swarm Runs">
        <div className="list">
          {(runs.data?.items ?? []).map((run: SwarmRunSummary) => (
            <Link key={run.run_id} className="list-row" to={`/runs/${run.run_id}`}>
              <div>
                <strong>{run.run_id}</strong>
                <p className="muted">{run.status}</p>
              </div>
              <div className="align-right">
                <div>{run.result_counts?.factor_count ?? 0} factors</div>
                <div className="muted">{run.result_counts?.strategy_count ?? 0} strategies</div>
              </div>
            </Link>
          ))}
          {!runs.data?.items?.length ? <p className="muted">No runs yet.</p> : null}
        </div>
      </SectionCard>
    </div>
  );
}

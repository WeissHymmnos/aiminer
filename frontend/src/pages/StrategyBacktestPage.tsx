import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { Sparkline } from "../components/Sparkline";
import { api } from "../lib/api";

const defaultConfig = {
  label: "Web strategy",
  strategy_mode: "cross_sectional",
  direction: "long_short",
  selection_rule: "top_bottom_n",
  rebalance_freq: "daily",
  top_n: 20,
  bottom_n: 20,
  long_threshold: 0.75,
  short_threshold: 0.25,
  exit_threshold: 0.5,
  max_positions: 40,
  max_weight_per_position: 0.05,
  min_holding_days: 2,
  commission_bps: 5,
  slippage_bps: 5,
  market: "000300.XSHG",
  start_date: "2017-01-01",
  end_date: "2020-10-31",
  engine: "polars",
};

export function StrategyBacktestPage() {
  const [expression, setExpression] = useState("Rank(Delta($close, 5))");
  const [advancedMode, setAdvancedMode] = useState(false);
  const [strategyJson, setStrategyJson] = useState(JSON.stringify(defaultConfig, null, 2));
  const [form, setForm] = useState(defaultConfig);
  const [formError, setFormError] = useState("");
  const history = useQuery({
    queryKey: ["strategy-history"],
    queryFn: api.strategyHistory,
  });
  const runMutation = useMutation({
    mutationFn: api.runStrategy,
    onError: (error) => setFormError((error as Error).message),
  });

  const strategyConfig = useMemo(() => {
    if (advancedMode) {
      try {
        setFormError("");
        return JSON.parse(strategyJson) as Record<string, unknown>;
      } catch {
        return null;
      }
    }
    return form;
  }, [advancedMode, strategyJson, form]);

  function run() {
    if (!strategyConfig) {
      setFormError("Strategy JSON is invalid.");
      return;
    }
    runMutation.mutate({
      expression,
      strategy_config: strategyConfig,
      data_backend: "ricequant",
      market_profile: "cn_stock",
      market_mode: "single",
      market_profiles: ["cn_stock"],
      local_data_path: "",
      local_data_layout: "auto",
    });
  }

  return (
    <div className="page-grid two-col">
      <SectionCard
        title="Strategy Backtester"
        actions={<button className="button" onClick={run}>Run Strategy</button>}
      >
        <label className="field">
          Signal Expression
          <textarea value={expression} onChange={(event) => setExpression(event.target.value)} rows={5} />
        </label>
        <label className="field">
          <span>Advanced JSON Mode</span>
          <input
            type="checkbox"
            checked={advancedMode}
            onChange={(event) => setAdvancedMode(event.target.checked)}
          />
        </label>
        {advancedMode ? (
          <label className="field">
            Strategy JSON
            <textarea value={strategyJson} onChange={(event) => setStrategyJson(event.target.value)} rows={16} />
          </label>
        ) : (
          <div className="page-grid two-col">
            <label className="field">
              Label
              <input value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} />
            </label>
            <label className="field">
              Mode
              <input value={form.strategy_mode} onChange={(event) => setForm({ ...form, strategy_mode: event.target.value })} />
            </label>
            <label className="field">
              Direction
              <input value={form.direction} onChange={(event) => setForm({ ...form, direction: event.target.value })} />
            </label>
            <label className="field">
              Rule
              <input value={form.selection_rule} onChange={(event) => setForm({ ...form, selection_rule: event.target.value })} />
            </label>
            <label className="field">
              Top N
              <input value={String(form.top_n)} onChange={(event) => setForm({ ...form, top_n: Number(event.target.value) || 0 })} />
            </label>
            <label className="field">
              Bottom N
              <input value={String(form.bottom_n)} onChange={(event) => setForm({ ...form, bottom_n: Number(event.target.value) || 0 })} />
            </label>
          </div>
        )}
        {formError ? <p className="error-text">{formError}</p> : null}
        {runMutation.data ? (
          <div className="stack">
            <MetricGrid metrics={(runMutation.data.metrics as Record<string, unknown>) ?? {}} />
            <Sparkline
              title="Strategy Returns"
              returns={(runMutation.data.daily_returns as Record<string, number>) ?? {}}
            />
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Strategy Results">
        <div className="list">
          {(history.data ?? []).map((entry, index) => (
            <div key={index} className="list-row">
              <div>
                <strong>{String(entry.label ?? entry.strategy_id ?? "strategy")}</strong>
                <p className="muted">{String(entry.ran_at ?? "")}</p>
              </div>
              <span>{String(entry.return_points ?? 0)} pts</span>
            </div>
          ))}
        </div>
        {runMutation.data ? <JsonView value={runMutation.data} /> : null}
      </SectionCard>
    </div>
  );
}

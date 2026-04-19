import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Panel, Group } from "react-resizable-panels";
import { ResizeHandle } from "../components/ResizeHandle";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { Sparkline } from "../components/Sparkline";
import { api } from "../lib/api";
import { strategyTemplates, type StrategyTemplateConfig } from "../lib/strategyTemplates";

const templateKeys = Object.keys(strategyTemplates);
const defaultTemplateKey = "cs_top_bottom";
const backendOptions = ["ricequant", "qlib", "local"];
const marketModeOptions = ["single", "multi"];
const localDataLayoutOptions = ["auto", "qlib", "contracts", "dominant"];
const rebalanceOptions = ["daily", "weekly", "monthly"];
const directionOptions = ["long_only", "long_short", "long_flat"];
const strategyModeOptions = ["cross_sectional", "time_series"];
const selectionRuleOptions = ["top_n", "bottom_n", "top_bottom_n", "threshold"];
const engineOptions = ["polars", "pandas"];

const defaultConfig = strategyTemplates[defaultTemplateKey];

const defaultRunSettings = {
  data_backend: "ricequant",
  market_profile: "cn_stock",
  market_mode: "single",
  market_profiles: "cn_stock",
  local_data_path: "",
  local_data_layout: "auto",
};

function numberValue(value: number | null) {
  return value === null ? "" : String(value);
}

function parseNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export function StrategyBacktestPage() {
  const [expression, setExpression] = useState("Rank(Delta($close, 5))");
  const [templateKey, setTemplateKey] = useState(defaultTemplateKey);
  const [advancedMode, setAdvancedMode] = useState(false);
  const [strategyJson, setStrategyJson] = useState(JSON.stringify(defaultConfig, null, 2));
  const [form, setForm] = useState<StrategyTemplateConfig>(defaultConfig);
  const [runSettings, setRunSettings] = useState(defaultRunSettings);
  const [formError, setFormError] = useState("");
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const history = useQuery({
    queryKey: ["strategy-history"],
    queryFn: api.strategyHistory,
  });
  const selectedStrategy = useQuery({
    queryKey: ["strategy-detail", selectedStrategyId],
    queryFn: () => api.getStrategy(selectedStrategyId!),
    enabled: Boolean(selectedStrategyId),
  });
  const runMutation = useMutation({
    mutationFn: api.runStrategy,
    onSuccess: (data) => {
      setFormError("");
      setSelectedStrategyId(String(data.strategy_id ?? ""));
      void queryClient.invalidateQueries({ queryKey: ["strategy-history"] });
    },
    onError: (error) => setFormError((error as Error).message),
  });
  const detail = selectedStrategy.data ?? runMutation.data ?? null;
  const ricequantHint = formError.includes("RiceQuant")
    ? "RiceQuant 远端链路断了。可以稍后重试，或把 Data Backend 切到 local / qlib。"
    : "";

  const strategyConfig = useMemo(() => {
    if (advancedMode) {
      try {
        return JSON.parse(strategyJson) as Record<string, unknown>;
      } catch {
        return null;
      }
    }
    return form;
  }, [advancedMode, strategyJson, form]);

  function loadTemplate(nextKey: string) {
    const next = strategyTemplates[nextKey];
    setTemplateKey(nextKey);
    setForm(next);
    setStrategyJson(JSON.stringify(next, null, 2));
    setAdvancedMode(false);
    setFormError("");
  }

  function syncJson() {
    setStrategyJson(JSON.stringify(form, null, 2));
    setFormError("");
  }

  function run() {
    if (!strategyConfig) {
      setFormError("Strategy JSON is invalid.");
      return;
    }
    runMutation.mutate({
      expression,
      strategy_config: strategyConfig,
      data_backend: runSettings.data_backend,
      market_profile: runSettings.market_profile,
      market_mode: runSettings.market_mode,
      market_profiles: runSettings.market_profiles
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      local_data_path: runSettings.local_data_path || null,
      local_data_layout: runSettings.local_data_layout,
    });
  }

  return (
    <Group orientation="horizontal" className="panel-container">
      <Panel id="left-panel" defaultSize={50} minSize={20}>
      <SectionCard
        title="Strategy Backtester"
        actions={
          <div className="button-group">
            <button className="button" onClick={() => loadTemplate(templateKey)} disabled={runMutation.isPending}>
              Load Template
            </button>
            <button className="button" onClick={syncJson} disabled={runMutation.isPending}>
              Sync JSON
            </button>
            <button className="button" onClick={run} disabled={runMutation.isPending}>
              Run Strategy
            </button>
          </div>
        }
      >
        <label className="field">
          Signal Expression
          <textarea value={expression} onChange={(event) => setExpression(event.target.value)} rows={5} />
        </label>
        <div className="page-grid two-col">
          <label className="field">
            Template Key
            <select value={templateKey} onChange={(event) => setTemplateKey(event.target.value)}>
              {templateKeys.map((key) => (
                <option key={key} value={key}>
                  {key}
                </option>
              ))}
            </select>
          </label>
          <label className="field-toggle">
            <span>Advanced JSON Mode</span>
            <input
              type="checkbox"
              checked={advancedMode}
              onChange={(event) => setAdvancedMode(event.target.checked)}
            />
          </label>
        </div>
        <div className="page-grid two-col">
          <label className="field">
            Data Backend
            <select
              value={runSettings.data_backend}
              onChange={(event) => setRunSettings({ ...runSettings, data_backend: event.target.value })}
            >
              {backendOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Market Mode
            <select
              value={runSettings.market_mode}
              onChange={(event) => setRunSettings({ ...runSettings, market_mode: event.target.value })}
            >
              {marketModeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Market Profile
            <input
              value={runSettings.market_profile}
              onChange={(event) => setRunSettings({ ...runSettings, market_profile: event.target.value })}
            />
          </label>
          <label className="field">
            Market Profiles
            <input
              value={runSettings.market_profiles}
              onChange={(event) => setRunSettings({ ...runSettings, market_profiles: event.target.value })}
            />
          </label>
          <label className="field">
            Local Data Path
            <input
              value={runSettings.local_data_path}
              onChange={(event) => setRunSettings({ ...runSettings, local_data_path: event.target.value })}
            />
          </label>
          <label className="field">
            Local Data Layout
            <select
              value={runSettings.local_data_layout}
              onChange={(event) => setRunSettings({ ...runSettings, local_data_layout: event.target.value })}
            >
              {localDataLayoutOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>
        {advancedMode ? (
          <label className="field">
            Strategy JSON
            <textarea value={strategyJson} onChange={(event) => setStrategyJson(event.target.value)} rows={18} />
          </label>
        ) : (
          <div className="page-grid two-col">
            <label className="field">
              Label
              <input value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} />
            </label>
            <label className="field">
              Strategy Mode
              <select
                value={form.strategy_mode}
                onChange={(event) =>
                  setForm({
                    ...form,
                    strategy_mode: event.target.value as StrategyTemplateConfig["strategy_mode"],
                  })
                }
              >
                {strategyModeOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Direction
              <select
                value={form.direction}
                onChange={(event) =>
                  setForm({
                    ...form,
                    direction: event.target.value as StrategyTemplateConfig["direction"],
                  })
                }
              >
                {directionOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Selection Rule
              <select
                value={form.selection_rule}
                onChange={(event) =>
                  setForm({
                    ...form,
                    selection_rule: event.target.value as StrategyTemplateConfig["selection_rule"],
                  })
                }
              >
                {selectionRuleOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Rebalance Frequency
              <select
                value={form.rebalance_freq}
                onChange={(event) =>
                  setForm({
                    ...form,
                    rebalance_freq: event.target.value as StrategyTemplateConfig["rebalance_freq"],
                  })
                }
              >
                {rebalanceOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Engine
              <select
                value={form.engine}
                onChange={(event) =>
                  setForm({
                    ...form,
                    engine: event.target.value as StrategyTemplateConfig["engine"],
                  })
                }
              >
                {engineOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Top N
              <input
                value={numberValue(form.top_n)}
                onChange={(event) => setForm({ ...form, top_n: parseNumber(event.target.value) })}
              />
            </label>
            <label className="field">
              Bottom N
              <input
                value={numberValue(form.bottom_n)}
                onChange={(event) => setForm({ ...form, bottom_n: parseNumber(event.target.value) })}
              />
            </label>
            <label className="field">
              Long Threshold
              <input
                value={numberValue(form.long_threshold)}
                onChange={(event) => setForm({ ...form, long_threshold: parseNumber(event.target.value) })}
              />
            </label>
            <label className="field">
              Short Threshold
              <input
                value={numberValue(form.short_threshold)}
                onChange={(event) => setForm({ ...form, short_threshold: parseNumber(event.target.value) })}
              />
            </label>
            <label className="field">
              Exit Threshold
              <input
                value={numberValue(form.exit_threshold)}
                onChange={(event) => setForm({ ...form, exit_threshold: parseNumber(event.target.value) })}
              />
            </label>
            <label className="field">
              Max Positions
              <input
                value={numberValue(form.max_positions)}
                onChange={(event) => setForm({ ...form, max_positions: parseNumber(event.target.value) })}
              />
            </label>
            <label className="field">
              Max Weight / Position
              <input
                value={String(form.max_weight_per_position)}
                onChange={(event) =>
                  setForm({
                    ...form,
                    max_weight_per_position: Number(event.target.value) || 0,
                  })
                }
              />
            </label>
            <label className="field">
              Min Holding Days
              <input
                value={String(form.min_holding_days)}
                onChange={(event) =>
                  setForm({ ...form, min_holding_days: Number(event.target.value) || 0 })
                }
              />
            </label>
            <label className="field">
              Commission Bps
              <input
                value={String(form.commission_bps)}
                onChange={(event) =>
                  setForm({ ...form, commission_bps: Number(event.target.value) || 0 })
                }
              />
            </label>
            <label className="field">
              Slippage Bps
              <input
                value={String(form.slippage_bps)}
                onChange={(event) =>
                  setForm({ ...form, slippage_bps: Number(event.target.value) || 0 })
                }
              />
            </label>
            <label className="field">
              Market
              <input value={form.market} onChange={(event) => setForm({ ...form, market: event.target.value })} />
            </label>
            <label className="field">
              Start Date
              <input
                value={form.start_date}
                onChange={(event) => setForm({ ...form, start_date: event.target.value })}
              />
            </label>
            <label className="field">
              End Date
              <input value={form.end_date} onChange={(event) => setForm({ ...form, end_date: event.target.value })} />
            </label>
          </div>
        )}
        {formError ? <p className="error-text">{formError}</p> : null}
        {ricequantHint ? <p className="muted">{ricequantHint}</p> : null}
        {detail ? (
          <div className="stack">
            <MetricGrid metrics={(detail.metrics as Record<string, unknown>) ?? {}} />
            <Sparkline
              title="Strategy Returns"
              returns={(detail.daily_returns as Record<string, number>) ?? {}}
            />
          </div>
        ) : null}
      </SectionCard>
      </Panel>
      <ResizeHandle />
      <Panel id="right-panel" defaultSize={50} minSize={20}>
      <SectionCard title="Strategy Results">
        <label className="field">
          Strategy JSON
          <textarea value={strategyJson} onChange={(event) => setStrategyJson(event.target.value)} rows={16} />
        </label>
        <div className="list">
          {(history.data ?? []).map((entry, index) => (
            <button
              type="button"
              key={index}
              className={`list-row button-reset ${selectedStrategyId === String(entry.strategy_id ?? "") ? "selected" : ""}`}
              onClick={() => setSelectedStrategyId(String(entry.strategy_id ?? ""))}
            >
              <div>
                <strong>{String(entry.label ?? entry.strategy_id ?? "strategy")}</strong>
                <p className="muted">{String(entry.ran_at ?? "")}</p>
              </div>
              <span>{String(entry.return_points ?? 0)} pts</span>
            </button>
          ))}
        </div>
        {selectedStrategy.isLoading ? <p className="muted">Loading strategy details...</p> : null}
        {detail ? <JsonView value={detail} /> : null}
      </SectionCard>
      </Panel>
    </Group>
  );
}

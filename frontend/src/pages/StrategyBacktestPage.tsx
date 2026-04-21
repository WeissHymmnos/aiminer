import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { Panel, Group, type PanelImperativeHandle } from "react-resizable-panels";
import { CodeEditor } from "../components/CodeEditor";
import { ResizeHandle } from "../components/ResizeHandle";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { Sparkline } from "../components/Sparkline";
import { api, getErrorMessage } from "../lib/api";
import { strategyTemplates, type StrategyTemplateConfig } from "../lib/strategyTemplates";
import type { FactorSummary } from "../types";

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
const SEED_PAGE_SIZE = 40;

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

function coerceEnum<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === "string" && allowed.includes(value as T) ? (value as T) : fallback;
}

function coerceNullableNumber(value: unknown, fallback: number | null) {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function coerceNumber(value: unknown, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeStrategyConfig(config: Record<string, unknown>): StrategyTemplateConfig {
  return {
    label: typeof config.label === "string" ? config.label : defaultConfig.label,
    strategy_mode: coerceEnum(
      config.strategy_mode,
      strategyModeOptions as readonly StrategyTemplateConfig["strategy_mode"][],
      defaultConfig.strategy_mode,
    ),
    direction: coerceEnum(
      config.direction,
      directionOptions as readonly StrategyTemplateConfig["direction"][],
      defaultConfig.direction,
    ),
    selection_rule: coerceEnum(
      config.selection_rule,
      selectionRuleOptions as readonly StrategyTemplateConfig["selection_rule"][],
      defaultConfig.selection_rule,
    ),
    rebalance_freq: coerceEnum(
      config.rebalance_freq,
      rebalanceOptions as readonly StrategyTemplateConfig["rebalance_freq"][],
      defaultConfig.rebalance_freq,
    ),
    top_n: coerceNullableNumber(config.top_n, defaultConfig.top_n),
    bottom_n: coerceNullableNumber(config.bottom_n, defaultConfig.bottom_n),
    long_threshold: coerceNullableNumber(config.long_threshold, defaultConfig.long_threshold),
    short_threshold: coerceNullableNumber(config.short_threshold, defaultConfig.short_threshold),
    exit_threshold: coerceNullableNumber(config.exit_threshold, defaultConfig.exit_threshold),
    max_positions: coerceNullableNumber(config.max_positions, defaultConfig.max_positions),
    max_weight_per_position: coerceNumber(
      config.max_weight_per_position,
      defaultConfig.max_weight_per_position,
    ),
    min_holding_days: coerceNumber(config.min_holding_days, defaultConfig.min_holding_days),
    commission_bps: coerceNumber(config.commission_bps, defaultConfig.commission_bps),
    slippage_bps: coerceNumber(config.slippage_bps, defaultConfig.slippage_bps),
    market: typeof config.market === "string" ? config.market : defaultConfig.market,
    start_date: typeof config.start_date === "string" ? config.start_date : defaultConfig.start_date,
    end_date: typeof config.end_date === "string" ? config.end_date : defaultConfig.end_date,
    engine: coerceEnum(
      config.engine,
      engineOptions as readonly StrategyTemplateConfig["engine"][],
      defaultConfig.engine,
    ),
  };
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
  const [selectedFactorId, setSelectedFactorId] = useState<string | null>(null);
  const [seedPage, setSeedPage] = useState(0);
  const [detailCollapsed, setDetailCollapsed] = useState(false);
  const detailPanelRef = useRef<PanelImperativeHandle | null>(null);
  const queryClient = useQueryClient();
  const seedOffset = seedPage * SEED_PAGE_SIZE;
  const factorSeeds = useQuery({
    queryKey: ["strategy-seed-factors", seedOffset, SEED_PAGE_SIZE],
    queryFn: () => api.listFactors({ offset: seedOffset, limit: SEED_PAGE_SIZE }),
    placeholderData: keepPreviousData,
    refetchInterval: 10000,
  });
  const selectedFactor = useQuery({
    queryKey: ["strategy-seed-factor", selectedFactorId],
    queryFn: () => api.getFactor(selectedFactorId!),
    enabled: Boolean(selectedFactorId),
  });
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
  const deleteMutation = useMutation({
    mutationFn: api.deleteStrategy,
    onSuccess: (_, strategyId) => {
      if (selectedStrategyId === strategyId) {
        setSelectedStrategyId(null);
      }
      void queryClient.invalidateQueries({ queryKey: ["strategy-history"] });
    },
    onError: (error) => setFormError((error as Error).message),
  });
  const selectedStrategyData = selectedStrategy.data ?? null;
  const selectedStrategyDetailId = String(selectedStrategyData?.strategy_id ?? "");
  const detail = selectedStrategyId
    ? selectedStrategyData && (!selectedStrategyDetailId || selectedStrategyDetailId === selectedStrategyId)
      ? selectedStrategyData
      : null
    : runMutation.data ?? null;
  const ricequantHint = formError.includes("RiceQuant")
    ? "RiceQuant 远端链路断了。可以稍后重试，或把 Data Backend 切到 local / qlib。"
    : "";
  const seedFactors = useMemo(
    () => (factorSeeds.data?.items ?? []).filter((factor: FactorSummary) => Boolean(factor.best_strategy_id)),
    [factorSeeds.data?.items],
  );
  const selectedBestStrategy = (selectedFactor.data?.best_strategy as Record<string, unknown> | undefined) ?? null;
  const hasNextSeedPage = (factorSeeds.data?.next_offset ?? 0) < (factorSeeds.data?.total ?? 0);

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

  function applySeed(mode: "expression" | "strategy" | "both") {
    if (!selectedFactor.data || !selectedBestStrategy) {
      return;
    }
    const nextExpression = String(selectedFactor.data.code ?? "").trim();
    const rawConfig = (selectedBestStrategy.strategy_config as Record<string, unknown> | undefined) ?? null;
    if ((mode === "expression" || mode === "both") && nextExpression) {
      setExpression(nextExpression);
    }
    if ((mode === "strategy" || mode === "both") && rawConfig) {
      const normalized = normalizeStrategyConfig(rawConfig);
      setForm(normalized);
      setStrategyJson(JSON.stringify(rawConfig, null, 2));
      setRunSettings((prev) => ({
        ...prev,
        data_backend:
          typeof selectedBestStrategy.data_backend === "string"
            ? selectedBestStrategy.data_backend
            : typeof selectedFactor.data.data_backend === "string"
              ? String(selectedFactor.data.data_backend)
              : prev.data_backend,
        market_profile:
          typeof selectedBestStrategy.market_profile === "string"
            ? selectedBestStrategy.market_profile
            : typeof selectedFactor.data.market_profile === "string"
              ? String(selectedFactor.data.market_profile)
              : prev.market_profile,
        market_mode:
          typeof selectedBestStrategy.market_mode === "string"
            ? selectedBestStrategy.market_mode
            : typeof selectedFactor.data.market_mode === "string"
              ? String(selectedFactor.data.market_mode)
              : prev.market_mode,
      }));
    }
    setFormError("");
  }

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
            <button
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
              {detailCollapsed ? "Show Results" : "Hide Results"}
            </button>
          </div>
        }
      >
        <label className="field">
          Signal Expression
          <CodeEditor value={expression} onChange={setExpression} language="python" height={180} />
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
            <CodeEditor value={strategyJson} onChange={setStrategyJson} language="json" height={380} />
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
        {runMutation.error ? <div className="status-block error">{getErrorMessage(runMutation.error)}</div> : null}
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
      <Panel
        id="right-panel"
        defaultSize={50}
        minSize={20}
        collapsible
        collapsedSize={0}
        panelRef={detailPanelRef}
        onResize={(size) => setDetailCollapsed(size.asPercentage <= 0.1)}
      >
      <SectionCard
        title="Strategy Results"
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
        <div className="field">
          <div className="panel-heading-row">
            <strong>Agent Execution Seeds</strong>
            <span className="muted">{seedFactors.length} factors on page {seedPage + 1}</span>
          </div>
          {factorSeeds.isPending && !factorSeeds.data ? (
            <div className="status-block loading">Loading strategy seeds...</div>
          ) : null}
          {factorSeeds.isError ? <div className="status-block error">{getErrorMessage(factorSeeds.error)}</div> : null}
          <div className="list compact">
            {seedFactors.map((factor: FactorSummary) => (
              <button
                key={factor.id}
                type="button"
                className={`list-row button-reset ${selectedFactorId === factor.id ? "selected" : ""}`}
                onClick={() => setSelectedFactorId((prev) => (prev === factor.id ? null : factor.id))}
              >
                <div>
                  <strong>{factor.id}</strong>
                  <p className="muted">{factor.hypothesis}</p>
                </div>
                <div className="align-right">
                  <div>{factor.ic?.toFixed?.(4) ?? "-"}</div>
                  <div className="muted">score {Number(factor.selection_score ?? 0).toFixed(3)}</div>
                </div>
              </button>
            ))}
            {!factorSeeds.isPending && !seedFactors.length ? (
              <p className="muted">No factor with a persisted best strategy on this page.</p>
            ) : null}
          </div>
          <div className="pagination-bar">
            <button className="button" disabled={seedPage === 0} onClick={() => setSeedPage((page) => Math.max(0, page - 1))}>
              Prev
            </button>
            <span className="pagination-summary">
              Page {seedPage + 1}
              {typeof factorSeeds.data?.total === "number" ? ` · ${factorSeeds.data.total} factors` : ""}
            </span>
            <button className="button" disabled={!hasNextSeedPage} onClick={() => setSeedPage((page) => page + 1)}>
              Next
            </button>
          </div>
        </div>
        {selectedFactor.isError ? <div className="status-block error">{getErrorMessage(selectedFactor.error)}</div> : null}
        {selectedFactor.isLoading ? <p className="muted">Loading factor strategy seed...</p> : null}
        {selectedFactor.data && selectedBestStrategy ? (
          <div className="subtle-card">
            <div className="panel-heading-row">
              <div>
                <strong>{String(selectedBestStrategy.label ?? selectedBestStrategy.strategy_id ?? "best strategy")}</strong>
                <p className="muted">
                  Source factor {String(selectedFactor.data.id ?? "")}
                  {selectedFactor.data.hypothesis ? ` · ${String(selectedFactor.data.hypothesis)}` : ""}
                </p>
              </div>
              <div className="pill-row">
                {selectedBestStrategy.template_name ? (
                  <span className="pill">{String(selectedBestStrategy.template_name)}</span>
                ) : null}
                <span className="pill">{String(selectedFactor.data.execution_style ?? "execution")}</span>
                <span className="pill">score {Number(selectedBestStrategy.selection_score ?? 0).toFixed(3)}</span>
                {selectedBestStrategy.is_primary ? <span className="pill">primary</span> : null}
              </div>
            </div>
            <div className="button-group wrap">
              <button type="button" className="button" onClick={() => applySeed("expression")}>
                Use Expression
              </button>
              <button type="button" className="button" onClick={() => applySeed("strategy")}>
                Use Strategy
              </button>
              <button type="button" className="button" onClick={() => applySeed("both")}>
                Use Both
              </button>
            </div>
            <MetricGrid metrics={(selectedBestStrategy.metrics as Record<string, unknown>) ?? {}} />
            {selectedBestStrategy.rationale ? (
              <p className="muted">{String(selectedBestStrategy.rationale)}</p>
            ) : null}
            <Sparkline
              title="Agent Strategy Returns"
              returns={(selectedBestStrategy.daily_returns as Record<string, number>) ?? {}}
            />
          </div>
        ) : null}
        <label className="field">
          Strategy JSON
          <CodeEditor value={strategyJson} onChange={setStrategyJson} language="json" height={320} />
        </label>
        {history.isPending && !history.data ? <div className="status-block loading">Loading strategy history...</div> : null}
        {history.isError ? <div className="status-block error">{getErrorMessage(history.error)}</div> : null}
        <div className="list">
          {(history.data ?? []).map((entry, index) => {
            const id = String(entry.strategy_id ?? "");
            return (
              <div
                key={index}
                className={`list-row ${selectedStrategyId === id ? "selected" : ""}`}
              >
                <button
                  type="button"
                  className="button-reset"
                  style={{ flex: 1, minWidth: 0 }}
                  onClick={() => {
                    setSelectedStrategyId((prev) => (prev === id ? null : id));
                    if (detailCollapsed) {
                      detailPanelRef.current?.expand();
                      setDetailCollapsed(false);
                    }
                  }}
                >
                  <div>
                    <strong>{String(entry.label ?? entry.strategy_id ?? "strategy")}</strong>
                    <p className="muted">
                      {entry.template_name ? `${String(entry.template_name)} · ` : ""}
                      {String(entry.ran_at ?? "")}
                      {entry.source_factor_id ? ` · ${String(entry.source_factor_id)}` : ""}
                    </p>
                  </div>
                </button>
                <div className="align-right">
                  <div>{entry.is_primary ? "primary" : `cand ${String(entry.candidate_rank ?? "-")}`}</div>
                  <div className="muted">score {Number(entry.selection_score ?? 0).toFixed(3)}</div>
                </div>
                <button
                  type="button"
                  className="button button-danger"
                  disabled={deleteMutation.isPending}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (id && confirm(`Delete strategy ${id}?`)) {
                      deleteMutation.mutate(id);
                    }
                  }}
                >
                  ✕
                </button>
              </div>
            );
          })}
          {!history.isPending && !(history.data ?? []).length ? <p className="muted">No saved strategies yet.</p> : null}
        </div>
        {selectedStrategy.isError ? <div className="status-block error">{getErrorMessage(selectedStrategy.error)}</div> : null}
        {selectedStrategy.isLoading ? <p className="muted">Loading strategy details...</p> : null}
        {detail ? <JsonView value={detail} /> : null}
      </SectionCard>
      </Panel>
    </Group>
  );
}

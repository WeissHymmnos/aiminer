import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Panel, Group, type PanelImperativeHandle } from "react-resizable-panels";
import { CodeEditor } from "../components/CodeEditor";
import { ResizeHandle } from "../components/ResizeHandle";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { Sparkline } from "../components/Sparkline";
import { api } from "../lib/api";

const backendOptions = ["ricequant", "qlib", "local"];
const engineOptions = ["polars", "pandas"];
const marketModeOptions = ["single", "multi"];
const localDataLayoutOptions = ["auto", "qlib", "contracts", "dominant"];

const defaultRequest = {
  expression: "Rank(Delta($close, 5))",
  start_date: "2017-01-01",
  end_date: "2020-10-31",
  engine: "polars",
  market: "000300.XSHG",
  daily_normalize: true,
  run_robustness: true,
  skip_validation: false,
  label: "Web manual backtest",
  data_backend: "ricequant",
  market_profile: "cn_stock",
  market_mode: "single",
  market_profiles: ["cn_stock"],
  local_data_path: "",
  local_data_layout: "auto",
};

export function ManualBacktestPage() {
  const [payload, setPayload] = useState(defaultRequest);
  const [validationMessage, setValidationMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const historyPanelRef = useRef<PanelImperativeHandle | null>(null);
  const queryClient = useQueryClient();
  const history = useQuery({
    queryKey: ["manual-history"],
    queryFn: api.backtestHistory,
  });
  const selectedBacktest = useQuery({
    queryKey: ["manual-backtest", selectedJobId],
    queryFn: () => api.getBacktest(selectedJobId!),
    enabled: Boolean(selectedJobId),
  });
  const validateMutation = useMutation({
    mutationFn: api.validateBacktest,
    onSuccess: (data) => {
      setValidationMessage(data.message);
      setErrorMessage(data.ok ? "" : data.message);
    },
    onError: (error) => setErrorMessage((error as Error).message),
  });
  const runMutation = useMutation({
    mutationFn: api.runBacktest,
    onSuccess: (data) => {
      setErrorMessage("");
      setValidationMessage("");
      setSelectedJobId(String(data.job_id ?? ""));
      void queryClient.invalidateQueries({ queryKey: ["manual-history"] });
    },
    onError: (error) => setErrorMessage((error as Error).message),
  });
  const deleteMutation = useMutation({
    mutationFn: api.deleteBacktest,
    onSuccess: (_, jobId) => {
      if (selectedJobId === jobId) {
        setSelectedJobId(null);
      }
      void queryClient.invalidateQueries({ queryKey: ["manual-history"] });
    },
    onError: (error) => setErrorMessage((error as Error).message),
  });
  const selectedBacktestData = selectedBacktest.data ?? null;
  const selectedBacktestJobId = String(selectedBacktestData?.job_id ?? "");
  const detail = selectedJobId
    ? selectedBacktestData && (!selectedBacktestJobId || selectedBacktestJobId === selectedJobId)
      ? selectedBacktestData
      : null
    : runMutation.data ?? null;
  const detailJobId = String(detail?.job_id ?? selectedJobId ?? "");
  const chartUrl =
    detailJobId && (detail?.chart_path || (detail as { chart_paths?: { equity?: string } } | null)?.chart_paths?.equity)
      ? api.manualBacktestChartUrl(detailJobId, String(detail?.ran_at ?? ""))
      : "";
  const ricequantHint = errorMessage.includes("RiceQuant")
    ? "RiceQuant 远端链路断了。可以稍后重试，或把 Data Backend 切到 local / qlib。"
    : "";

  return (
    <Group orientation="horizontal" className="panel-container">
      <Panel id="left-panel" defaultSize={50} minSize={20}>
        <SectionCard
          title="Manual Factor Backtest"
          actions={
            <div className="button-group">
              <button
                className="button"
                onClick={() => validateMutation.mutate(payload)}
                disabled={validateMutation.isPending || runMutation.isPending}
              >
                Validate
              </button>
              <button
                className="button"
                onClick={() => runMutation.mutate(payload)}
                disabled={runMutation.isPending || validateMutation.isPending}
              >
                Run
              </button>
              <button
                type="button"
                className="button"
                onClick={() => {
                  if (historyCollapsed) {
                    historyPanelRef.current?.expand();
                    setHistoryCollapsed(false);
                  } else {
                    historyPanelRef.current?.collapse();
                    setHistoryCollapsed(true);
                  }
                }}
              >
                {historyCollapsed ? "Show History" : "Hide History"}
              </button>
            </div>
          }
        >
          <label className="field">
            Expression
            <CodeEditor
              value={payload.expression}
              onChange={(expression) => setPayload({ ...payload, expression })}
              language="python"
              height={220}
            />
          </label>
          <div className="page-grid two-col">
            <label className="field">
              Label
              <input
                value={payload.label}
                onChange={(event) => setPayload({ ...payload, label: event.target.value })}
              />
            </label>
            <label className="field">
              Market
              <input
                value={payload.market}
                onChange={(event) => setPayload({ ...payload, market: event.target.value })}
              />
            </label>
            <label className="field">
              Start Date
              <input
                value={payload.start_date}
                onChange={(event) => setPayload({ ...payload, start_date: event.target.value })}
              />
            </label>
            <label className="field">
              End Date
              <input
                value={payload.end_date}
                onChange={(event) => setPayload({ ...payload, end_date: event.target.value })}
              />
            </label>
            <label className="field">
              Data Backend
              <select
                value={payload.data_backend}
                onChange={(event) => setPayload({ ...payload, data_backend: event.target.value })}
              >
                {backendOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Engine
              <select
                value={payload.engine}
                onChange={(event) => setPayload({ ...payload, engine: event.target.value })}
              >
                {engineOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Market Mode
              <select
                value={payload.market_mode}
                onChange={(event) => setPayload({ ...payload, market_mode: event.target.value })}
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
                value={payload.market_profile}
                onChange={(event) => setPayload({ ...payload, market_profile: event.target.value })}
              />
            </label>
            <label className="field">
              Market Profiles
              <input
                value={payload.market_profiles.join(",")}
                onChange={(event) =>
                  setPayload({
                    ...payload,
                    market_profiles: event.target.value
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean),
                  })
                }
              />
            </label>
            <label className="field">
              Local Data Path
              <input
                value={payload.local_data_path}
                onChange={(event) => setPayload({ ...payload, local_data_path: event.target.value })}
              />
            </label>
            <label className="field">
              Local Data Layout
              <select
                value={payload.local_data_layout}
                onChange={(event) => setPayload({ ...payload, local_data_layout: event.target.value })}
              >
                {localDataLayoutOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="toggle-grid">
            <label className="field-toggle">
              <span>Daily Normalize</span>
              <input
                type="checkbox"
                checked={payload.daily_normalize}
                onChange={(event) => setPayload({ ...payload, daily_normalize: event.target.checked })}
              />
            </label>
            <label className="field-toggle">
              <span>Run Robustness</span>
              <input
                type="checkbox"
                checked={payload.run_robustness}
                onChange={(event) => setPayload({ ...payload, run_robustness: event.target.checked })}
              />
            </label>
            <label className="field-toggle">
              <span>Skip Validation</span>
              <input
                type="checkbox"
                checked={payload.skip_validation}
                onChange={(event) => setPayload({ ...payload, skip_validation: event.target.checked })}
              />
            </label>
          </div>
          <p className="muted">{validationMessage || "Validation output will appear here."}</p>
          {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
          {ricequantHint ? <p className="muted">{ricequantHint}</p> : null}
          {detail ? (
            <div className="stack">
              <MetricGrid metrics={(detail.metrics as Record<string, unknown>) ?? {}} />
              <Sparkline
                title="Manual Backtest Curve"
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
        panelRef={historyPanelRef}
        onResize={(size) => setHistoryCollapsed(size.asPercentage <= 0.1)}
      >
        <SectionCard
          title="Manual Backtest History"
          actions={
            <button
              type="button"
              className="button"
              onClick={() => {
                if (historyCollapsed) {
                  historyPanelRef.current?.expand();
                  setHistoryCollapsed(false);
                } else {
                  historyPanelRef.current?.collapse();
                  setHistoryCollapsed(true);
                }
              }}
            >
              {historyCollapsed ? "Expand" : "Collapse"}
            </button>
          }
        >
          <div className="list">
            {(history.data ?? []).map((entry, index) => {
              const id = String(entry.job_id ?? "");
              return (
                <div key={index} className={`list-row ${selectedJobId === id ? "selected" : ""}`}>
                  <button
                    type="button"
                    className="button-reset"
                    style={{ flex: 1, minWidth: 0 }}
                    onClick={() => {
                      setSelectedJobId((prev) => (prev === id ? null : id));
                      if (historyCollapsed) {
                        historyPanelRef.current?.expand();
                        setHistoryCollapsed(false);
                      }
                    }}
                  >
                    <div>
                      <strong>{String(entry.label ?? entry.job_id ?? "manual")}</strong>
                      <p className="muted">{String(entry.ran_at ?? "")}</p>
                    </div>
                  </button>
                  <span>{String(entry.return_points ?? 0)} pts</span>
                  <button
                    type="button"
                    className="button button-danger"
                    disabled={deleteMutation.isPending}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (id && confirm(`Delete backtest ${id}?`)) {
                        deleteMutation.mutate(id);
                      }
                    }}
                  >
                    ✕
                  </button>
                </div>
              );
            })}
          </div>
          {selectedBacktest.isLoading ? <p className="muted">Loading result details...</p> : null}
          {chartUrl ? (
            <div className="chart-panel">
              <div className="plot-title">
                <span>Equity Curve</span>
                <span className="muted" style={{ marginLeft: 8 }}>
                  {detailJobId}
                </span>
              </div>
              <img className="chart-image" src={chartUrl} alt={`Manual backtest chart ${detailJobId}`} />
            </div>
          ) : null}
          {detail ? <JsonView value={detail} /> : null}
        </SectionCard>
      </Panel>
    </Group>
  );
}

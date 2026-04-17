import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { Sparkline } from "../components/Sparkline";
import { api } from "../lib/api";

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
  const history = useQuery({
    queryKey: ["manual-history"],
    queryFn: api.backtestHistory,
  });
  const validateMutation = useMutation({
    mutationFn: api.validateBacktest,
    onSuccess: (data) => setValidationMessage(data.message),
  });
  const runMutation = useMutation({
    mutationFn: api.runBacktest,
  });

  return (
    <div className="page-grid two-col">
      <SectionCard
        title="Manual Factor Backtest"
        actions={
          <div className="button-group">
            <button className="button" onClick={() => validateMutation.mutate(payload)}>
              Validate
            </button>
            <button className="button" onClick={() => runMutation.mutate(payload)}>
              Run
            </button>
          </div>
        }
      >
        <label className="field">
          Expression
          <textarea
            value={payload.expression}
            onChange={(event) => setPayload({ ...payload, expression: event.target.value })}
            rows={8}
          />
        </label>
        <p className="muted">{validationMessage || "Validation output will appear here."}</p>
        {runMutation.data ? (
          <div className="stack">
            <MetricGrid metrics={(runMutation.data.metrics as Record<string, unknown>) ?? {}} />
            <Sparkline
              title="Manual Backtest Curve"
              returns={(runMutation.data.daily_returns as Record<string, number>) ?? {}}
            />
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Manual Backtest History">
        <div className="list">
          {(history.data ?? []).map((entry, index) => (
            <div key={index} className="list-row">
              <div>
                <strong>{String(entry.label ?? entry.job_id ?? "manual")}</strong>
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

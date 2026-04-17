import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { JsonView } from "../components/JsonView";
import { MetricGrid } from "../components/MetricGrid";
import { SectionCard } from "../components/SectionCard";
import { Sparkline } from "../components/Sparkline";
import { api } from "../lib/api";
import type { FactorSummary } from "../types";

export function AlphaPoolPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const factors = useQuery({
    queryKey: ["factors"],
    queryFn: () => api.listFactors(),
    refetchInterval: 10000,
  });
  const factorDetail = useQuery({
    queryKey: ["factor", selectedId],
    queryFn: () => api.getFactor(selectedId!),
    enabled: Boolean(selectedId),
  });

  return (
    <div className="page-grid two-col">
      <SectionCard title="Alpha Pool">
        <div className="list">
          {(factors.data?.items ?? []).map((factor: FactorSummary) => (
            <button
              type="button"
              key={factor.id}
              className={`list-row button-reset ${selectedId === factor.id ? "selected" : ""}`}
              onClick={() => setSelectedId(factor.id)}
            >
              <div>
                <strong>{factor.id}</strong>
                <p className="muted">{factor.hypothesis}</p>
              </div>
              <span>{factor.ic?.toFixed?.(4) ?? "-"}</span>
            </button>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Factor Detail">
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
    </div>
  );
}

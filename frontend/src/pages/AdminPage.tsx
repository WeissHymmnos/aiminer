import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { JsonView } from "../components/JsonView";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";

const scopeOptions = [
  { value: "pool", label: "Alpha Pool" },
  { value: "memory", label: "Wiki / Memory" },
  { value: "rag", label: "RAG Cache" },
  { value: "runs", label: "Run Artifacts" },
];

export function AdminPage() {
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["pool"]);
  const [resetToken, setResetToken] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const resetMutation = useMutation({
    mutationFn: api.adminReset,
    onSuccess: () => setErrorMessage(""),
    onError: (error) => setErrorMessage((error as Error).message),
  });

  const result = resetMutation.data ?? null;
  const resultConfirmed = Boolean((result?.confirm as boolean | undefined) ?? false);
  const selectedSummary = useMemo(
    () => (selectedScopes.length ? selectedScopes.join(", ") : "none"),
    [selectedScopes],
  );

  function toggleScope(scope: string) {
    setSelectedScopes((current) =>
      current.includes(scope) ? current.filter((item) => item !== scope) : [...current, scope],
    );
  }

  function submit(confirm: boolean) {
    if (!selectedScopes.length) {
      setErrorMessage("Select at least one scope before running reset.");
      return;
    }
    resetMutation.mutate({
      scopes: selectedScopes,
      confirm,
      reset_token: confirm ? resetToken || undefined : undefined,
    });
  }

  return (
    <div className="page-grid two-col">
      <SectionCard
        title="Workspace Reset"
        actions={
          <div className="button-group">
            <button className="button" disabled={resetMutation.isPending} onClick={() => submit(false)}>
              Preview Plan
            </button>
            <button className="button button-danger" disabled={resetMutation.isPending} onClick={() => submit(true)}>
              Execute Reset
            </button>
          </div>
        }
      >
        <p className="muted">
          Reset is reversible. Matching paths are moved into <code>results/.trash/</code> instead of being deleted.
        </p>
        <div className="toggle-grid">
          {scopeOptions.map((scope) => (
            <label className="field-toggle" key={scope.value}>
              <span>{scope.label}</span>
              <input
                type="checkbox"
                checked={selectedScopes.includes(scope.value)}
                onChange={() => toggleScope(scope.value)}
              />
            </label>
          ))}
        </div>
        <label className="field">
          Reset Token
          <input
            value={resetToken}
            onChange={(event) => setResetToken(event.target.value)}
            placeholder="Only required when executing a reset"
          />
        </label>
        <div className="metric-grid">
          <div className="metric">
            <span>Selected Scopes</span>
            <strong>{selectedSummary}</strong>
          </div>
          <div className="metric">
            <span>Mode</span>
            <strong>{result ? (resultConfirmed ? "confirmed" : "dry-run") : "waiting"}</strong>
          </div>
        </div>
        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
      </SectionCard>

      <SectionCard title="Reset Preview">
        {result ? (
          <div className="stack">
            {typeof result.plan_text === "string" ? <pre className="code-block">{result.plan_text}</pre> : null}
            <JsonView value={result} maxLines={80} />
          </div>
        ) : (
          <p className="muted">Preview a reset plan to inspect the files that would be moved.</p>
        )}
      </SectionCard>
    </div>
  );
}

import { FormEvent, useState } from "react";
import { deskFetch } from "../lib/api";

export function AgentPage() {
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setFailed(false);
    setResult(null);
    deskFetch("/api/v1/agent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, max_turns: 16 }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`agent ${r.status}`);
        return r.json();
      })
      .then((body) => {
        if (body && body.ok === false) {
          setFailed(true);
          setError(
            String(body.error_type ? `${body.error_type}: ${body.error}` : body.error || "agent failed"),
          );
          setResult(body.text || null);
          return;
        }
        setResult(body.text || JSON.stringify(body, null, 2));
      })
      .catch((err) => {
        setFailed(true);
        setError(String(err));
      });
  };

  return (
    <div className="page-grid">
      <h2>Agent</h2>
      <p className="muted">Calls catalog, eval, reproduce, and review. Does not invent backtests.</p>
      <form onSubmit={onSubmit}>
        <label className="field">
          Request
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="复现这份研报并告诉我能不能晋升进 alpha pool"
            rows={4}
          />
        </label>
        <button className="button" type="submit">
          Run desk
        </button>
      </form>
      {failed ? <div className="status-block error">failed · {error}</div> : null}
      {!failed && error ? <div className="status-block error">{error}</div> : null}
      {result ? <pre className="code-block">{result}</pre> : null}
    </div>
  );
}

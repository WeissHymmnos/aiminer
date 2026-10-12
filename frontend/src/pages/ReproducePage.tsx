import { FormEvent, useState } from "react";
import { deskFetch } from "../lib/api";

type JobBody = {
  id?: string;
  status?: string;
  error?: string | null;
  result?: { status?: string; factors?: unknown[]; factor_count?: number };
};

export function ReproducePage() {
  const [pdfPath, setPdfPath] = useState("");
  const [job, setJob] = useState<JobBody | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setJob(null);
    deskFetch("/api/v1/reproduce", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pdf_path: pdfPath, sync: false }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`reproduce ${r.status}`);
        return r.json();
      })
      .then((body: JobBody) => {
        setJob(body);
        const jobId = body.id;
        if (!jobId) {
          setError("reproduce did not return a job id");
          return;
        }
        const tick = () => {
          deskFetch(`/api/v1/jobs/${jobId}`)
            .then((r) => {
              if (!r.ok) throw new Error(`job ${r.status}`);
              return r.json();
            })
            .then((next: JobBody) => {
              setJob(next);
              if (next.status === "error") {
                setError(String(next.error || "reproduce failed"));
              }
              if (next.status === "running" || next.status === "queued") {
                window.setTimeout(tick, 1500);
              }
            })
            .catch((err) => setError(String(err)));
        };
        tick();
      })
      .catch((err) => setError(String(err)));
  };

  const resultStatus = job?.result?.status;
  const noFactors = resultStatus === "no_factors";

  return (
    <div className="page-grid">
      <h2>Reproduce</h2>
      <p className="muted">
        PDF path must sit under FINAINCE_PDF_ROOT. Job poll uses the same id. Desk
        token required.
      </p>
      <form onSubmit={onSubmit}>
        <label className="field">
          PDF path
          <input
            value={pdfPath}
            onChange={(e) => setPdfPath(e.target.value)}
            placeholder="/path/to/report.pdf"
          />
        </label>
        <button className="button" type="submit">
          Reproduce
        </button>
      </form>
      {error ? <div className="status-block error">{error}</div> : null}
      {job?.status ? (
        <p className="muted">
          job {job.id} · {job.status}
        </p>
      ) : null}
      {noFactors ? (
        <div className="status-block">no_factors — extraction found nothing honest to backtest.</div>
      ) : null}
      {resultStatus && !noFactors ? <p className="muted">result: {resultStatus}</p> : null}
    </div>
  );
}

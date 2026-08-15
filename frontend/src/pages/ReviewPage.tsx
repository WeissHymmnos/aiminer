import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deskFetch } from "../lib/api";

type Promo = {
  id: string;
  catalog_id: string;
  direction: string;
  decision: string;
  gates?: { passed?: boolean; failures?: string[] };
};

export function ReviewPage() {
  const [items, setItems] = useState<Promo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [overrideThin, setOverrideThin] = useState(false);

  const load = () => {
    deskFetch("/api/v1/review")
      .then((r) => {
        if (!r.ok) throw new Error(`review ${r.status}`);
        return r.json();
      })
      .then((body) => setItems(body.items || []))
      .catch((err) => setError(String(err)));
  };

  useEffect(() => {
    load();
  }, []);

  const approve = (id: string) => {
    const override = overrideThin ? ["thin_panel"] : [];
    deskFetch(`/api/v1/review/${id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ override }),
    })
      .then((r) => r.json())
      .then((body) => {
        if (body && body.ok === false) {
          setError(String(body.error || "approve failed"));
        } else {
          setError(null);
        }
        setMessage(body.ok === false ? String(body.error || "approve failed") : "approved");
        load();
      })
      .catch((err) => setError(String(err)));
  };

  const reject = (id: string) => {
    deskFetch(`/api/v1/review/${id}/reject`, { method: "POST" })
      .then((r) => r.json())
      .then((body) => {
        if (body && body.ok === false) {
          setError(String(body.error || "reject failed"));
        } else {
          setError(null);
        }
        setMessage(body.ok === false ? String(body.error || "reject failed") : "rejected");
        load();
      })
      .catch((err) => setError(String(err)));
  };

  return (
    <div className="page-grid">
      <h2>Review</h2>
      <p className="muted">Pending promotions. Approve writes the other store.</p>
      <label className="field-toggle">
        <span>override thin_panel</span>
        <input
          type="checkbox"
          checked={overrideThin}
          onChange={(e) => setOverrideThin(e.target.checked)}
        />
      </label>
      {error ? <div className="status-block error">{error}</div> : null}
      {message ? <p className="muted">{message}</p> : null}
      <div className="list">
        {items.map((item) => (
          <div key={item.id} className="list-row">
            <div>
              <Link to={`/catalog/${item.catalog_id}`}>{item.id.slice(0, 8)}</Link>
              {" · "}
              {item.direction} · {item.decision}
              {item.gates?.failures?.length ? (
                <div className="status-block error">gates: {item.gates.failures.join(",")}</div>
              ) : (
                <p className="muted">gates passed</p>
              )}
            </div>
            <div className="desk-actions">
              <button className="button" type="button" onClick={() => approve(item.id)}>
                Approve
              </button>
              <button className="button" type="button" onClick={() => reject(item.id)}>
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
      {items.length === 0 && !error ? <p className="muted">Queue empty.</p> : null}
    </div>
  );
}

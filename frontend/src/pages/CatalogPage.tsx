import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { deskFetch } from "../lib/api";

type CatalogItem = {
  id: string;
  name: string;
  name_cn?: string;
  style?: string;
  universe?: string;
  status?: string;
  tags?: string[];
  lineage?: { source?: string; source_ref?: string; formula_proxy?: boolean };
  metrics?: { ic?: number | null };
  expression?: { dialect?: string; text?: string; alt_text?: string | null; translatable?: boolean };
};

export function CatalogPage() {
  const { id } = useParams();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [detail, setDetail] = useState<CatalogItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [direction, setDirection] = useState("to_pool");

  useEffect(() => {
    setError(null);
    if (id) {
      deskFetch(`/api/v1/catalog/${id}`)
        .then((r) => {
          if (!r.ok) throw new Error(`catalog ${id} ${r.status}`);
          return r.json();
        })
        .then((body) => setDetail(body))
        .catch((err) => setError(String(err)));
      return;
    }
    setDetail(null);
    deskFetch("/api/v1/catalog")
      .then((r) => {
        if (!r.ok) throw new Error(`catalog ${r.status}`);
        return r.json();
      })
      .then((body) => setItems(body.items || []))
      .catch((err) => setError(String(err)));
  }, [id]);

  const promote = (event: FormEvent) => {
    event.preventDefault();
    if (!id) return;
    setMessage(null);
    deskFetch("/api/v1/promote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ catalog_id: id, direction }),
    })
      .then(async (r) => {
        const body = await r.json().catch(() => ({}));
        if (!r.ok || body.ok === false) {
          setError(String(body.detail || body.error || `promote ${r.status}`));
          setMessage(null);
          return;
        }
        setError(null);
        setMessage(`queued ${body.promotion_id || ""}`.trim());
      })
      .catch((err) => setError(String(err)));
  };

  if (id) {
    return (
      <div className="page-grid">
        <div className="card-header">
          <h2>Catalog</h2>
          <Link to="/">All factors</Link>
        </div>
        {error ? <div className="status-block error">{error}</div> : null}
        {detail ? (
          <div className="card">
            <p>
              {detail.name} · {detail.lineage?.source} · {detail.status} · IC{" "}
              {detail.metrics?.ic ?? "—"}
            </p>
            <p className="muted">
              {detail.style || "style?"} · {detail.universe || "universe?"} ·{" "}
              {detail.expression?.dialect}
              {detail.expression?.translatable === false ? " · not translatable" : ""}
              {detail.lineage?.formula_proxy ? " · formula_proxy" : ""}
              {detail.universe === "local_panel" ? " · thin_panel" : ""}
            </p>
            {detail.tags?.includes("synthetic") ? (
              <p className="muted">Source: discovery (synthetic report)</p>
            ) : null}
            {detail.expression?.text ? <pre className="code-block">{detail.expression.text}</pre> : null}
            <form onSubmit={promote}>
              <label className="field">
                Direction
                <select value={direction} onChange={(e) => setDirection(e.target.value)}>
                  <option value="to_pool">to_pool</option>
                  <option value="to_library">to_library</option>
                </select>
              </label>
              <button className="button" type="submit">
                提交晋升
              </button>
            </form>
            {message ? <p className="muted">{message}</p> : null}
          </div>
        ) : !error ? (
          <p className="muted">Loading…</p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="page-grid">
      <h2>Catalog</h2>
      <p className="muted">Discovery and reproduction index.</p>
      {error ? <div className="status-block error">{error}</div> : null}
      <div className="list">
        {items.map((item) => (
          <Link key={item.id} className="list-row" to={`/catalog/${item.id}`}>
            <span>
              {item.name} · {item.lineage?.source} · {item.status}
            </span>
            <span className="factor-row-ic">IC {item.metrics?.ic ?? "—"}</span>
          </Link>
        ))}
      </div>
      {items.length === 0 && !error ? <p className="muted">Catalog is empty.</p> : null}
    </div>
  );
}

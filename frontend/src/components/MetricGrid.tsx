type Props = {
  metrics: Record<string, unknown>;
};

export function MetricGrid({ metrics }: Props) {
  const entries = Object.entries(metrics ?? {});
  if (!entries.length) {
    return <p className="muted">No metrics available.</p>;
  }
  return (
    <div className="metric-grid">
      {entries.map(([key, value]) => (
        <div key={key} className="metric">
          <span>{key}</span>
          <strong>{typeof value === "number" ? value.toFixed(4) : String(value)}</strong>
        </div>
      ))}
    </div>
  );
}

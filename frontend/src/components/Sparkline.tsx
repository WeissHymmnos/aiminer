type Props = {
  returns?: Record<string, number>;
  title: string;
};

export function Sparkline({ returns, title }: Props) {
  const values = Object.entries(returns ?? {})
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, value]) => Number(value));
  if (!values.length) {
    return (
      <div className="plot-empty">
        <span>{title}</span>
        <p className="muted">No return series available.</p>
      </div>
    );
  }
  let cumulative = 1;
  const points = values.map((value) => {
    cumulative *= 1 + value;
    return cumulative;
  });
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const path = points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * 100;
      const y = 90 - ((point - min) / range) * 80;
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
  return (
    <div className="plot">
      <div className="plot-title">{title}</div>
      <svg viewBox="0 0 100 100" className="plot-svg" preserveAspectRatio="none">
        <path d={path} fill="none" stroke="currentColor" strokeWidth="2.5" />
      </svg>
    </div>
  );
}

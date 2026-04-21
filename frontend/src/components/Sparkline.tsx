type Props = {
  returns?: Record<string, number>;
  title: string;
};

export function Sparkline({ returns, title }: Props) {
  const values = Object.entries(returns ?? {})
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, value]) => Number(value))
    .filter((v) => Number.isFinite(v));

  if (!values.length) {
    return (
      <div className="plot-empty">
        <span>{title}</span>
        <p className="muted">No return series available.</p>
      </div>
    );
  }

  // 从 1.0 起点开始累计, 这样第一天的收益也能被可视化
  let cumulative = 1;
  const points = [1, ...values.map((value) => (cumulative *= 1 + value))];

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = Math.max(max - min, 1e-9);

  const toX = (index: number) => (index / Math.max(points.length - 1, 1)) * 100;
  const toY = (p: number) => 95 - ((p - min) / range) * 90;

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${toX(i).toFixed(2)} ${toY(p).toFixed(2)}`)
    .join(" ");
  const areaPath = `${linePath} L 100 95 L 0 95 Z`;

  const final = points[points.length - 1];
  const pct = ((final - 1) * 100).toFixed(2);
  const isUp = final >= 1;
  const color = isUp ? "var(--ctp-green)" : "var(--ctp-red)";
  const baselineY = toY(1);

  return (
    <div className="plot">
      <div className="plot-title">
        <span>{title}</span>
        <span style={{ marginLeft: 8, color, fontWeight: 600 }}>
          {isUp ? "+" : ""}
          {pct}%
        </span>
      </div>
      <svg viewBox="0 0 100 100" className="plot-svg" preserveAspectRatio="none">
        {/* 基线: 本金不变 (1.0) */}
        {baselineY >= 0 && baselineY <= 100 && (
          <line
            x1="0"
            x2="100"
            y1={baselineY}
            y2={baselineY}
            stroke="var(--ctp-surface2)"
            strokeWidth="0.4"
            strokeDasharray="2,2"
            vectorEffect="non-scaling-stroke"
          />
        )}
        <path d={areaPath} fill={color} fillOpacity="0.18" />
        <path
          d={linePath}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
        />
      </svg>
      <div className="muted" style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginTop: 4 }}>
        <span>min {((min - 1) * 100).toFixed(2)}%</span>
        <span>{values.length} days</span>
        <span>max {((max - 1) * 100).toFixed(2)}%</span>
      </div>
    </div>
  );
}

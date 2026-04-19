export interface Paginated<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  next_offset: number;
}

export interface SwarmRunSummary {
  run_id: string;
  status: "pending" | "running" | "completed" | "failed";
  is_active: boolean;
  config: Record<string, any>;
  started_at?: string;
  ended_at?: string;
  result_counts?: {
    factor_count: number;
    strategy_count: number;
  };
}

export interface FactorMetrics {
  information_coefficient?: number;
  sharpe?: number;
  annual_return?: number;
  max_drawdown?: number;
  volatility?: number;
  calmar?: number;
  fitness?: number;
  [key: string]: any;
}

export interface FactorSummary {
  id: string;
  hypothesis: string;
  run_id: string;
  iteration: number;
  ic?: number;
  metrics?: FactorMetrics;
  returns?: Record<string, number>;
}

export interface StrategySummary {
  strategy_id: string;
  run_id: string;
  label: string;
  strategy_mode: "cross_sectional" | "time_series";
  metrics?: {
    sharpe?: number;
    annual_return?: number;
    max_drawdown?: number;
    [key: string]: any;
  };
}

export interface WikiGraphNode {
  id: string;
  slug: string;
  title: string;
  type: "factor_card" | "strategy_family" | "market_profile" | "technical_ref";
  status: string;
  degree?: number;
  x?: number;
  y?: number;
}

export interface WikiGraphEdge {
  source: string | WikiGraphNode;
  target: string | WikiGraphNode;
  kind: "related" | "wikilink";
}

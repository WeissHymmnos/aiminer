export type SwarmRunSummary = {
  run_id: string;
  status: string;
  is_active?: boolean;
  started_at?: string | null;
  ended_at?: string | null;
  created_at?: string | null;
  process_pid?: number | null;
  parallel?: boolean;
  config?: Record<string, unknown>;
  result_counts?: {
    factor_count: number;
    strategy_count: number;
  };
};

export type Paginated<T> = {
  items: T[];
  total: number;
  offset: number;
  next_offset: number;
};

export type FactorSummary = {
  id: string;
  hypothesis: string;
  ic: number | null;
  rank_ic: number | null;
  is_effective: boolean | null;
  perf_metric: number | null;
  timestamp: string;
  run_id?: string | null;
};

export type StrategySummary = {
  strategy_id: string;
  label?: string;
  strategy_mode?: string;
  market?: string;
  engine?: string;
  run_id?: string | null;
  source_factor_id?: string | null;
  ran_at?: string | null;
  metrics: Record<string, number>;
};

export type WikiGraphNode = {
  id: string;
  slug: string;
  title: string;
  type: string;
  status: string;
  updated: string;
  tags: string[];
  degree: number;
};

export type WikiGraphEdge = {
  source: string;
  target: string;
  kind: "related" | "wikilink";
};

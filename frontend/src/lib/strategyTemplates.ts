export type StrategyTemplateConfig = {
  label: string;
  strategy_mode: "cross_sectional" | "time_series";
  direction: "long_only" | "long_short" | "long_flat";
  selection_rule: "top_n" | "bottom_n" | "top_bottom_n" | "threshold";
  rebalance_freq: "daily" | "weekly" | "monthly";
  top_n: number | null;
  bottom_n: number | null;
  long_threshold: number | null;
  short_threshold: number | null;
  exit_threshold: number | null;
  max_positions: number | null;
  max_weight_per_position: number;
  min_holding_days: number;
  commission_bps: number;
  slippage_bps: number;
  market: string;
  start_date: string;
  end_date: string;
  engine: "pandas" | "polars";
};

export const strategyTemplates: Record<string, StrategyTemplateConfig> = {
  cs_top_bottom: {
    label: "Cross-sectional Top/Bottom Long-Short",
    strategy_mode: "cross_sectional",
    direction: "long_short",
    selection_rule: "top_bottom_n",
    rebalance_freq: "daily",
    top_n: 20,
    bottom_n: 20,
    long_threshold: null,
    short_threshold: null,
    exit_threshold: null,
    max_positions: 40,
    max_weight_per_position: 0.05,
    min_holding_days: 1,
    commission_bps: 5,
    slippage_bps: 5,
    market: "000300.XSHG",
    start_date: "2017-01-01",
    end_date: "2020-10-31",
    engine: "polars",
  },
  cs_top_only: {
    label: "Cross-sectional Top-N Long-Only",
    strategy_mode: "cross_sectional",
    direction: "long_only",
    selection_rule: "top_n",
    rebalance_freq: "daily",
    top_n: 20,
    bottom_n: null,
    long_threshold: null,
    short_threshold: null,
    exit_threshold: null,
    max_positions: 20,
    max_weight_per_position: 0.08,
    min_holding_days: 1,
    commission_bps: 5,
    slippage_bps: 5,
    market: "000300.XSHG",
    start_date: "2017-01-01",
    end_date: "2020-10-31",
    engine: "polars",
  },
  cs_threshold: {
    label: "Cross-sectional Threshold Long-Only",
    strategy_mode: "cross_sectional",
    direction: "long_only",
    selection_rule: "threshold",
    rebalance_freq: "weekly",
    top_n: null,
    bottom_n: null,
    long_threshold: 0.75,
    short_threshold: null,
    exit_threshold: null,
    max_positions: 25,
    max_weight_per_position: 0.06,
    min_holding_days: 3,
    commission_bps: 5,
    slippage_bps: 5,
    market: "000300.XSHG",
    start_date: "2017-01-01",
    end_date: "2020-10-31",
    engine: "polars",
  },
  ts_long_flat: {
    label: "Time-Series Threshold Long/Flat",
    strategy_mode: "time_series",
    direction: "long_flat",
    selection_rule: "threshold",
    rebalance_freq: "daily",
    top_n: null,
    bottom_n: null,
    long_threshold: 0.6,
    short_threshold: null,
    exit_threshold: 0.45,
    max_positions: 40,
    max_weight_per_position: 0.04,
    min_holding_days: 2,
    commission_bps: 5,
    slippage_bps: 5,
    market: "000300.XSHG",
    start_date: "2017-01-01",
    end_date: "2020-10-31",
    engine: "polars",
  },
  ts_long_short: {
    label: "Time-Series Threshold Long/Short",
    strategy_mode: "time_series",
    direction: "long_short",
    selection_rule: "threshold",
    rebalance_freq: "daily",
    top_n: null,
    bottom_n: null,
    long_threshold: 0.75,
    short_threshold: 0.25,
    exit_threshold: 0.5,
    max_positions: 50,
    max_weight_per_position: 0.03,
    min_holding_days: 2,
    commission_bps: 5,
    slippage_bps: 5,
    market: "000300.XSHG",
    start_date: "2017-01-01",
    end_date: "2020-10-31",
    engine: "polars",
  },
};

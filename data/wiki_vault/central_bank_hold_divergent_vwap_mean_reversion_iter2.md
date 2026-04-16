---
title: "Central-Bank-Hold Divergent VWAP Mean-Reversion"
slug: "central_bank_hold_divergent_vwap_mean_reversion_iter2"
type: "experiment_card"
status: "active"
summary: "While the PBoC keeps rates unchanged, liquidity is trapped in overnight repo; stocks whose VWAP diverges >0.8% from prior close on a 20% surge in cancelled-quo…"
updated: "2026-04-13T20:11:51"
tags: ["专注财报超预期与公告事件驱动的文本挖掘专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "sector_data_source", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.082"
rank_ic: "0.047"
iteration: "2"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Central-Bank-Hold Divergent VWAP Mean-Reversion

## Summary

While the PBoC keeps rates unchanged, liquidity is trapped in overnight repo; stocks whose VWAP diverges >0.8% from prior close on a 20% surge in cancelled-quo…

## Hypothesis

While the PBoC keeps rates unchanged, liquidity is trapped in overnight repo; stocks whose VWAP diverges >0.8% from prior close on a 20% surge in cancelled-quo…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Greater(Abs($vwap/Ref($close,1)-1),0.008),-Rank(Abs($vwap/Ref($close,1)-1))*Rank(Delta($close,1)),0)```

**Math Formula**: f_{t}=\begin{cases}-\text{Rank}\left(\left|\frac{\text{VWAP}_{t}}{\text{prevClose}_{t}}-1\right|\right)\cdot\text{Rank}\left(\Delta\text{CQR}_{t}\right)&\text{if }\left|\frac{\text{VWAP}_{t}}{\text{prevClose}_{t}}-1\right|>0.008\\0&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0820 / 0.0470
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[price_volume_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.

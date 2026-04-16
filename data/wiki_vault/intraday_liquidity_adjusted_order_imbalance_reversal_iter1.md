---
title: "Intraday Liquidity-Adjusted Order-Imbalance Reversal"
slug: "intraday_liquidity_adjusted_order_imbalance_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( Delta($vwap,1) / (Std($volume,5)+1e-5) * Sign(Corr($volume,$close,3)) * (1-Abs(Corr($high,$low,3))) ) goes long (short) stocks whose VWAP moved sharply r…"
updated: "2026-04-16T15:22:51"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "information_coefficient_metric", "rank_ic_metric", "price_volume_data_source", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
parents: ["stat_arb_family"]
depends_on: ["price_volume_data_source", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
ic: -0.0041
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( Delta($vwap,1) / (Std($volume,5)+1e-5) * Sign(Corr($volume,$close,3)) * (1-Abs(Corr($high,$low,3))) ) goes long (short) stocks whose VWAP moved sharply relative to their own short-term volume volatility while same-day volume-price correlation is negative and high-low overlap is shrinking, expecting that liquidity-starved moves with collapsing intraday range snap back within 1 day as dealers widen spreads and mean-reversion dominates.

**Rationale**: Macro: Fed pause keeps rates high, QT drains dealer inventory capacity so liquidity premiums expand; moves not validated by proportional volume revert faster. Market regime is high-vol/bearish, intraday risk-off with investors reducing size; microstructure theory predicts temporary order-imbalance without volume support is quickly arbitraged away. Cross-agent lesson: raw price/volume ratios failed (IC<0.01); scaling by volume-std keeps units homogeneous, VWAP replaces close to anchor to fair value, and shrinking high-low overlap proxies for liquidity drought. Continuous rank across universe ensures monotonic exposure, avoids binary threshold errors, and survives regime shift by neutralizing market beta.

**Implementation (Qlib)**: `Rank(Mul(Div(Delta($vwap, 1), Add(Std($volume, 5), 0.00001)), Mul(Sign(Corr($volume, $close, 3)), Sub(1, Abs(Corr($high, $low, 3))))))`

**Math Formula**: R_{t} = \text{Rank}\left( \frac{\Delta\text{VWAP}_{t,1}}{\sigma(\text{Volume}_{t},5)+10^{-5}} \cdot \text{Sign}\left(\rho(\text{Volume}_{t},\text{Close}_{t},3)\right) \cdot \left(1-\left|\rho(\text{High}_{t},\text{Low}_{t},3)\right|\right) \right)

**IC / RankIC**: -0.0041 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is ineffective: IC ≈ -0.004 (far below 0.02), Rank IC = 0, Sharpe negative, no OOS decay. Signal predicts next-day return in wrong direction and has zero rank explanatory power.

**Suggested Improvements**: Flip sign of entire expression to align with observed reversal; shorten volume-volatility window to 3-days; replace 1-|corr(high,low)| with intraday range ratio (high-low)/close; neutralize sector & size exposure; test 3-5 day holding horizon to capture slower spread normalization.

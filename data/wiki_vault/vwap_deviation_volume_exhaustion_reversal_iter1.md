---
title: "VWAP-Deviation Volume Exhaustion Reversal"
slug: "vwap_deviation_volume_exhaustion_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks that close well above their volume-weighted average price (VWAP) on sharply shrinking volume over the past two sessions tend to mean-revert the next day…"
updated: "2026-04-13T20:11:28"
tags: ["监测收益率肥尾风险与动态对冲的风险管理专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0121
rank_ic: -0.0148
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Stocks that close well above their volume-weighted average price (VWAP) on sharply shrinking volume over the past two sessions tend to mean-revert the next day; factor = Rank((Close - VWAP)/VWAP) * (-Rank(Delta(Volume,2)))

**Rationale**: With the central bank on hold and macro uncertainty elevated, investors are reluctant to chase price extensions. When a stock finishes far above its VWAP—signifying an intraday premium—yet volume is contracting, it signals waning commitment from buyers. The VWAP premium identifies stretched valuations while the volume drop confirms lack of follow-through, creating a high-probability exhaustion reversal. Cross-sectional ranks neutralize market direction, isolating this microstructure imbalance.

**Implementation (Qlib)**: `CSRank(($close - $vwap) / $vwap) * CSRank(-Delta($volume, 2)) * -1`

**Math Formula**: E\left[\frac{r_{i,t+1}}{\sigma_{i,t+1}}\right]=-\alpha\cdot\text{Rank}_{c}\left(\frac{C_{i,t}-VWAP_{i,t}}{VWAP_{i,t}}\right)\cdot\text{Rank}_{c}\left(-\Delta_{2}V_{i,t}\right)

**IC / RankIC**: -0.0121 / -0.0148

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows weak negative IC and Rank IC, both below 0.02 threshold, indicating no predictive power. Negative Sharpe and large max drawdown suggest poor risk-adjusted returns. Zero RRE, PFS, and diversity indicate no robustness or diversification benefit. Factor may be capturing noise rather than mean-reversion signal.

**Suggested Improvements**: 1) Extend lookback window from 2 to 5-10 days to reduce noise 2) Add volatility adjustment (divide by realized vol) 3) Apply sector-neutral ranking to reduce systematic bias 4) Consider using intraday VWAP instead of daily 5) Add minimum volume threshold to filter illiquid stocks 6) Test asymmetric treatment of up/down moves 7) Incorporate recent price trend as additional filter

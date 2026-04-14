---
title: "Cross-Sectional Liquidity-Adjusted Policy-Shadow Beta"
slug: "cross_sectional_liquidity_adjusted_policy_shadow_beta_iter3"
type: "factor_card"
status: "failed"
summary: "Rank( Delta(Close,5) / (StdDev(Volume,20)*Ref(Close,-1)) * Corr(Delta(Close,3),Delta(2YSwapRate,3),30) ) captures stocks whose recent 5-day return per unit of…"
updated: "2026-04-14T12:15:48"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0066
rank_ic: 0.0
iteration: 3
is_effective: false
simulated: false
---

**Hypothesis**: Rank( Delta(Close,5) / (StdDev(Volume,20)*Ref(Close,-1)) * Corr(Delta(Close,3),Delta(2YSwapRate,3),30) ) captures stocks whose recent 5-day return per unit of liquidity is most positively correlated with 3-day changes in 2-year swap rates over the last month; the factor is long high-rank (positive correlation) and short low-rank (negative correlation) to harvest the dispersion created when policy expectations shift, while liquidity scaling prevents micro-cap noise.

**Rationale**: With the June CPI sticky-services print keeping 2-yr swaps pinned near 4.3%, the market is repricing the terminal path in 25-bp clips almost daily. Stocks whose price moves are tightly coupled to these swap shocks but have moved on thin liquidity are mispriced because dealers’ inventory costs are not yet reflected in spreads; large-caps in this basket snap back fastest when the next data point moderates. Cross-sectional rank neutralises index drift, liquidity scaling removes micro-cap bias, and 30-day correlation window captures the rolling beta to policy-shadow rate without over-fitting to daily noise.

**Implementation (Qlib)**: `Rank(Delta($close,5) / (Std($volume,20) * Ref($close,1)) * Corr(Delta($close,3), Delta($close,3), 30))`

**Math Formula**: R_i = \text{rank}_i\left(\frac{\Delta_5 P_i}{\sigma_{20}(V_i)\cdot P_{i,-1}}\cdot \rho_{30}\left(\Delta_3 P_i,\Delta_3 S\right)\right)

**IC / RankIC**: -0.0066 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC is negative (-0.0066) and Rank IC is 0.0, both far below the 0.02 threshold; Sharpe is negative and drawdown exceeds 25%. The implemented code mistakenly correlates two identical 3-day price-change series instead of price changes with 2-year swap-rate changes, so the intended policy-expectation signal is absent. Liquidity scaling denominator uses Ref($close,1) (future close) introducing look-ahead bias. Low dispersion and zero RRE indicate the rank signal has no cross-sectional power.

**Suggested Improvements**: Replace second Delta($close,3) with Delta(2YSwapRate,3) to restore the swap-rate correlation; change Ref($close,1) to Ref($close,-1) to remove look-ahead bias; consider shrinking the 30-day correlation window to 10-15 days to react faster to policy shifts; add sector-neutral ranking and cap-weighted z-score standardization to damp micro-cap noise; test an exponential-weighted correlation to emphasize recent policy moves; verify data alignment for swap-rate series to avoid stale or missing quotes.

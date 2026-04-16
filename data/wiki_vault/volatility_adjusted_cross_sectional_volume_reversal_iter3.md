---
title: "Volatility-Adjusted Cross-Sectional Volume Reversal"
slug: "volatility_adjusted_cross_sectional_volume_reversal_iter3"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( -Sign(Delta($close,1))  Power(Std($close,5),0.5)  Corr(Rank($close/Ref($close,3)),Rank($volume),7) ) goes long (short) st…"
updated: "2026-04-11T20:47:28.605329"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( -Sign(Delta($close,1)) * Power(Std($close,5),0.5) * Corr(Rank($close/Ref($close,3)),Rank($volume),7) ) goes long (short) stocks whose 1-day price change is negative (positive) and whose 7-day price-volume correlation is strongly negative, scaled by 5-day volatility, expecting that high-volatility stocks with divergent volume-price dynamics mean-revert sharply as liquidity seekers overshoot.
**Rationale**: Amid heightened macro uncertainty and bearish risk sentiment, intraday volatility spikes as liquidity providers widen quotes. When price moves opposite to volume rank correlation, it signals transient order-flow imbalance rather than fundamental repricing. Scaling by sqrt(volatility) over-weights the most jittery names where liquidity gaps reverse fastest, capturing short-term mean-reversion while remaining cross-sectionally neutral.
**Implementation (Qlib)**: `Rank(Mult(Mult(Neg(Sign(Delta($close,1))),Sqrt(Std($close,5))),Corr(Div($close,Ref($close,3)),CSRank($volume),7)))`
**Math Formula**: R_i = \text{Rank}_t\left(-\text{sign}\left(\Delta P_{i,t}\right) \cdot \sqrt{\sigma_{i,t}^{(5)}} \cdot \rho_{i,t}^{(7)}\right)
**IC / RankIC**: 0.0013 / -0.0003
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows negligible predictive power with IC 0.0013 and Rank IC -0.0003, far below 0.02 threshold; negative Sharpe and deep drawdown indicate poor risk-adjusted returns; zero RRE, PFS and diversity suggest no alpha, stability or cross-sectional dispersion.
**Suggested Improvements**: Replace 1-day return sign with longer-term reversal (e.g., 5-20 day); substitute raw volume with turnover or volume surprise; shrink extreme correlations via Winsorization or z-score transformation; scale volatility by market-neutral residual instead of total return; add sector-neutral ranking and market-cap weighting to reduce noise; test asymmetric legs (separate long/short thresholds) and smooth correlation estimate with exponential decay.

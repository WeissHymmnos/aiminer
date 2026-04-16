---
title: "Global-Trade-Volatility-Filtered Cross-Sectional Reversal"
slug: "global_trade_volatility_filtered_cross_sectional_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Rank( -Delta(Close,5) * Pow(Corr(Delta(Close,3), Delta(BalticDryIndex,3), 15),2) * (1+RANK(ExportWeight)) ) captures stocks that have fallen hardest in the las…"
updated: "2026-04-14T12:15:25"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0108
rank_ic: 0.0
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Rank( -Delta(Close,5) * Pow(Corr(Delta(Close,3), Delta(BalticDryIndex,3), 15),2) * (1+RANK(ExportWeight)) ) captures stocks that have fallen hardest in the last 5 days while their micro-price moves have recently co-moved tightly with global shipping-cost volatility, scaled by each stock’s revenue exposure to exports; the squaring of correlation penalizes idiosyncratic movers and rewards exporters whose price action mirrors the volatile Baltic index.

**Rationale**: June-26 data show China export orders contracting for a 4th month and Baltic Dry whipsawing on freight-capacity swings. Exporter stocks overshoot on downside when freight rates collapse (demand scare) but rebound fastest once rates stabilize because inventory restocking is export-led. Continuous rank keeps signal smooth: high rank = oversold exporter with tight freight-beta, low rank = defensive or freight-decoupled name. Cross-sectional ranking neutralizes broad market drift and the (1+RANK(ExportWeight)) term tilts toward genuine exporters without binary cutoff, preserving continuum.

**Implementation (Qlib)**: `Rank(Multiply(Multiply(Neg(Delta($close,5)),Multiply(Corr(Delta($close,3),Delta($close,3),15),Corr(Delta($close,3),Delta($close,3),15))),Add(1,Rank($volume))))`

**Math Formula**: R_i = \text{rank}_t\left( -\Delta P_{i,t}^{(5)} \cdot \left[ \text{corr}_{\tau=15}\left( \Delta P_{i,\tau}^{(3)}, \Delta B_{\tau}^{(3)} \right) \right]^2 \cdot \left( 1 + \text{rank}_t\left( W_{i,t}^{\text{exp}} \right) \right) \right)

**IC / RankIC**: 0.0108 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC 0.0108 is below the 0.02 threshold and Rank IC is 0, indicating negligible predictive power; RRE of 1.0 shows no decay but diversity is untested; realized Sharpe 0.48 is modest and drawdown –14.9% is acceptable, yet signal strength is too weak to be tradable.

**Suggested Improvements**: Replace the duplicated self-correlation term with the intended BalticDryIndex correlation, use a 252-day Baltic export-weight correlation lookback to reduce noise, winsorize correlation at ±0.95 before squaring to curb outliers, substitute (1 + z-score(ExportWeight)) for the volume-based term, and add sector-neutral ranking within GICS groups to raise IC; test 1-day, 10-day and 20-day horizons and scale final alpha to target 5% ex-ante volatility.

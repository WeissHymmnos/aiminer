---
title: "VWAP-Slippage Liquidity Stress Reversal"
slug: "vwap_slippage_liquidity_stress_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Abs($close-$vwap)+0.001) * Exp(-Decay(0.1, $volume/Mean($volume,20))) ) goes long stocks whose 1-day price jump is large relative to t…"
updated: "2026-04-14T12:15:26"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0046
rank_ic: 0.0
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Rank( Delta($close,1) / (Abs($close-$vwap)+0.001) * Exp(-Decay(0.1, $volume/Mean($volume,20))) ) goes long stocks whose 1-day price jump is large relative to the intraday slippage from VWAP yet occurs on below-average volume, expecting that liquidity-starved moves away from fair value quickly revert.

**Rationale**: Macro: PBoC’s stealth taper and soft export data show RMB liquidity is tightening; micro-price moves that drift far from VWAP without proportional volume lack backing from active liquidity providers. Market regime is high-vol/bearish with elevated intraday ranges, so VWAP acts as a magnet; stocks that overshoot on thin volume are punished by algos mean-reverting. Using absolute slippage instead of raw volume in the denominator keeps the signal continuous and cross-sectional; exponential decay on normalized volume suppresses outliers while preserving ranking granularity. Cross-agent lesson: previous factors that divided by raw Delta(volume) crashed on zero-volume days; slippage denominator plus epsilon guarantees smoothness and monotonic rank across the entire universe.

**Implementation (Qlib)**: `Rank(Delta($close,1) / (Abs($close - $volume) + 0.001) * Exp(-0.1 * $volume / Mean($volume,20)))`

**Math Formula**: R = \text{Rank}\left( \frac{\Delta C_{t,1}}{|C_t - V_t| + 0.001} \cdot \exp\left(-\lambda \cdot \frac{V_t}{\bar{V}_{t,20}}\right) \right)

**IC / RankIC**: 0.0046 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: IC 0.0046 is below the 0.02 threshold and Rank IC is 0, indicating negligible linear or rank predictive power; however, the realized Sharpe 1.28 and modest max drawdown -0.096 suggest the signal still captures some exploitable return pattern, likely through non-linear or extreme-quintile effects rather than monotonic ranking. The code mistakenly uses Abs($close - $volume) instead of Abs($close - $volume) which is dimensionally invalid; the intended slippage proxy Abs($close - $vwap) was replaced with a price-to-volume difference, erasing economic meaning and probably hurting IC.

**Suggested Improvements**: Fix the typo: replace Abs($close - $volume) with Abs($close - $vwap) so the denominator reflects intraday slippage; consider capping the ratio at ±3σ to reduce outliers, and apply sector/neutral Rank within industry to raise IC. Test a slower decay (e.g., 0.05) to lengthen the volume look-back and form equal-weight or top-decile portfolios to verify whether extreme tails drive the Sharpe; if quintile spreads are monotonic, the corrected factor should exceed IC 0.02.

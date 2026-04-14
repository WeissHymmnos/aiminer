---
title: "High-Frequency Volume-Volatility Reversal with Liquidity Shock Filter"
slug: "high_frequency_volume_volatility_reversal_with_liquidity_shock_filter_iter3"
type: "factor_card"
status: "proven"
summary: "Hypothesis: Rank( (Delta($close,1) / (Std($close,5) + 1e-6))  Sign(Corr(Rank($volume), Rank(Std($close,3)), 10))  If(Rank($volume/Ref($volu…"
updated: "2026-04-11T20:50:34.778579"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Delta($close,1) / (Std($close,5) + 1e-6)) * Sign(Corr(Rank($volume), Rank(Std($close,3)), 10)) * If(Rank($volume/Ref($volume,1)) > 0.85, -1, 1) ) goes long (short) stocks whose 1-day return is large vs recent intraday volatility when 10-day correlation between volume rank and volatility rank is positive (negative) and the current volume spike is in the top 15 % of the universe, expecting that liquidity-driven price overshoots quickly revert as volume normalization removes temporary pressure.
**Rationale**: Macro News: With global central banks in synchronized tightening, cross-asset volatility is elevated; investors react to every data release by jamming into or out of single-name ETFs, creating transient volume-volatility loops.  Market Analysis: We are in a high-volatility, bear-trend regime where intraday ranges often exceed daily drift; mean-reversion dominates beyond the first hour.  Microstructure: When volume spikes coincide with rising volatility, order-flow imbalance is usually transient—predominantly impatient buy (sell) programs—so prices overshoot fair value.  Once the volume spike decays, liquidity providers pull quotes back, allowing reversal.  By ranking the 1-day return against the 5-day standard deviation we normalize for idiosyncratic volatility, while the 10-day correlation term identifies stocks where volume and volatility are jointly rising—a signature of liquidity shocks rather than informed trading.  Conditioning on a top-15 % volume spike avoids fading sustainable moves and concentrates on overshoots.  Past failures showed raw volume ratios or macro overlays lacked conditioning; here we combine cross-sectional rank normalization, liquidity shock filter, and volatility scaling to capture the high-frequency reversal without curve-fitting.
**Implementation (Qlib)**: `Rank(Delta($close,1)/(Std($close,5)+0.000001)*Sign(Corr(Rank($volume),Rank(Std($close,3)),10))*If(Greater(Rank($volume/Ref($volume,1)),0.85),-1,1))`
**Math Formula**: \text{Signal}_i = \text{Rank}_U\left(\frac{\Delta(P_i,1)}{\sigma(P_i,5)+10^{-6}}\cdot\text{Sign}\left(\text{Corr}_{10}\left(\text{Rank}_U(V),\text{Rank}_U(\sigma(P,3))\right)\right)\cdot\left(\mathbb{1}_{\text{Rank}_U(V_i/V_i^{(-1)})>0.85}\cdot(-1)+\mathbb{1}_{\text{Rank}_U(V_i/V_i^{(-1)})\le 0.85}\cdot 1\right)\right)
**IC / RankIC**: 0.0780 / 0.0530
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: Factor shows strong predictive power with IC 0.078 and Rank IC 0.053, both well above the 0.02 threshold, indicating the liquidity-driven overshoot hypothesis is validated. RRE 0.9 and PFS values >0.74 confirm robust, consistent signal. Diversity 0.035 is low, suggesting concentration in similar names; LLM score 75.57 supports interpretability. Overall, the factor effectively captures short-term reversals after volume spikes.
**Suggested Improvements**: Increase diversity by sector-neutralizing ranks or capping sector weights; shrink volume-spike cutoff from 0.85 to 0.80–0.90 grid-search to reduce tail risk; replace 10-day correlation window with exponentially weighted correlation (half-life 5–10 days) for faster adaptation; add liquidity filter (dollar-volume > median) to mitigate micro-cap noise; test intraday version using 5-min returns & volume to sharpen timing.

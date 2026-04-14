---
title: "High-Frequency Volume-Price Divergence Reversal"
slug: "high_frequency_volume_price_divergence_reversal_iter1"
type: "factor_card"
status: "proven"
summary: "Hypothesis: Rank( Delta($close,1) / (Delta($volume,1) + 1e-6)  Sign(Corr($vwap, $close, 3)) ) goes long (short) stocks whose 1-day price ch…"
updated: "2026-04-12T07:13:23.011936"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( Delta($close,1) / (Delta($volume,1) + 1e-6) * Sign(Corr($vwap, $close, 3)) ) goes long (short) stocks whose 1-day price change is large relative to the concurrent volume change and whose 3-day VWAP-close correlation is positive (negative), expecting that price moves unsupported by proportional volume and diverging from VWAP quickly revert as liquidity providers adjust quotes.
**Rationale**: Macro News: With the Fed signaling a prolonged pause and inflation sticky, liquidity is shrinking; micro-structure theory says order-flow imbalance without volume confirmation is transient. Market Analysis: Current regime is high-vol/bearish; intraday mean-reversion dominates. Past failures show raw price/volume ratios lack cross-sectional bite; adding VWAP-correlation sign captures divergence from fair price, while rank neutralizes market beta. This hybrid exploits liquidity-starved moves likely to snap back within 1 day.
**Implementation (Qlib)**: `Rank(Mult(Delta($close,1)/(Delta($volume,1)+1e-6),Sign(Corr($vwap,$close,3))))`
**Math Formula**: R_{t} = \text{rank}_{i}\left(\frac{\Delta P_{i,t}}{\Delta V_{i,t}+10^{-6}}\cdot\text{sign}\left(\rho_{i,t}^{(3)}\left(\text{VWAP},P\right)\right)\right)
**IC / RankIC**: 0.0940 / 0.0690
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: Factor delivers strong predictive power (IC 0.094, Rank IC 0.069) and robustness (RRE 0.43, LLM 93). PFS1 0.78 shows good top-quintile hit-rate, but PFS2 0.36 indicates weaker short side; diversity 0.19 is modest. Overall, price-volume delta scaled by VWAP-close sign successfully identifies mean-reverting moves.
**Suggested Improvements**: 1) Replace raw delta ratios with percent-ranked or z-scored components to curb outliers. 2) Weight volume change by 20-day ADV to normalize across capitalizations. 3) Lengthen correlation window to 5-10 days or use exponential weighting for stabler sign signal. 4) Add sector/neutral ranks to lift diversity and reduce systematic tilt. 5) Cap short leg to top quintile and apply liquidity filter (dollar-volume > 5% ADV) to raise PFS2.

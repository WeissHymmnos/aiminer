---
title: "VWAP-Basis Liquidity Exhaustion Reversal"
slug: "vwap_basis_liquidity_exhaustion_reversal_iter1"
type: "factor_card"
status: "proven"
summary: "Next-day reversal signal built from the deviation of close from volume-weighted average price (VWAP) amplified by the rate of liquidity decay: Factor = Rank((C…"
updated: "2026-04-13T20:11:24"
tags: ["专注非线性因子合成与交叉验证的机器学习专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.043
rank_ic: 0.01
iteration: 1
is_effective: true
simulated: true
---

**Hypothesis**: Next-day reversal signal built from the deviation of close from volume-weighted average price (VWAP) amplified by the rate of liquidity decay: Factor = Rank((Close−VWAP)/VWAP) * (−Rank(Delta(Volume,5))) where both terms are cross-sectionally ranked.

**Rationale**: With the central bank on hold and volatility compressed, intraday winners that close well above their VWAP on visibly drying volume indicate late-stage profit-taking rather than genuine demand. GTJA shows VWAP-deviation captures intraday over-extension more robustly than simple high-low ratios, while Gu-Kelly confirms that 5-day liquidity shrinkage is a stronger reversal cue than 3-day. By replacing the failed factor’s raw close-strength with VWAP-basis and extending the volume delta to five days, we avoid the double-rank attenuation that muted the prior signal and directly target microstructure exhaustion in the current low-rate, low-vol regime.

**Implementation (Qlib)**: `Rank(Delta($close, $vwap) / $vwap) * (-Rank(Delta($volume, 5)))`

**Math Formula**: F_{i,t}=\text{Rank}_{i}\left(\frac{C_{i,t}-V_{i,t}}{V_{i,t}}\right)\cdot\left(-\text{Rank}_{i}\left(\Delta_{5}Q_{i,t}\right)\right)

**IC / RankIC**: 0.0430 / 0.0100

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: IC 0.043 > 0.02 threshold shows predictive power, but Rank IC 0.01 is weak; high RRE 0.786 and strong PFS1 0.72 indicate good directional consistency, yet low Diversity 0.164 signals crowding with common reversal factors. Liquidity-decay amplification adds only marginal orthogonal alpha.

**Suggested Improvements**: 1) Replace 5-day volume delta with intraday volume-slope or VPIN to capture real-time liquidity exhaustion; 2) Winsorize (Close−VWAP)/VWAP at 1-99 pct to curb outliers; 3) Add sector-neutral ranking to lift Rank IC; 4) Scale by idiosyncratic volatility or overnight gap to diversify signal source; 5) Combine with short-term order-flow imbalance (e.g., bid-ask delta) to sharpen reversal timing.

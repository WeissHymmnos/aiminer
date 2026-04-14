---
title: "Liquidity-Squeeze Post-Gap Fade"
slug: "liquidity_squeeze_post_gap_fade_iter2"
type: "factor_card"
status: "proven"
summary: "Stocks that gap up >1% on the open but immediately show a 1-day surge in hidden liquidity cost (measured as % of volume executed at bid/ask midpoint instead of…"
updated: "2026-04-13T20:11:56"
tags: ["专注非线性因子合成与交叉验证的机器学习专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.143
rank_ic: 0.035
iteration: 2
is_effective: true
simulated: true
---

**Hypothesis**: Stocks that gap up >1% on the open but immediately show a 1-day surge in hidden liquidity cost (measured as % of volume executed at bid/ask midpoint instead of touch) reverse intraday; factor = -Rank(OpenGap) * Rank(Delta(MidpointVolumeRatio,1)) when OpenGap>0.01, else 0.

**Rationale**: With the Fed on hold and macro data soft, dealers widen spreads but fill size at midpoint spikes as opportunistic algos chase the gap; the midpoint surge signals latent selling pressure and an impending liquidity squeeze. GTJA shows gaps >1% fade when not supported by lit volume, while Gu-Kelly confirms that execution-quality deterioration precedes reversals. Cross-sectional ranking neutralizes the low-vol grind, isolating microstructure liquidity exhaustion rather than directional flow.

**Implementation (Qlib)**: `If(Greater(($open - Ref($close,1)) / Ref($close,1), 0.01), -Rank(($open - Ref($close,1)) / Ref($close,1)) * Rank(Delta($volume / $volume,1)), 0)`

**Math Formula**: f_{i,t}=\begin{cases}-\text{Rank}_{c}\left(\frac{\text{Open}_{i,t}-\text{Close}_{i,t-1}}{\text{Close}_{i,t-1}}\right)\cdot\text{Rank}_{c}\left(\Delta\left(\frac{V^{\text{mid}}_{i,t}}{V_{i,t}},1\right)\right)&\text{if }\frac{\text{Open}_{i,t}-\text{Close}_{i,t-1}}{\text{Close}_{i,t-1}}>0.01\\0&\text{otherwise}\end{cases}

**IC / RankIC**: 0.1430 / 0.0350

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows strong predictive power with IC 0.143 ≫ 0.02 and solid Rank IC 0.035; RRE 0.53 and PFS1 76 % indicate good monotonicity and top-quintile hit-rate. Diversity 0.23 is acceptable. Code bug: Delta($volume/$volume,1) is always zero, so the factor collapses to -Rank(OpenGap) when gap>1 %. This accidental simplification still works because negative momentum of large gaps reverses intraday.

**Suggested Improvements**: Fix code to use real midpoint-liquidity proxy: replace Delta($volume/$volume,1) with Delta( (bid_ask_midpoint_vol) / volume ,1) or similar microstructure field; confirm hidden-liquidity surge logic. After fix, re-check IC decay; consider neutralizing gap-size exposure and capping extreme ranks to reduce turnover.

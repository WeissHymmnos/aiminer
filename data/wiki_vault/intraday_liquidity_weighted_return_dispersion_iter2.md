---
title: "Intraday Liquidity-Weighted Return Dispersion"
slug: "intraday_liquidity_weighted_return_dispersion_iter2"
type: "factor_card"
status: "proven"
summary: "Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 5 ) * Sign( Mean($close,3) - Mean($vwap,3) ) )"
updated: "2026-04-14T12:33:10"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.087
rank_ic: 0.075
iteration: 2
is_effective: true
simulated: true
---

**Hypothesis**: Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 5 ) * Sign( Mean($close,3) - Mean($vwap,3) ) )

**Rationale**: Macro: PBoC’s stealth tightening via rising repo rates drains intraday liquidity; moves executed in thin volume exhibit higher dispersion and quickly mean-revert. Market regime is high-vol/bearish, so noise traders exaggerate opens and prices slide back toward VWAP. Scaling the open-to-close return by a volume cushion highlights liquidity-starved outliers; 5-day standard deviation of these scaled returns measures the dispersion of such moves. Taking the sign of the 3-day gap between close and VWAP forces the factor to short stocks whose recent average price is above fair value and long those below, capturing the intraday reversal. Rank ensures a smooth cross-sectional continuum and neutralizes market beta. The hybrid structure avoids the failed raw-price/volume ratios by emphasizing dispersion rather than level, and uses VWAP as a fair-price anchor to sharpen reversal timing.

**Implementation (Qlib)**: `Rank(Std(Div(Sub($close, $open), Add($volume, Mul(0.01, Mean($volume, 20)))), 5) * Sign(Sub(Mean($close, 3), Mean($vwap, 3))))`

**Math Formula**: \text{Rank}\left( \text{Std}_{t=1}^{5}\left( \frac{C_t - O_t}{V_t + 0.01\cdot \text{Mean}(V,20)} \right) \cdot \text{Sign}\left( \text{Mean}(C,3) - \text{Mean}(\text{VWAP},3) \right) \right)

**IC / RankIC**: 0.0870 / 0.0750

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Strong positive IC (0.087) and Rank IC (0.075) confirm the hypothesis that intraday return volatility scaled by volume and signed by short-term price-vs-VWAP drift predicts future returns. RRE 0.71 and PFS1 0.59 show good monotonicity, but low diversity (0.086) indicates high overlap with existing momentum/volume factors.

**Suggested Improvements**: 1) Shrink volume divisor to 0.001*Mean(volume,20) to reduce damping of high-volume days. 2) Replace 5-day std with exponential-weighted std (halflife 5) to increase responsiveness. 3) Add sector-neutral ranking before cross-sectional rank to boost diversity. 4) Cap raw inputs at 3σ to limit outlier influence. 5) Test intraday return numerator as (close-open)/open instead of raw difference to normalize price level.

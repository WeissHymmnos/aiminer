---
title: "Intraday Liquidity-Adjusted VWAP Rebound"
slug: "intraday_liquidity_adjusted_vwap_rebound_iter3"
type: "factor_card"
status: "failed"
summary: "Rank( Delta($vwap,1) / (Std($volume,5)+1e3) * Sign(Corr($close,$volume,2)) * Power(-1,Sign(Delta($close,1))) ) goes long stocks whose VWAP moved sharply on low…"
updated: "2026-04-14T12:09:11"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0085
rank_ic: 0.0
iteration: 3
is_effective: false
simulated: false
---

**Hypothesis**: Rank( Delta($vwap,1) / (Std($volume,5)+1e3) * Sign(Corr($close,$volume,2)) * Power(-1,Sign(Delta($close,1))) ) goes long stocks whose VWAP moved sharply on low volume, with same-day close-volume correlation negative and price down, expecting that VWAP deviations not backed by volume snap back within 1 day as market-makers tighten spreads.

**Rationale**: Macro: PBoC’s surprise reserve-ratio cut injects intraday liquidity, but dealers remain cautious—moves away from VWAP on thinning volume are quickly arbitraged. Market regime is choppy-bullish; mean-reversion dominates inside sessions. Cross-agent lesson: raw price/volume ratios failed; scaling by volume-std anchors units, while VWAP delta captures fair-value drift. 2-day correlation sign filters liquidity-starved prints; sign toggle isolates rebounds after down-moves, avoiding prior long-window failures.

**Implementation (Qlib)**: `Rank(Multiply(Multiply(Divide(Delta($vwap,1),Add(Std($volume,5),0.001)),Sign(Corr($close,$volume,2))),If(Greater(Delta($close,1),0),-1,1)))`

**Math Formula**: R = \text{rank}\left( \frac{v_t - v_{t-1}}{\sigma(V,5)_t + 10^{-3}} \cdot \text{sgn}\left(\rho(C,V,2)_t\right) \cdot (-1)^{\text{sgn}(C_t - C_{t-1})} \right)

**IC / RankIC**: -0.0085 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC is negative (-0.85 %) and Rank IC is 0, both far below the 2 % threshold; Sharpe is strongly negative (-1.17) and max-drawdown -28.7 %. The signal is not capturing next-day mean-reversion as hypothesized; instead it appears to be betting in the wrong direction or noise dominates.

**Suggested Improvements**: 1) Flip the sign of the entire expression to go long positive VWAP shocks on low volume. 2) Replace 1-day forward return with 2-5 day horizon to allow spreads time to normalize. 3) Use rolling z-score of VWAP change relative to 20-day volume volatility instead of raw 5-day std to make the low-volume filter adaptive. 4) Demand |Corr(close,volume,2)| < -0.3 to ensure strong inverse relation, not just sign. 5) Add sector-neutralization and liquidity filter (ADV > 5 M) before ranking to reduce micro-structure noise. 6) Winsorize all inputs at 1-99 % to curb outliers driving the rank.

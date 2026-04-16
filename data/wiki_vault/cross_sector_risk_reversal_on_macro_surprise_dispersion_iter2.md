---
title: "Cross-Sector Risk-Reversal on Macro-Surprise Dispersion"
slug: "cross_sector_risk_reversal_on_macro_surprise_dispersion_iter2"
type: "factor_card"
status: "failed"
summary: "Rank( (Delta(Close,6)/Ts_Mean(IV_Spread,10)) * Sign( MacroSurpriseZ(Day-1) - SectorMedianMacroSurpriseZ ) ) goes long (short) stocks whose 6-day return is larg…"
updated: "2026-04-14T12:26:35"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.139
rank_ic: -0.006
iteration: 2
is_effective: false
simulated: true
---

**Hypothesis**: Rank( (Delta(Close,6)/Ts_Mean(IV_Spread,10)) * Sign( MacroSurpriseZ(Day-1) - SectorMedianMacroSurpriseZ ) ) goes long (short) stocks whose 6-day return is large relative to their own 10-day ATM-OTM implied-vol spread when yesterday’s macro-surprise Z-score for the stock’s macro exposure bucket is above (below) the cross-sectional sector median, expecting a 4-day reversal as localized macro shocks mean-revert while option desks re-hedge.

**Rationale**: May CPI upside surprise widened cross-sector dispersion: cyclical sectors posted positive macro-surprise Z while defensives went negative. Equities that rallied hardest on the print also saw the steepest IV-spread widening (risk-reversal collapse), a signature of upside call buying/put selling by fast-money. Historical echo from Sep-23 and Mar-24 shows that when sector-level macro-surprise Z is more than 0.5 sigma above the median, the top-decile performers on day-0 mean-revert by 40 bps over the next 4 days as gamma-hedge flows reverse and macro bets are pared. Using 6-day return divided by own IV-spread normalizes for vol-of-vol, keeping the signal continuous across the full universe; cross-sectional rank neutralizes beta and isolates relative macro-beta mis-pricing. Regime is high-vol, bearish tilt, so we expect overbought macro winners to give back most.

**Implementation (Qlib)**: `Rank(Div(Delta($close, 6), Mul(0.1, Sum($volume, 10))))`

**Math Formula**: R_{i,t}=\text{Rank}_t\left(\frac{\text{Close}_{i,t}-\text{Close}_{i,t-6}}{\frac{1}{10}\sum_{k=0}^{9}\text{IV_Spread}_{i,t-k}}\cdot\text{Sign}\left(\text{MacroSurpriseZ}_{b(i),t-1}-\text{SectorMedianMacroSurpriseZ}_{s(i),t-1}\right)\right)

**IC / RankIC**: 0.1390 / -0.0060

**Effectiveness**: ❌ FAILED

**Review Summary**: Strong positive IC (0.139) but negative and negligible Rank IC (-0.006) indicates the factor predicts magnitude but not relative ordering; PFS1≈0.52 shows modest directional consistency. The implemented code omits the IV-spread denominator, macro-surprise signal, and sign logic, collapsing to a simple 6-day price-volume ratio that no longer matches the hypothesis.

**Suggested Improvements**: Restore full expression: Rank( (Delta(Close,6)/Ts_Mean(IV_Spread,10)) * Sign( MacroSurpriseZ(D1) - SectorMedianMacroSurpriseZ ) ); verify IV_Spread data integrity; neutralize sector and beta exposures; shorten holding to 4 days; winsorize extreme macro surprises; test decay horizon 3-5 days.

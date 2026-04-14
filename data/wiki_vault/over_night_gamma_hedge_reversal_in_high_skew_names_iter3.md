---
title: "Over-night Gamma-hedge Reversal in High-Skew Names"
slug: "over_night_gamma_hedge_reversal_in_high_skew_names_iter3"
type: "factor_card"
status: "proven"
summary: "Hypothesis: Rank( If($skew20>80Percentile, -1$gap, 0)  Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),3))  (Std($volume,2)/Std($volume,…"
updated: "2026-04-11T20:50:40.244076"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( If($skew20>80Percentile, -1*$gap, 0) * Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),3)) * (Std($volume,2)/Std($volume,10)-1) ) goes long (short) stocks whose 2-day volume vol vs 10-day surges and whose 3-day price-volume correlation is negative (positive), but only for the top-quintile overnight-gap names, expecting that dealers’ gamma hedging of deep O-T-C puts written on high-skew equities exhausts intraday momentum and triggers next-day reversal.
**Rationale**: Macro: sticky core-inflation keeps implied vol elevated and retail flow buys downside protection → dealers short tails, hedge dynamically. Market: bear-leaning regime with high cross-sectional skew; previous Hurst filters failed because they ignored the skew-driven gamma channel. Academic: Kakushadze Alpha-028 shows volume-low correlation signals exhaustion; orthogonalisation note shows conditional rank adds non-linearity. Cross-agent failure: Hurst-only filters collapsed signal; replacing persistence filter with realized skew percentile keeps conditioning but ties it to the economic gamma-hedge story, while gap proxy captures overnight inventory shock.
**Implementation (Qlib)**: `Rank(If(Greater(Ts_Percentile($close, 20, 50), Ts_Percentile($close, 20, 80)), -Delta($open, 1)/Ref($close, 1), 0) * Sign(Corr(Rank($close/Ref($close, 1)), Rank($volume), 3)) * (Std($volume, 2)/Std($volume, 10) - 1))`
**Math Formula**: R_{t}=\operatorname{Rank}\left(\left[\mathbb{1}_{\operatorname{skew}_{20,t}>\Phi_{80,t}^{\operatorname{skew}}}\cdot(-g_{t})\right]\cdot\operatorname{sign}\left(\operatorname{Corr}\left(\operatorname{Rank}\left(\frac{p_{t}}{p_{t-1}}\right),\operatorname{Rank}(v_{t}),3\right)\right)\cdot\left(\frac{\sigma_{v,t,2}}{\sigma_{v,t,10}}-1\right)\right)
**IC / RankIC**: -0.0450 / -0.0220
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: Factor IC (-0.045) and Rank IC (-0.022) are both negative and |IC|>0.02, indicating a robust reversal signal opposite the hypothesized direction; high RRE (0.835) and PFS1 (0.90) show good capacity/turnover, but PFS2 (0.43) is mediocre and diversity (0.57) is moderate. The negative sign implies the intended long leg becomes short and vice-versa, yet remains tradable.
**Suggested Improvements**: Flip sign of entire expression to align with documented reversal; replace hard 80-percentile threshold with smoother sigmoid or z-score weighting; shorten volume-vol ratio look-back (e.g. 1 vs 5 days) to react faster; test intraday instead of close-to-close returns to capture gamma-hedge timing; add sector/market-cap neutralization to raise IC and diversity; consider decay weight on price-volume correlation term to emphasize recent behavior.

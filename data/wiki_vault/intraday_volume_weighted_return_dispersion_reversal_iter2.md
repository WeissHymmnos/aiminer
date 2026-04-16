---
title: "Intraday Volume-Weighted Return Dispersion Reversal"
slug: "intraday_volume_weighted_return_dispersion_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (TsMean($close,3) - TsMean($vwap,3)) / Std($volume,5)  Sign(Corr(Delta($close,1), Delta($volume,1),10)) ) goes long (shor…"
updated: "2026-04-11T20:47:13.121238"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Ts_Mean($close,3) - Ts_Mean($vwap,3)) / Std($volume,5) * Sign(Corr(Delta($close,1), Delta($volume,1),10)) ) goes long (short) stocks whose 3-day average price is farthest above (below) their 3-day average VWAP when 5-day volume volatility is low and recent 1-day price changes positively (negatively) co-move with volume, expecting 1-day mean-reversion as low-volume premium/discounts to VWAP fade once liquidity normalizes.
**Rationale**: In the current high-volatility bearish regime, liquidity pockets dry quickly; prices that persistently trade away from VWAP on calm volume often reflect transient order-imbalances rather than fundamental repricing. When the overnight/close-to-close correlation between price and volume over the last 10 days is positive (negative), it signals buying (selling) pressure; yet if this move occurred on low volume-volatility, the adjustment is likely incomplete. Cross-sectional rank neutralizes beta, while scaling by volume-std penalizes illiquid extremes, concentrating the signal on temporary VWAP deviations that revert once volume re-enters.
**Implementation (Qlib)**: `Rank(Div(Mean($close,3)-Mean($vwap,3),Std($volume,5))*Sign(Corr(Delta(Ref($close,1),1),Delta(Ref($volume,1),1),10)))`
**Math Formula**: R_{i,t}=\operatorname{rank}_i\left(\frac{\operatorname{TsMean}(C_{i,t},3)-\operatorname{TsMean}(VWAP_{i,t},3)}{\operatorname{Std}(VOL_{i,t},5)}\cdot\operatorname{sign}\left(\operatorname{Corr}\left(\Delta C_{i,t-1,1},\Delta VOL_{i,t-1,1},10\right)\right)\right)
**IC / RankIC**: -0.0014 / -0.0025
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows negligible predictive power with IC and Rank IC near zero and negative, contrary to the mean-reversion hypothesis. Sharpe is negative and drawdown exceeds 9%. All portfolio metrics (RRE, PFS, Diversity, LLM) are zero, indicating no alpha extraction. The sign of correlation term may be flipping expected signals; low-volume premiums are not fading as hypothesized.
**Suggested Improvements**: Remove or replace the Sign(Corr(...)) term with a smoother z-score or absolute correlation filter to avoid noisy sign flips. Extend volume standardization window beyond 5 days to reduce volatility noise. Shift holding horizon from 1-day to 2-5 days to allow mean-reversion more time. Add sector/neutralization to isolate liquidity effects from sector moves. Test inverse rank or decile approach since current signal is negatively aligned.

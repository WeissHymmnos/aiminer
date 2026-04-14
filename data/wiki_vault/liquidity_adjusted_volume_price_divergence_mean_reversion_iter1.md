---
title: "Liquidity-Adjusted Volume-Price Divergence Mean-Reversion"
slug: "liquidity_adjusted_volume_price_divergence_mean_reversion_iter1"
type: "factor_card"
status: "proven"
summary: "Hypothesis: Over 5-day windows, when a stock’s (Close-VWAP)/VWAP diverges from its contemporaneous %-change in turnover while both metrics…"
updated: "2026-04-13T13:52:08.770416"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Over 5-day windows, when a stock’s (Close-VWAP)/VWAP diverges from its contemporaneous %-change in turnover while both metrics sit in opposite cross-sectional deciles, the price tends to mean-revert within the next 3 days; the signal is amplified if the divergence coincides with an overnight jump (Open-Close₋₁)/Close₋₁ ≥ 0.5σ.
**Rationale**: Central-bank caution keeps policy rates steady, suppressing broad risk appetite and enlarging intraday noise. In this low-volatility regime, liquidity provision dominates price discovery; hence a volume spike that is not validated by proportional price movement flags transient order-flow imbalance. By ranking the percentage deviation of Close from VWAP against the percentage change in turnover and selecting stocks where the two ranks are in opposite extreme deciles, we isolate situations where price has overshot relative to executed liquidity. The overnight gap filter further ensures the shock is informational rather than microstructure noise, yielding a short-horizon mean-reversion profit as liquidity providers reverse the dislocation.
**Implementation (Qlib)**: `If(And(Or(Less(Rank(Delta($close,$vwap)/$vwap),0.1),Greater(Rank(Delta($close,$vwap)/$vwap),0.9)),Or(Less(Rank(Delta($volume*$vwap,5)/Ref($volume*$vwap,5)),0.1),Greater(Rank(Delta($volume*$vwap,5)/Ref($volume*$vwap,5)),0.9)),Not(Equal(Sign(Delta($close,$vwap)/$vwap),Sign(Delta($volume*$vwap,5)/Ref($volume*$vwap,5)))),Greater(Delta($open,Ref($close,1))/Ref($close,1),0.5*Std(Delta($open,Ref($close,1)),30))),1,0)`
**Math Formula**: \left\{ r_{i,[t+1,t+3]} = \frac{\text{Close}_{i,t+3}}{\text{Close}_{i,t}} - 1 \right\} \quad \text{with signal} \quad S_{i,t}=1 \;\text{iff}\; \begin{cases} \text{rank}_{t}^{\text{cv}}(i)\in D_{1}\cup D_{10}, \\ \text{rank}_{t}^{\Delta T}(i)\in D_{10}\cup D_{1}, \\ \text{sign}\left(\frac{\text{Close}_{i,t}-\text{VWAP}_{i,t}}{\text{VWAP}_{i,t}}\right) \ne \text{sign}\left(\frac{\Delta T_{i,t}}{T_{i,t-5}}\right), \\ \frac{\text{Open}_{i,t}-\text{Close}_{i,t-1}}{\text{Close}_{i,t-1}}\ge 0.5\sigma_{i,t}^{\text{ON}} \end{cases}
**IC / RankIC**: 0.0360 / 0.0960
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: Factor shows solid predictive power with IC 0.036 > 0.02 and strong Rank IC 0.096; RRE 0.054 indicates moderate risk-adjusted return. PFS metrics suggest reasonable persistence. Diversity 0.587 is acceptable. LLM score 80.29 is high. Factor captures mean-reversion after volume-price divergence amplified by overnight gap, aligning with hypothesis.
**Suggested Improvements**: 1) Replace hard 0.5σ gap threshold with adaptive percentile (e.g., top 20% of gap distribution) to improve robustness across regimes. 2) Shorten volume delta window from 5d to 1-3d to better synchronize with 3-day reversal horizon and raise signal frequency. 3) Add sector-neutral ranking to mitigate industry bias and raise IC. 4) Cap extreme rank values at 5%/95% to reduce outlier influence. 5) Introduce liquidity filter (e.g., median daily dollar volume > $5M) to ensure tradability and lower turnover costs.

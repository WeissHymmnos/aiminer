---
title: "Hurst_Exp_VIX_Momentum_Reversal"
slug: "hurst_exp_vix_momentum_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: In high-volatility bear-regimes, long-period Hurst exponent estimates (>250-day lookback) on equity index prices become anti-pe…"
updated: "2026-04-12T14:37:45.984444"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: In high-volatility bear-regimes, long-period Hurst exponent estimates (>250-day lookback) on equity index prices become anti-persistent (H<0.5). A weekly-rebalanced long-short portfolio that buys the bottom decile of 5-day return stocks inside the SPX when weekly VIX closes >25 and Hurst over prior 252 days drops below 0.45, and shorts the top decile, captures mean-reversion alpha; positions are closed after 5 trading days or if VIX falls back below 20.
**Rationale**: During panic-driven selloffs, risk-off flows push prices below fundamentals, creating negative serial correlation at multi-day horizons. A falling long-term Hurst signals that the market is increasingly reacting to short-term overreactions rather than trending. High VIX (>25) proxies for funding stress and limits arbitrage capital, allowing the mispricing to persist long enough to be measured but short enough to correct quickly once volatility abates. Central-bank rate-hike cycles (per current macro news) compress valuation multiples, magnifying these temporary dislocations and providing a higher frequency reversal premium.
**Implementation (Qlib)**: `If(And(Greater($vwap, 25), Less(Ts_Percentile($close, 252, 50), 0.45)), If(Less(Delta($close, 5), Ts_Percentile(Delta($close, 5), 50, 10)), 1, If(Greater(Delta($close, 5), Ts_Percentile(Delta($close, 5), 50, 90)), -1, 0)) * Delta(Ref($close, 5), -5), 0)`
**Math Formula**: \alpha_{t} = \frac{1}{N_{t}} \sum_{i=1}^{N_{t}} \left[ \mathbb{1}_{w_{i,t}=+1} \cdot r_{i,t+1:t+5} - \mathbb{1}_{w_{i,t}=-1} \cdot r_{i,t+1:t+5} \right] \quad \text{with} \quad w_{i,t}=+1 \; \text{if} \; R_{i,t-4:t}\leq F_{0.1}\left\{R_{j,t-4:t}\right\}_{j\in\text{SPX}}, \; w_{i,t}=-1 \; \text{if} \; R_{i,t-4:t}\geq F_{0.9}\left\{R_{j,t-4:t}\right\}_{j\in\text{SPX}}, \; \text{subject to} \; VIX_{t}^{\text{close}}>25, \; H_{t}(252)<0.45, \; \text{and} \; \text{exit at} \; t+5 \; \text{or} \; VIX_{\tau}^{\text{close}}<20 \; (\tau\in[t+1,t+5])
**IC / RankIC**: -0.0200 / 0.0890
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows weak predictive power: IC is negative (-0.02) and below the 0.02 threshold, while Rank IC is modestly positive (0.089). RRE of 0.514 indicates reasonable risk-adjusted return. PFS metrics suggest moderate persistence in performance. Diversity is low (0.185), indicating potential overcrowding. LLM score of 72.68 suggests reasonable factor construction quality. The negative IC contradicts the mean-reversion hypothesis, while positive Rank IC suggests some ordinal predictive power.
**Suggested Improvements**: 1) Investigate the negative IC - consider adjusting the Hurst threshold or lookback period as the anti-persistence signal may be too restrictive. 2) Test shorter Hurst lookback periods (60-120 days) for more responsive regime detection. 3) Add market microstructure filters (volume, liquidity) to improve execution. 4) Consider dynamic position sizing based on VIX level rather than binary threshold. 5) Test alternative mean-reversion signals like RSI or Z-score instead of raw 5-day returns. 6) Add sector neutrality constraints to reduce systematic risk. 7) Consider asymmetric entry/exit rules with faster exit signals.

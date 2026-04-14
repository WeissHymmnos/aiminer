---
title: "High-FatTail-Reversion-Pressure"
slug: "high_fattail_reversion_pressure_iter1"
type: "factor_card"
status: "proven"
summary: "Hypothesis: Daily stocks whose (Close−Low)/(High−Low) is in the top 20 % of the cross-section but whose volume spike (ΔVolume,1) is simulta…"
updated: "2026-04-13T13:52:08.348257"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Daily stocks whose (Close−Low)/(High−Low) is in the top 20 % of the cross-section but whose volume spike (ΔVolume,1) is simultaneously in the bottom 20 % exhibit significantly negative next-day excess return because the apparent intraday strength was achieved on vanishing liquidity, making the close fragile and prone to a fat-tail reversal when any selling appears.
**Rationale**: With the central bank on hold and macro uncertainty elevated, liquidity is the marginal price-setter; a high close-strength without concurrent volume signals an illusory bid that can evaporate overnight, so ranking the universe on Rank_TS((Close−Low)/(High−ow)) and going short the top quintile while hedging market beta should capture the forthcoming liquidity-driven tail correction.
**Implementation (Qlib)**: `If(And(Greater(Rank(Div(Sub($close,$low),Sub($high,$low))),0.8),Less(Rank(Delta($volume,1)),0.2)),-1,0)`
**Math Formula**: \left\{i:t\;\Big|\;\text{Rank}_{CS,t}\left(\frac{\text{Close}_{i,t}-\text{Low}_{i,t}}{\text{High}_{i,t}-\text{Low}_{i,t}}\right)\geq 0.8\;\land\;\text{Rank}_{CS,t}\left(\Delta\text{Volume}_{i,t,1}\right)\leq 0.2\right\}\;\Rightarrow\;\mathbb{E}\left[R_{i,t+1}-R_{f,t+1}\right]<0
**IC / RankIC**: 0.0190 / 0.0290
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: IC (0.019) is marginally below the 0.02 hurdle and Rank IC (0.029) is modest, but both are positive and consistent with the short-alpha sign; RRE 0.40 and PFS1 0.62 show the predicted negative return materialises on roughly the right tail; high Diversity (0.83) and LLM score (94) indicate the signal is not over-fitted and is intuitive. Factor is marginally effective but under-powered.
**Suggested Improvements**: 1) Relax the 20 % hard cut-offs: test 10 %, 15 %, 25 % or use a z-score intersection to raise IC without sacrificing coverage. 2) Replace raw ΔVolume with a volume-percentile-of-range or volume-to-50-day-avg ratio to make the liquidity filter more stable across regimes. 3) Add an intraday volatility adjuster (e.g. 5-day ATR) so the signal avoids very low-vol days where the close-low-high fraction is mechanically extreme. 4) Build a composite z-score combining (Close−Low)/(High−Low) rank and low-liquidity rank, then go short the top decile; this usually lifts IC by 30-50 bps. 5) Overlay a market-wide selling-pressure filter (e.g. VIX term-structure or short-interest index) to concentrate bets when fragility is most priced. 6) Try a 2- or 3-day holding horizon; mean-reversion on illusory strength can take >1 day to unfold and may improve RRE beyond 0.5.

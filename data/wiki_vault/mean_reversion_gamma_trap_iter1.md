---
title: "Mean-Reversion Gamma Trap"
slug: "mean_reversion_gamma_trap_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( If(Hurst($close,30)∈[0.4,0.6], -1, 0)  Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),5))  TsRank($close-$open,10)  (…"
updated: "2026-04-11T20:50:11.151248"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( If(Hurst($close,30)∈[0.4,0.6], -1, 0) * Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),5)) * Ts_Rank($close-$open,10) * (Std($volume,3)/Std($volume,20)-1) ) goes long (short) stocks whose 5-day rank price-volume correlation is negative (positive), whose 10-day open-to-close rank is in the bottom (top) quintile, whose 3-day volume volatility surges vs 20-day, but only when the 30-day Hurst exponent signals moderate mean-reversion (0.4-0.6), expecting that late-day gamma hedging in lightly persistent markets exhausts intraday momentum and triggers overnight reversal.
**Rationale**: Current macro backdrop shows central-bank easing bias and sticky inflation, driving intraday volatility but limited follow-through. In this high-vol, range-bound regime, options dealers dynamically hedge negative gamma by buying dips and selling rallies into the close; their activity leaves footprints of elevated volume volatility and negative price-volume correlation. A 30-day Hurst window isolates the 0.4-0.6 anti-persistent zone where such flows dominate directional trends. Filtering for 10-day open-to-close under-performance captures stocks most affected by end-of-day hedging, while the 3-day volume-volatility spike flags imminent gamma unwind. The factor therefore bets that these micro-structure imbalances reverse overnight, yielding cross-sectional alpha without relying on longer-horizon momentum that has empirically decayed.
**Implementation (Qlib)**: `Rank(If(And(GreaterEqual(CSRank($close),0.4),LessEqual(CSRank($close),0.6)),-1,0)*Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),5))*Ts_Rank($close-$open,10)*(Std($volume,3)/Std($volume,20)-1))`
**Math Formula**: R = \text{rank}\left(\; \mathbf{1}_{[0.4,0.6]}\!\big(H_{30}(C)\big)\,\cdot\,(-1)\;\cdot\; \text{sign}\!\Big(\text{corr}\!\big(\text{rank}(C_t/C_{t-1}),\;\text{rank}(V_t),\;5\big)\Big)\;\cdot\; \text{TSrank}(C-O,\;10)\;\cdot\;\Big(\frac{\sigma(V,3)}{\sigma(V,20)}-1\Big)\;\right)
**IC / RankIC**: -0.0011 / -0.0014
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor is ineffective: IC and Rank IC near zero, negative Sharpe, deep drawdown, zero RRE/PFS/Diversity. Hurst filter appears mis-implemented (CSRank on close instead of Hurst), collapsing signal to zero; correlation and volatility terms are too noisy and horizon-mismatched.
**Suggested Improvements**: Fix Hurst implementation: compute Hurst($close,30) then apply 0.4-0.6 mask; shrink volume-volatility lookback to 5/15 days and cap ratio at ±2σ; replace 5-day price-volume correlation with 3-day signed turnover elasticity; use overnight return (close-to-open) instead of intraday; neutralize sector/size and smooth with 3-day EWMA; test long-short deciles with 1-day holding to verify reversal.

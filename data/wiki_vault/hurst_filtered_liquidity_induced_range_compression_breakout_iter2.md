---
title: "Hurst-Filtered Liquidity-Induced Range Compression Breakout"
slug: "hurst_filtered_liquidity_induced_range_compression_breakout_iter2"
type: "factor_card"
status: "failed"
summary: "Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Ts_Rank($close,3)-0.5) * (1-Corr(Rank($close/Ref($close,10)),Rank($volume),7)) * (Ts_Max($high,5)-Ts_Min($lo…"
updated: "2026-04-14T12:08:58"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0006
rank_ic: 0.0
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Ts_Rank($close,3)-0.5) * (1-Corr(Rank($close/Ref($close,10)),Rank($volume),7)) * (Ts_Max($high,5)-Ts_Min($low,5))/Ref($close,5) ) goes long (short) stocks whose 7-day price-volume correlation is low, whose 5-day range relative to lagged close is in the top (bottom) quintile, whose 3-day price rank is rising (falling), but only when the 21-day Hurst exponent signals mild-to-moderate persistence (0.45-0.7), expecting that volume-agnostic range compression in lightly trending markets resolves directionally.

**Rationale**: Macro: Fed’s hawkish pause keeps front-end rates elevated, shrinking dealer inventory appetite and compressing intraday ranges; concurrent tariff headlines raise sector-specific uncertainty, further fragmenting liquidity. Market Analysis: implied vol term-structure remains inverted, indicating a high-vol regime where capital is rationed to the most directional setups. Within this backdrop, volume that fails to confirm price produces coiled ranges; when Hurst shows mild persistence the subsequent breakout is more reliable than classic mean-reversion trades that have failed repeatedly. Cross-sectional ranking neutralizes beta, while the range/price scalar standardizes signal across tick sizes. Thus we capture liquidity-starved compressions poised for volatility expansion rather than fading already-exhausted moves.

**Implementation (Qlib)**: `Rank(If(And(GreaterEqual(Ts_Rank($close,21),0.45),LessEqual(Ts_Rank($close,21),0.7)),1,0)*Sign(Ts_Rank($close,3)-0.5)*(1-Corr(Rank($close/Ref($close,10)),Rank($volume),7))*(Ts_Max($high,5)-Ts_Min($low,5))/Ref($close,5))`

**Math Formula**: R=\operatorname{Rank}\Bigl(\mathbf{1}_{[0.45,0.7]}\!igl(H_{21}(C)\bigr)\cdot\operatorname{Sign}\!igl(r_{3}(C)-0.5\bigr)\cdot\bigl(1-\rho_{7}\bigl(\operatorname{Rank}(C/C_{-10}),\operatorname{Rank}(V)\bigr)\bigr)\cdot\frac{\max_{5}(H)-\min_{5}(L)}{C_{-5}}\Bigr)

**IC / RankIC**: -0.0006 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is ineffective: IC≈0, Rank IC=0, negative Sharpe (-0.34) and deep drawdown (-57%). Hurst filter uses Ts_Rank instead of actual Hurst exponent, collapsing the signal to a binary 0/1; price-volume correlation term is inverted (1-corr) and noisy; 5-day range/close term dominates but lacks normalization; no sector/neutralization or cap adjustment; sign() on 3-day rank introduces unnecessary non-linearity.

**Suggested Improvements**: Replace Ts_Rank($close,21) with true 21-day Hurst(H,21) and keep continuous H in [0.45,0.7] instead of binary flag. Flip price-volume correlation to +Corr(...) so low correlation gets high score. Winsorize all sub-terms at 1-99 % and z-score normalize before multiplying. Add sector-neutral cross-sectional z-score within each country/sector. Replace sign(Ts_Rank($close,3)-0.5) with smoothed z-score of Ts_Rank($close,3). Apply 20-day exponential decay to final composite and verify IC>0.02, Rank IC>0.03 on out-of-sample data.

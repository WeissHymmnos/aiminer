---
title: "Cross-Sector Risk-Reversal on Macro-Surprise Dispersion"
slug: "cross_sector_risk_reversal_on_macro_surprise_dispersion_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank( (Delta(Close,6)/Ts_Mean(IV_Spread,10)) * Sign( MacroSurpriseZ(Day-1) - SectorMedianMacroSurpriseZ ) ) goes long (short) stocks whose 6-day return is larg…"
updated: "2026-04-14T12:26:35"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "0.139"
rank_ic: "-0.006"
iteration: "2"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Cross-Sector Risk-Reversal on Macro-Surprise Dispersion

## Summary

Rank( (Delta(Close,6)/Ts_Mean(IV_Spread,10)) * Sign( MacroSurpriseZ(Day-1) - SectorMedianMacroSurpriseZ ) ) goes long (short) stocks whose 6-day return is larg…

## Hypothesis

Rank( (Delta(Close,6)/Ts_Mean(IV_Spread,10)) * Sign( MacroSurpriseZ(Day-1) - SectorMedianMacroSurpriseZ ) ) goes long (short) stocks whose 6-day return is larg…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Div(Delta($close, 6), Mul(0.1, Sum($volume, 10))))```

**Math Formula**: R_{i,t}=\text{Rank}_t\left(\frac{\text{Close}_{i,t}-\text{Close}_{i,t-6}}{\frac{1}{10}\sum_{k=0}^{9}\text{IV_Spread}_{i,t-k}}\cdot\text{Sign}\left(\text{MacroSurpriseZ}_{b(i),t-1}-\text{SectorMedianMacroSurpriseZ}_{s(i),t-1}\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.1390 / -0.0060
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.

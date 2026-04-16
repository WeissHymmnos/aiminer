---
title: "Hurst Filter Signal Primitive"
slug: "hurst_filter_signal"
type: "signal_primitive"
status: "active"
summary: "Uses Hurst or persistence proxies to gate whether a signal should be interpreted as trend or reversion."
updated: "2026-04-16T13:12:24"
tags: []
related: []
node_type: "signal_primitive"
evidence_level: "baseline"
canonical: "true"
parents: []
depends_on: []
risk_flags: []
metrics_ref: []
---

## Definition

Hurst-based filters classify when local price dynamics are persistent versus mean-reverting.

## Typical Expressions

- (1 - Hurst) reversion gates
- Hurst-scaled return shocks
- Hurst-conditioned liquidity signals

## Backlinks

- [[centralbankhurstmomentum_iter2]] — CentralBankHurstMomentum
- [[cross_sectional_hurst_term_structure_volatility_reversal_iter3]] — Cross-Sectional Hurst-Term Structure Volatility Reversal
- [[hurst_exp_vix_momentum_reversal_iter1]] — Hurst_Exp_VIX_Momentum_Reversal
- [[hurst_filtered_cross_sectional_volume_price_divergence_reversal_iter1]] — Hurst-Filtered Cross-Sectional Volume-Price Divergence Reversal
- [[hurst_filtered_liquidity_contrarian_iter1]] — Hurst-Filtered Liquidity Contrarian
- [[hurst_filtered_liquidity_exhaustion_reversal_iter1]] — Hurst-Filtered Liquidity Exhaustion Reversal
- [[hurst_filtered_liquidity_induced_range_compression_breakout_iter2]] — Hurst-Filtered Liquidity-Induced Range Compression Breakout
- [[hurst_filtered_liquidity_price_compression_breakout_iter3]] — Hurst-Filtered Liquidity-Price Compression Breakout
- [[hurst_filtered_liquidity_volatility_divergence_reversal_iter1]] — Hurst-Filtered Liquidity-Volatility Divergence Reversal
- [[hurst_filtered_short_covering_rally_iter1]] — Hurst-Filtered Short-Covering Rally
- [[hurst_filtered_volume_price_divergence_reversal_iter2]] — Hurst-Filtered Volume-Price Divergence Reversal
- [[hurst_macro_vol_momentum_iter1]] — Hurst_Macro_Vol_Momentum
- [[hurst_oil_momentum_reversal_iter2]] — Hurst_Oil_Momentum_Reversal
- [[hurst_scaled_liquidity_adjusted_intraday_reversal_iter1]] — Hurst-Scaled Liquidity-Adjusted Intraday Reversal
- [[hurst_scaled_liquidity_imbalance_mean_reversion_iter3]] — Hurst-Scaled Liquidity-Imbalance Mean-Reversion
- [[hurst_scaled_liquidity_weighted_cross_sectional_mean_reversion_iter3]] — Hurst-Scaled Liquidity-Weighted Cross-Sectional Mean-Reversion
- [[hurst_scaled_liquidity_weighted_order_imbalance_reversal_iter2]] — Hurst-Scaled Liquidity-Weighted Order-Imbalance Reversal
- [[hurst_slope_volume_divergence_reversal_iter2]] — Hurst-Slope Volume Divergence Reversal
- [[hurst_volatility_adjusted_volume_climax_reversal_iter1]] — Hurst-Volatility-Adjusted Volume Climax Reversal
- [[liquidity_adjusted_hurst_dispersion_reversal_iter2]] — Liquidity-Adjusted Hurst Dispersion Reversal
- [[liquidity_adjusted_hurst_slope_dispersion_reversal_iter2]] — Liquidity-Adjusted Hurst-Slope Dispersion Reversal
- [[liquidity_adjusted_hurst_weighted_idiosyncratic_reversal_iter1]] — Liquidity-Adjusted Hurst-Weighted Idiosyncratic Reversal
- [[liquidity_weighted_hurst_adjusted_cross_sectional_reversal_iter1]] — Liquidity-Weighted Hurst-Adjusted Cross-Sectional Reversal
- [[mean_reversion_gamma_trap_iter1]] — Mean-Reversion Gamma Trap
- [[over_night_gamma_hedge_reversal_in_high_skew_names_iter3]] — Over-night Gamma-hedge Reversal in High-Skew Names
- [[volume_accelerated_cross_sectional_reversal_iter2]] — Volume-Accelerated Cross-Sectional Reversal

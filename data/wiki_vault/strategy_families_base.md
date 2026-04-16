---
title: "Alpha Strategy Families Baseline"
slug: "strategy_families_base"
type: "strategy_family"
status: "baseline"
summary: "Alpha Strategy Families Baseline"
updated: "2026-04-11T20:44:26.781374"
tags: []
related: []
node_type: "strategy_family"
evidence_level: "baseline"
canonical: "true"
parents: []
depends_on: []
risk_flags: []
metrics_ref: []
---

# Alpha Strategy Families Baseline  
*Internal reference – v1.0*

---

## 1. Purpose  
Provide a concise, evergreen definition of the major alpha families used in quantitative portfolios, the standard design patterns that practitioners apply, and the most common failure modes (“cautionary notes”).  
Use this page as the first stop when onboarding a new model, comparing signal mix, or debugging live PnL.

---

## 2. Taxonomy & Core Definitions  

| Family | Working Definition | Typical Horizon | Key Data Sources |
|---|---|---|---|
| **Momentum** | Time-series or cross-sectional persistence of past returns | 1 d – 6 m | Daily returns, intraday snapshots, earnings revisions |
| **Mean-Reversion** | Temporary dislocation followed by convergence | 5 m – 3 m | Intraday order book, ETF vs basket, residual spreads |
| **Value** | Cheap vs fundamental anchor; converges to “fair” multiple | 1 m – 2 y | Sector-normalised P/E, EV/EBITDA, B/P, analyst target |
| **Carry** | Income earned while holding position (positive θ) | 1 w – 6 m | Div yield, repo rate, swap basis, FX forward pts |
| **Quality** | Profitability & balance-sheet strength predict future out-performance | 1 m – 1 y | ROE, debt/EBITDA, accruals, cash-flow volatility |
| **Size** | Small-cap premium after risk-adjustment | 1 m – 1 y | Free-float market cap, log(mcap) z-score |
| **Volatility & Tail** | Selling or buying realised/implied volatility spread | 1 d – 3 m | ATM IV vs RV, vol surface skew, VVIX |
| **Event** | Risk premium around corporate or macro catalysts | 1 d – 3 m | Deal spread, earnings drift, Fed days, CPI |
| **ESG/Sustainability** | Non-financial scores predict returns or risk | 1 m – 1 y | Refinitiv ESG, MSCI controversies, EU taxonomy |
| **Stat-Arb & Cross-Asset** | Residual co-integration or lead-lag across instruments | 5 m – 2 w | PCA residuals, ADF test, Johansen |
| **Machine-Learning Meta** | Non-linear ensemble of micro-features | 1 d – 1 m | Order-flow, satellite, web-scraped, alternative |

---

## 3. Standard Patterns  

### 3.1 Momentum  
- **Time-series (TSMOM)**: `sign(12M ret) * σ_target / σ_realised`  
- **Cross-sectional (XSMOM)**: `z-score(ret_1M) * winsor(σ_1M)`  
- **Volatility scaling**: target 10 % ex-ante σ; clip at 4× median σ.  
- **Earnings revision sub-type**: `(ΔFY1 EPS / price) * (1 – rank(ΔEPS_3M))` to avoid chasing stale revisions.

### 3.2 Mean-Reversion  
- **Intraday**: open-to-close reversal in top liquidity quartile; entry at +3× σ_intraday; exit at prior midpoint.  
- **Pairs/Basket**: residual `ε_t = spread_t – β*spread_t-1`; entry when `|ε| > 2.5 σ_residual`; stop when half-life > 30 trading days.  
- **Volatility adjusted**: rank stocks by 5-day RSI, skip bottom 2 deciles if 20-day σ > 80th percentile (avoid falling knives).

### 3.3 Value  
- **Sector-neutral composite**: `z-score(E/P, B/P, EV/EBITDA, FY1 PEG)` equally weighted; cap sector exposure ±2 %.  
- **Forward-looking**: blend 60 % trailing metric + 40 % consensus 12-m forecast to reduce value trap.  
- **Timing overlay**: reduce weight when PMI < 50 and credit spreads > 75th percentile (value tends to underperform in early recession).

### 3.4 Carry  
- **FX**: long 1-m forward premium (F/S-1), filter where 5-y CDS < 150 bps to remove default carry.  
- **Equity dividend**: `(div_fy1 – div_fy0) / price` hedged with sector ETF to strip price β.  
- **Rates**: receive 5-y swap in 25-y vs 5-y slope > 100 bps; risk-weight by DV01 bucket.

### 3.5 Quality  
- **F-score overlay**: require Piotroski ≥ 6 before entry; rank by `ROE_ttm` and `Debt/EBITDA` inverse.  
- **Earnings stability**: 12-quarter EPS cv < 0.25; combined with accruals ratio < –5 % (conservative).  
- **Defensive tilt**: up-weight when VIX > 25 and term-structure in backwardation.

### 3.6 Size  
- **Log-linear regression**: `ret ~ α + β*log(mcap) + γ*β_mkt + ε`; family return = residual α.  
- **Liquidity filter**: median 30-day ADV ≥ $20 m to avoid short-squeeze.  
- **Futures proxy**: use micro-contracts on Russell 2000 vs S&P 500 to get cheap, scalable exposure.

### 3.7 Volatility & Tail  
- **Straddle writing**: sell 1-m ATM straddle, delta-hedge daily; target when implied > realised by 2× σ_error (vol risk-premium).  
- **Skew buying**: buy 25-d put, sell 25-d call when skew > 90th percentile; hedge vega with VIX futures.  
- **Tail risk**: long 3-m 10-delta put on equity index, roll when delta > 30; size so that loss in 2008 replay ≤ 150 bps of NAV.

### 3.8 Event  
- **Merger arb**: long target, short acquirer (cash deal: long only); entry ≤ 3 days post announcement; required spread ≥ 3× σ_completion.  
- **Earnings drift**: buy if beat > 1 σ and guidance up; hold 60 days; exclude firms with options IV > 80th percentile (reduce PEAD decay).  
- **Macro calendar**: straddle 1-d before non-farm payroll when forecast std-dev > 1.2× 5-y median; exit close after print.

### 3.9 ESG/Sustainability  
- **Best-in-class**: overweight top 30 % ESG score within each GICS sector; score normalised by region.  
- **Carbon-tilt**: `weight ∝ –log(Scope 1+2 / EVIC)` constrained to tracking error ≤ 1 %.  
- **Controversy filter**: zero weight if red-flag (MSCI severity = 0) not resolved in 90 days.

### 3.10 Stat-Arb & Cross-Asset  
- **PCA residual**: first 10 eigenvectors removed; trade mean-reversion in 50 smallest eigenportfolios; half-life cut-off 5 days.  
- **Cross-asset momentum**: commodity ETF vs producer-stock basket; entry when 20-day rolling β-adjusted correlation < 0.3 and recent commodity move > 2 σ.  
- **Lead-lag**: large-cap index vs small-cap index; use Kalman filter β; entry threshold |ε| > 1.8 σ.

### 3.11 Machine-Learning Meta  
- **Feature neutralisation**: residualise all inputs vs sector, size, β prior to model fit to avoid implicit double-counting.  
- **Horizon matching**: label = forward 1-day return for intraday features, 5-day for daily; use rolling CV with purged k-fold.  
- **Ensemble weighting**: Bayesian shrinkage to 1/N with shrinkage intensity = 0.3 to reduce over-fit turnover.

---

## 4. Cautionary Notes  

| Family | Typical Risk | Mitigation / Check |
|---|---|---|
| **Momentum** | Crash after reversal (Mar-20, Aug-15) | Vol-target cap, add short-term reversal overlay, stop if 1-week drawdown > 5 %. |
| **Mean-Reversion** | Fundamental regime shift (left-tail) | Half-life monitor; exit if ADF p-value > 0.20; impose max sector net 5 %. |
| **Value** | Value trap, secular decline | Require positive 3-y median FCF; overlay quality score ≥ 5; trim if forward EPS downgrade > 10 %. |
| **Carry** | Sudden devaluation, margin spike | CDS filter, position size via max-loss 3 × carry yield; use options collar for EM FX. |
| **Quality** | Crowding, factor rotation | Track active-share vs benchmark; reduce if fund-flow > 2 σ of 2-y history. |
| **Size** | Liquidity shock, short-squeeze | Min ADV filter; stagger rebalance across 3 days; cap individual weight 1 %. |
| **Volatility** | Vol spike, gamma squeeze | Vega limit, daily re-hedge; stress-test +10 vol pts; maintain 20 % cash buffer. |
| **Event** | Deal break, regulatory block | Max 5 % NAV in any single spread; legal counsel review if CFIUS/anti-trust risk; use options to cap loss. |
| **ESG** | Green-washing, score rebalancing | Verify third-party score correlation ≥ 0.7 across vendors; rebalance only at month-end to lower turnover. |
| **Stat-Arb** | Residual breakdown, leverage | Out-of-sample ADF every week; gross leverage ≤ 4×; kill switch if 5-day loss > 3 %. |
| **ML Meta** | Over-fit, regime drift | Walk-forward only; feature importance stability > 0.7 across quarters; turnover penalty in objective. |

---

## 5. Portfolio Construction Cheat-Sheet  

1. **Signal stacking hierarchy**  
   1. Risk-model factors (size, β, sector)  
   2. Style alphas (value, quality, momentum)  
   3. Overlay alphas (ESG, event, vol)  
   4. Stat-arb residuals  

2. **Neutralisation order**  
   - Demean cross-sectionally  
   - Regress out sector & country  
   - Regress out size & β  
   - Volatility target at security level  

3. **Diversification weighting**  
   - Risk-parity between families using 1-y realised IC covariance  
   - Shrink to equal weight if effective N < 8 families  
   - Max single family TE ≤ 1.5 %  

---

## 6. Performance Diagnostics  

- **IC decay plot**: family IC by lag day; expect 1/e decay < 5 days for intraday, < 25 days for value.  
- **Turnover vs after-cost IC**: target after-cost IC ≥ 0.3 × gross IC; else down-weight.  
- **Drawdown attribution**: decompose daily α into family contributions; flag if one family > 40 % of 5-day loss.  

---

## 7. Version Control & Extensions  
- Update this page quarterly or when a new family ≥ 5 % risk budget is introduced.  
- Document any local calibration (e.g., China on-shore value filters) in annex and link.

## Backlinks

- [[centralbankhurstmomentum_iter2]] — CentralBankHurstMomentum
- [[cross_sectional_residual_reversal_after_cb_hawkish_shock_iter1]] — Cross-Sectional Residual Reversal After CB Hawkish Shock
- [[high_fattail_reversion_pressure_iter1]] — High-FatTail-Reversion-Pressure
- [[high_frequency_volume_price_divergence_reversal_iter1]] — High-Frequency Volume-Price Divergence Reversal
- [[high_frequency_volume_volatility_reversal_with_liquidity_shock_filter_iter3]] — High-Frequency Volume-Volatility Reversal with Liquidity Shock Filter
- [[hurst_exp_vix_momentum_reversal_iter1]] — Hurst_Exp_VIX_Momentum_Reversal
- [[hurst_filtered_cross_sectional_volume_price_divergence_reversal_iter1]] — Hurst-Filtered Cross-Sectional Volume-Price Divergence Reversal
- [[hurst_filtered_volume_price_divergence_reversal_iter2]] — Hurst-Filtered Volume-Price Divergence Reversal
- [[hurst_macro_vol_momentum_iter1]] — Hurst_Macro_Vol_Momentum
- [[hurst_oil_momentum_reversal_iter2]] — Hurst_Oil_Momentum_Reversal
- [[intraday_volume_weighted_return_dispersion_reversal_iter2]] — Intraday Volume-Weighted Return Dispersion Reversal
- [[intraday_volume_weighted_return_dispersion_reversal_iter3]] — Intraday Volume-Weighted Return Dispersion Reversal
- [[liquidity_adjusted_intraday_momentum_reversal_iter1]] — Liquidity-Adjusted Intraday Momentum Reversal
- [[liquidity_adjusted_overnight_gap_reversal_iter1]] — Liquidity-Adjusted Overnight Gap Reversal
- [[liquidity_adjusted_overnight_reversal_with_sector_dispersion_iter2]] — Liquidity-Adjusted Overnight Reversal with Sector Dispersion
- [[liquidity_adjusted_sector_relative_reversal_iter2]] — Liquidity-Adjusted Sector-Relative Reversal
- [[liquidity_adjusted_sector_relative_reversal_on_fed_driven_volatility_shock_iter2]] — Liquidity-Adjusted Sector-Relative Reversal on Fed-Driven Volatility Shock
- [[liquidity_adjusted_sector_relative_reversal_on_fed_pivot_shock_iter3]] — Liquidity-Adjusted Sector-Relative Reversal on Fed-Pivot Shock
- [[liquidity_adjusted_sector_rotation_on_fed_pivot_sentiment_iter1]] — Liquidity-Adjusted Sector Rotation on Fed-Pivot Sentiment
- [[liquidity_adjusted_sector_rotation_on_fed_pivot_surprise_iter3]] — Liquidity-Adjusted Sector Rotation on Fed-Pivot Surprise
- [[liquidity_adjusted_volume_price_divergence_mean_reversion_iter1]] — Liquidity-Adjusted Volume-Price Divergence Mean-Reversion
- [[liquidity_driven_sector_rotation_reversal_iter1]] — Liquidity-Driven Sector Rotation Reversal
- [[liquiditydiscountreversal_iter1]] — LiquidityDiscountReversal
- [[mean_reversion_gamma_trap_iter1]] — Mean-Reversion Gamma Trap
- [[over_night_gamma_hedge_reversal_in_high_skew_names_iter3]] — Over-night Gamma-hedge Reversal in High-Skew Names
- [[overnight_reversal_gamma_squeeze_iter1]] — Overnight-Reversal Gamma Squeeze
- [[shrinking_volume_reversal_iter1]] — Shrinking-Volume Reversal
- [[volatility_adjusted_cross_sectional_volume_reversal_iter3]] — Volatility-Adjusted Cross-Sectional Volume Reversal
- [[volume_accelerated_cross_sectional_reversal_iter2]] — Volume-Accelerated Cross-Sectional Reversal
- [[volume_accelerated_intraday_reversal_with_liquidity_wick_filter_iter1]] — Volume-Accelerated Intraday Reversal with Liquidity Wick Filter
- [[volume_vwap_divergence_reversal_iter1]] — Volume-VWAP Divergence Reversal
- [[liquidity_triggered_overnight_gap_reversal_iter1]] — Liquidity-Triggered Overnight Gap Reversal
- [[overnight_gap_reversal_with_liquidity_confirmation_iter1]] — Overnight Gap Reversal with Liquidity Confirmation
- [[vwap_anchored_volume_surge_reversal_iter1]] — VWAP-Anchored Volume-Surge Reversal
- [[hurst_filtered_liquidity_exhaustion_reversal_iter1]] — Hurst-Filtered Liquidity Exhaustion Reversal
- [[vwap_deviation_volume_exhaustion_reversal_iter1]] — VWAP-Deviation Volume Exhaustion Reversal
- [[vwap_reversion_under_liquidity_surge_iter1]] — VWAP-Reversion Under Liquidity Surge
- [[vwap_deviation_liquidity_surge_reversal_iter1]] — VWAP-Deviation Liquidity Surge Reversal
- [[vwap_basis_liquidity_exhaustion_reversal_iter1]] — VWAP-Basis Liquidity Exhaustion Reversal
- [[overnight_gap_reversal_with_liquidity_surge_filter_iter1]] — Overnight Gap Reversal with Liquidity Surge Filter
- [[liquidity_contrarian_overnight_gap_mean_reversion_iter1]] — Liquidity-Contrarian Overnight Gap Mean-Reversion
- [[liquidity_filtered_overnight_gap_reversal_iter1]] — Liquidity-Filtered Overnight Gap Reversal
- [[hurst_filtered_liquidity_contrarian_iter1]] — Hurst-Filtered Liquidity Contrarian
- [[liquidity_adjusted_overnight_gap_reversal_with_sector_neutralization_iter1]] — Liquidity-Adjusted Overnight Gap Reversal with Sector-Neutralization
- [[order_flow_imbalance_micro_trend_exhaustion_iter1]] — Order-Flow Imbalance Micro-Trend Exhaustion
- [[hurst_slope_volume_divergence_reversal_iter2]] — Hurst-Slope Volume Divergence Reversal
- [[central_bank_hold_divergent_vwap_mean_reversion_iter2]] — Central-Bank-Hold Divergent VWAP Mean-Reversion
- [[orderflow_imbalance_micro_trend_exhaustion_iter1]] — OrderFlow Imbalance Micro-Trend Exhaustion
- [[supply_chain_vulnerability_overnight_reversal_iter2]] — Supply-Chain-Vulnerability Overnight Reversal
- [[liquidity_adjusted_intraday_fake_out_continuation_iter1]] — Liquidity-Adjusted Intraday Fake-Out Continuation
- [[hidden_markov_order_flow_exhaustion_reversal_iter2]] — Hidden-Markov Order-Flow Exhaustion Reversal
- [[liquidity_squeeze_post_gap_fade_iter2]] — Liquidity-Squeeze Post-Gap Fade
- [[cross_sector_liquidity_rotation_reversal_iter1]] — Cross-Sector Liquidity Rotation Reversal
- [[tail_hedge_net_demand_reversal_iter1]] — Tail-Hedge Net Demand Reversal
- [[volatility_adjusted_overnight_gap_with_liquidity_exhaustion_iter2]] — Volatility-Adjusted Overnight Gap with Liquidity Exhaustion
- [[central_bank_dampened_flow_rebound_iter2]] — Central-Bank-Dampened Flow Rebound
- [[hurst_volatility_adjusted_volume_climax_reversal_iter1]] — Hurst-Volatility-Adjusted Volume Climax Reversal
- [[liquidity_vacuum_gap_reversal_iter1]] — Liquidity Vacuum Gap Reversal
- [[hurst_filtered_liquidity_volatility_divergence_reversal_iter1]] — Hurst-Filtered Liquidity-Volatility Divergence Reversal
- [[cross_sector_defensive_quality_flow_iter1]] — Cross-Sector Defensive Quality Flow
- [[vwap_slipage_liquidity_vacuum_reversion_iter2]] — VWAP-Slipage Liquidity Vacuum Reversion
- [[hurst_filtered_liquidity_induced_range_compression_breakout_iter2]] — Hurst-Filtered Liquidity-Induced Range Compression Breakout
- [[cap_adjusted_liquidity_shock_reversal_on_trade_weighted_dollar_spikes_iter2]] — Cap-Adjusted Liquidity Shock Reversal on Trade-Weighted Dollar Spikes
- [[intraday_liquidity_adjusted_vwap_rebound_iter3]] — Intraday Liquidity-Adjusted VWAP Rebound
- [[hurst_filtered_liquidity_price_compression_breakout_iter3]] — Hurst-Filtered Liquidity-Price Compression Breakout
- [[cap_anchored_liquidity_shock_rebound_on_global_trade_weakness_iter3]] — Cap-Anchored Liquidity Shock Rebound on Global Trade Weakness
- [[intraday_liquidity_weighted_return_dispersion_iter1]] — Intraday Liquidity-Weighted Return Dispersion
- [[flight_to_quality_balance_sheet_momentum_iter1]] — Flight-to-Quality Balance-Sheet Momentum
- [[global_trade_volatility_filtered_cross_sectional_reversal_iter2]] — Global-Trade-Volatility-Filtered Cross-Sectional Reversal
- [[vwap_slippage_liquidity_stress_reversal_iter2]] — VWAP-Slippage Liquidity Stress Reversal
- [[hurst_scaled_liquidity_adjusted_intraday_reversal_iter1]] — Hurst-Scaled Liquidity-Adjusted Intraday Reversal
- [[intraday_volume_weighted_mean_reversion_acceleration_iter3]] — Intraday Volume-Weighted Mean Reversion Acceleration
- [[cross_sectional_liquidity_adjusted_policy_shadow_beta_iter3]] — Cross-Sectional Liquidity-Adjusted Policy-Shadow Beta
- [[hurst_scaled_liquidity_weighted_order_imbalance_reversal_iter2]] — Hurst-Scaled Liquidity-Weighted Order-Imbalance Reversal
- [[hurst_scaled_liquidity_weighted_cross_sectional_mean_reversion_iter3]] — Hurst-Scaled Liquidity-Weighted Cross-Sectional Mean-Reversion
- [[intraday_volume_weighted_return_dispersion_iter1]] — Intraday Volume-Weighted Return Dispersion
- [[liquidity_weighted_hurst_adjusted_cross_sectional_reversal_iter1]] — Liquidity-Weighted Hurst-Adjusted Cross-Sectional Reversal
- [[volume_weighted_intraday_gradient_reversal_iter2]] — Volume-Weighted Intraday Gradient Reversal
- [[liquidity_adjusted_hurst_slope_dispersion_reversal_iter2]] — Liquidity-Adjusted Hurst-Slope Dispersion Reversal
- [[cross_sectional_gamma_squeeze_reversal_with_gamma_adjusted_volume_iter1]] — Cross-Sectional Gamma-Squeeze Reversal with Gamma-Adjusted Volume
- [[vwap_liquidity_gradient_reversal_iter3]] — VWAP Liquidity Gradient Reversal
- [[hurst_scaled_liquidity_imbalance_mean_reversion_iter3]] — Hurst-Scaled Liquidity-Imbalance Mean-Reversion
- [[cross_sector_risk_reversal_on_macro_surprise_dispersion_iter2]] — Cross-Sector Risk-Reversal on Macro-Surprise Dispersion
- [[liquidity_adjusted_hurst_weighted_idiosyncratic_reversal_iter1]] — Liquidity-Adjusted Hurst-Weighted Idiosyncratic Reversal
- [[volatility_adjusted_volume_flow_divergence_iter1]] — Volatility-Adjusted Volume Flow Divergence
- [[liquidity_adjusted_inflation_beta_reversal_with_policy_uncertainty_filter_iter1]] — Liquidity-Adjusted Inflation-Beta Reversal with Policy-Uncertainty Filter
- [[liquidity_adjusted_hurst_dispersion_reversal_iter2]] — Liquidity-Adjusted Hurst Dispersion Reversal
- [[intraday_liquidity_weighted_return_dispersion_iter2]] — Intraday Liquidity-Weighted Return Dispersion
- [[cross_sectional_liquidity_adjusted_inflation_expectation_reversal_with_sector_volatility_filter_iter2]] — Cross-Sectional Liquidity-Adjusted Inflation-Expectation Reversal with Sector-Volatility Filter
- [[intraday_liquidity_weighted_return_dispersion_iter3]] — Intraday Liquidity-Weighted Return Dispersion
- [[cross_sectional_hurst_term_structure_volatility_reversal_iter3]] — Cross-Sectional Hurst-Term Structure Volatility Reversal
- [[cross_sectional_term_structure_slope_reversal_with_liquidity_filter_iter3]] — Cross-Sectional Term-Structure Slope Reversal with Liquidity Filter
- [[centralbankslopemacd_iter1]] — CentralBankSlopeMACD
- [[disinflation_divergence_momentum_iter1]] — Disinflation-Divergence Momentum
- [[hmm_state_filtered_liquidity_surge_momentum_iter1]] — HMM-State-Filtered Liquidity Surge Momentum
- [[hurst_filtered_short_covering_rally_iter1]] — Hurst-Filtered Short-Covering Rally
- [[liquidity_adjusted_overnight_gap_reversal_with_asymmetric_volume_confirmation_iter2]] — Liquidity-Adjusted Overnight Gap Reversal with Asymmetric Volume Confirmation
- [[liquidity_divergent_overnight_gap_reversal_with_sector_neutral_z_score_iter1]] — Liquidity-Divergent Overnight Gap Reversal with Sector-Neutral Z-Score
- [[liquidity_divergent_pairs_spillover_reversal_iter2]] — Liquidity-Divergent Pairs Spillover Reversal
- [[liquidity_shock_reversal_iter1]] — Liquidity Shock Reversal
- [[overnight_reversal_on_trade_war_headlines_iter1]] — Overnight-Reversal-On-Trade-War-Headlines
- [[post_gap_liquidity_vacuum_reversal_iter2]] — Post-Gap Liquidity Vacuum Reversal
- [[liquidity_weighted_inflation_regime_reversal_iter1]] — Liquidity-Weighted Inflation-Regime Reversal
- [[hurst_scaled_liquidity_noise_reversal_continuum_iter1]] — Hurst-Scaled Liquidity-Noise Reversal Continuum
- [[intraday_liquidity_adjusted_order_imbalance_reversal_iter1]] — Intraday Liquidity-Adjusted Order-Imbalance Reversal

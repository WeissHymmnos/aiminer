---
title: "Market Regime & Universe Baseline"
slug: "market_regime_base"
type: "market_profile"
status: "baseline"
summary: "Market Regime & Universe Baseline"
updated: "2026-04-13T03:58:46.451037"
tags: []
related: []
---

# Market Regime & Universe Baseline  
*Internal reference for quantitative research agents*  

---

## 1. Purpose  
Provide a **stable, reproducible starting point** for every modelling pipeline:  
1. Define the **investable universe** (what you can trade).  
2. Classify the **market regime** (what kind of market you are in).  
3. Freeze both decisions **before** any alpha, risk or portfolio construction code runs.  
This prevents look-ahead bias, universe drift and regime cherry-picking.

---

## 2. Definitions  

| Term | Working Definition | Agent Note |
|---|---|---|
| **Universe Baseline** | The smallest superset of assets that can ever enter the portfolio during the back-test or live period, plus the **rules** that map membership to dates. | Must be **date-stamped** and stored as a single parquet table (`universe_master.parquet`). |
| **Market Regime** | A discrete, forward-looking label assigned at time *t* using only information ≤ *t*. Labels partition the state space into behaviourally different periods (e.g. bull, bear, high-vol, low-vol, rising-rates). | Regime vector is **merged 1-to-1** with every primary sample row so that no model can accidentally peek. |
| **Primary Sample** | The intersection of (a) universe baseline membership and (b) a defined regime window. | Any row outside this intersection is **dropped** before feature engineering. |

---

## 3. Standard Patterns  

### 3.1 Universe Construction Workflow  
1. **Raw security master** → filter by:  
   - Listing exchange MIC codes (remove grey market).  
   - Asset type = {Common Stock, ETF, ETN, REIT, Depository Receipt}.  
   - Currency = strategy reporting currency (FX-hedged share classes mapped to base).  
2. **Liquidity screen** (month-end snapshot):  
   - 20-day median dollar-volume ≥ 5th percentile of NYSE universe that month.  
   - 20-day median bid-ask spread ≤ 200 bps.  
3. **Corporate action adjustment**  
   - Use CRSP/Refinitiv adjustment factors; keep only securities with ≥ 95 % price history after adjustment.  
4. **Survivorship bias guard**  
   - Include delisted tickers with death-date ≤ back-test end.  
5. **Final membership table**  
   Columns: `date`, `ticker`, `perm_id`, `include_flag`, `reason_excluded`.  
   Store in `universe_master.parquet`, partitioned by `date`.

### 3.2 Regime Labelling Workflow  
Pick **one** primary regime axis; secondary axes can be added as extra columns.  

| Axis | Rule Set (illustrative) | Look-back | Rebalance Freq | Code Snippet |
|---|---|---|---|---|
| **Trend** | S&P 500 200-DMA vs level | 200 days | EOM | `regime = 'Bull' if close > sma200 else 'Bear'` |
| **Volatility** | 20-day realised vol rank within 2-year rolling window | 500 days | EOM | `regime = 'High' if vol_rank > 0.8 else 'Low'` |
| **Macro** | US 10-yr yield change vs 6 mth ago | 1 day | EOM | `regime = 'Rising' if Δyield > 0 else 'Falling'` |

Store regime vector as `regime_master.parquet` with columns: `date`, `regime_<axis>`.  
Merge on `date` with any dataset using **left join** to propagate NAs (forces explicit handling).

### 3.3 Freeze File  
After universe + regime finalised, create `freeze_vYYYYMMDD.yaml`:  
```yaml
universe_hash: 9f3e77a4   # md5 of universe_master.parquet
regime_hash: 1a2bc8d0    # md5 of regime_master.parquet
start_date: 2000-01-03
end_date: 2023-12-31
primary_axis: Trend
secondary_axes: [Volatility]
note: "ETFs with AUM ≥ 100 M included from 2010-01-01"
```
Commit to Git; every downstream notebook must load this file **first**.

---

## 4. Cautionary Notes  

| Risk | Symptom | Mitigation |
|---|---|---|
| **Look-ahead leakage** | Regime label uses future data (e.g. end-of-month macro release dated *t* but published *t+1*). | Shift publication dates; use **announcement day** not **reference day**. |
| **Universe drift** | Strategy PnL suddenly jumps after addition of new sector (e.g. crypto ETFs in 2021). | Re-run back-test with **constant-universe** sub-sample to quantify impact. |
| **Liquidity ghosting** | Screen uses current market-cap; historically small stocks enter universe after they surge. | Apply **point-in-time** market-cap from securities database. |
| **Regime over-fitting** | 20 different regime axes tried, finally pick the one with best Sharpe. | Pre-register primary axis in experiment tracker; secondary axes must be **orthogonal** (report variance-inflation). |
| **FX asymmetry** | Non-US assets included without converting returns to base currency. | Impose **currency-convention** layer: all prices → base currency using London 4 pm FX fix. |
| **Delist bias** | Delisted names missing → long-only strategies look better. | Use **CRSP delist return** table; if unavailable, apply –30 % default delist return for NASDAQ bankruptcy flag. |

---

## 5. Quick Checklist (pre-modelling)  
- [ ] `universe_master.parquet` exists and covers [start, end] with daily rows.  
- [ ] `regime_master.parquet` exists and has no NA for primary axis.  
- [ ] Both files referenced in `freeze_vYYYYMMDD.yaml` committed to repo.  
- [ ] Notebook header loads freeze file and asserts hash match.  
- [ ] Primary sample count printed (should drop ≤ 5 % vs raw data).  

---

## 6. File Templates  

**universe_master.parquet schema**  
```
date: date32
ticker: string
perm_id: int64
include_flag: bool
reason_excluded: string  # enum: "illiquid", "delisted", "bad_price", "ok"
```

**regime_master.parquet schema**  
```
date: date32
regime_Trend: string   # Bull / Bear
regime_Vol: string     # High / Low
regime_Yield: string   # Rising / Falling
```

---

## 7. Version History  
| Version | Date | Editor | Summary |
|---|---|---|---|
| v1.0 | 2024-06-01 | AI-RG-01 | Initial wiki page. |

---

*End of document*

## Backlinks

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

# Market Data Metadata

Generated on: 2026-03-28 14:00:50

## Overview
This document provides metadata about the financial market data available for factor mining.
- **Total A-Share Equities:** 5493
- **Total Futures Contracts (Active):** 86

## A-Share Daily Bar Data Structure
The standard daily history data for A-shares (forward adjusted `qfq`) contains the following columns:
- `日期`
- `股票代码`
- `开盘`
- `收盘`
- `最高`
- `最低`
- `成交量`
- `成交额`
- `振幅`
- `涨跌幅`
- `涨跌额`
- `换手率`

### Sample Stock Tickers
- 000001: 平安银行
- 000002: 万  科Ａ
- 000004: *ST国华
- 000006: 深振业Ａ
- 000007: 全新好

## How to align with Qlib Format
When writing Qlib factor code, map these AKShare/standard columns as follows:
- `开盘` -> `$open`
- `收盘` -> `$close`
- `最高` -> `$high`
- `最低` -> `$low`
- `成交量` -> `$volume`
- `成交额` / `成交量` -> `$vwap` (approximate)

## Notes on Strategy Design
- All factor values must handle `NaN` gracefully (e.g., using Qlib's robust operations).
- Prices are adjusted for splits and dividends.
- Futures data usually includes Open Interest (`持仓量`) which can be used as a strong predictor.

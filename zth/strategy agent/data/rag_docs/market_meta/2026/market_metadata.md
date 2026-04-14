# Financial Market Metadata (Qlib Format)

## Standard Daily Trading Data
In quantitative trading and alpha factor mining within Qlib, the raw data typically consists of daily bar data for equities (e.g., CSI300, CSI500 universe in China A-shares).

### Base Price and Volume Fields
These fields represent the standard daily metrics for a given stock:
- `$open`: The opening price of the day.
- `$close`: The closing price of the day.
- `$high`: The highest traded price of the day.
- `$low`: The lowest traded price of the day.
- `$volume`: The total trading volume (number of shares traded) during the day.
- `$vwap`: Volume-Weighted Average Price. Represents the average price a stock has traded at throughout the day, based on both volume and price. It is often a better representation of the true trading cost than the closing price.

### Data Adjustment (复权)
In Qlib, data like `$close`, `$open`, etc., are generally adjusted for dividends and splits (Backward/Forward Adjusted) to prevent artificial jumps in price series which would ruin momentum or volatility calculations.

### Factor Expression Syntax
Qlib uses a formulaic expression engine to compute features dynamically from these base fields:
- `Ref(X, d)`: The value of feature `X` `d` days ago.
- `Mean(X, d)`: The `d`-day moving average of `X`.
- `Std(X, d)`: The `d`-day standard deviation of `X`.
- `Slope(X, d)`: The linear regression slope of `X` over the past `d` days.
- `Rsquare(X, d)`: The R-squared value of the linear regression of `X` over `d` days.
- `Resi(X, d)`: The residual of the linear regression.
- `Max(X, d)` / `Min(X, d)`: The maximum / minimum value over the past `d` days.
- `Quantile(X, d, q)`: The `q`-th quantile of `X` over `d` days.
- `Rank(X, d)`: The percentile rank of the current `X` value relative to its past `d` days of history.
- `IdxMax(X, d)` / `IdxMin(X, d)`: The number of days since the maximum / minimum value occurred within the last `d` days.
- `Corr(X, Y, d)`: The rolling correlation between `X` and `Y` over the past `d` days.
- `Cov(X, Y, d)`: The rolling covariance.
- `Abs(X)`: Absolute value.
- `Log(X)`: Natural logarithm.
- `Sign(X)`: Sign of `X` (1, 0, -1).

## Label Definition
In factor mining, the target to predict (label) is usually the future return of the asset.
A typical label in Qlib for daily trading is:
`Ref($close, -2)/Ref($close, -1) - 1`
This represents the return of buying at the close of tomorrow and selling at the close of the day after tomorrow (a 1-day holding period return with a 1-day delay to simulate execution constraints).
Alternatively, using VWAP:
`Ref($vwap, -2)/Ref($vwap, -1) - 1`

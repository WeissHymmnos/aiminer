# Alpha158 & Alpha360 Library

## Alpha360
Alpha360 provides a dataset with original normalized price data over the past 60 days.
It focuses on the raw sequence of prices and volumes, suitable for time-series deep learning models (like GRU, LSTM, ALSTM).
**Fields included**:
- `CLOSE{i}`: `Ref($close, i)/$close` (for i in 59 down to 0)
- `OPEN{i}`: `Ref($open, i)/$close`
- `HIGH{i}`: `Ref($high, i)/$close`
- `LOW{i}`: `Ref($low, i)/$close`
- `VWAP{i}`: `Ref($vwap, i)/$close`
- `VOLUME{i}`: `Ref($volume, i)/($volume+1e-12)`

## Alpha158
Alpha158 computes 158 statistical and technical indicators over varying rolling windows (typically 5, 10, 20, 30, 60 days). These represent traditional quantitative finance factors.

### K-bar Features
- `KMID`: `($close-$open)/$open`
- `KLEN`: `($high-$low)/$open`
- `KMID2`: `($close-$open)/($high-$low+1e-12)`
- `KUP`: `($high-Greater($open, $close))/$open`
- `KLOW`: `(Less($open, $close)-$low)/$open`
- `KSFT`: `(2*$close-$high-$low)/$open`

### Price Features
- Normalised historical prices: `Ref($open, d)/$close`, `Ref($high, d)/$close`, `Ref($low, d)/$close`, etc.
- Volume: `Ref($volume, d)/($volume+1e-12)`

### Rolling Operators (computed for window sizes d in [5, 10, 20, 30, 60])
- `ROC{d}` (Rate of Change): `Ref($close, d)/$close`
- `MA{d}` (Moving Average): `Mean($close, d)/$close`
- `STD{d}` (Standard Deviation): `Std($close, d)/$close`
- `BETA{d}` (Trend Slope): `Slope($close, d)/$close`
- `RSQR{d}` (Trend R-Square): `Rsquare($close, d)`
- `RESI{d}` (Residual of Trend): `Resi($close, d)/$close`
- `MAX{d}`, `MIN{d}`: `Max($high, d)/$close`, `Min($low, d)/$close`
- `QTLU{d}`, `QTLD{d}` (Quantiles): 80% and 20% quantiles of past `d` days close price.
- `RANK{d}`: `Rank($close, d)` (Percentile of current close price in past `d` days)
- `RSV{d}`: `($close-Min($low, d))/(Max($high, d)-Min($low, d)+1e-12)`
- `IMAX{d}`, `IMIN{d}`: `IdxMax($high, d)/d`, `IdxMin($low, d)/d` (Days since highest/lowest price)
- `IMXD{d}`: `(IdxMax($high, d)-IdxMin($low, d))/d`
- `CORR{d}`: `Corr($close, Log($volume+1), d)` (Price-volume correlation)
- `CORD{d}`: `Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), d)`
- `CNTP{d}`, `CNTN{d}`: `Mean($close>Ref($close, 1), d)` (Percentage of up/down days)
- `CNTD{d}`: Diff between up and down days percentage.
- `SUMP{d}`, `SUMN{d}`, `SUMD{d}`: RSI-like indicators using `Sum(Greater(...), d)`.

These factors provide fundamental components for AI factor mining. You can use these Qlib expressions (`Ref`, `Mean`, `Std`, `Slope`, `Corr`, `Rank`, `IdxMax`) to compose new, more complex Alphas.

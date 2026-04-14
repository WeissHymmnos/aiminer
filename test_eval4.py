import polars as pl
import numpy as np
from core.alphaeval.polars_engine import PolarsEngine

dates = pl.date_range(pl.date(2020, 1, 1), pl.date(2020, 1, 30), "1d", eager=True).cast(
    pl.String
)
df = pl.DataFrame(
    {
        "datetime": dates.to_list() * 2,
        "instrument": ["A"] * 30 + ["B"] * 30,
        "close": np.random.rand(60) * 10 + 10,
        "open": np.random.rand(60) * 10 + 10,
        "high": np.random.rand(60) * 10 + 15,
        "low": np.random.rand(60) * 10 + 5,
        "volume": np.random.rand(60) * 1000 + 100,
    }
).sort(["instrument", "datetime"])

engine = PolarsEngine(df)
# Use original Qlib syntax to pass through compiler
expr = "If(Greater(Rank(Std(Delta($close, 1) / Ref($close, 1), 20)), 0.75), 1, 0) * Rank(Corr(($high - If(Greater($open, $close), $open, $close)) / ($high - $low), $volume / Median($volume, 20), 3))"

res_col, res_df = engine.evaluate(expr)
print(res_df.select(res_col).head(50))
print("Non-null count:", res_df.select(res_col).drop_nulls().count()[0, 0])

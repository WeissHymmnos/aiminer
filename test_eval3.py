import polars as pl
from core.alphaeval.polars_engine import PolarsEngine

df = pl.DataFrame(
    {
        "instrument": ["A", "B", "A", "B"],
        "datetime": ["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-02"],
        "close": [1.0, 2.0, 1.5, 2.5],
        "open": [1.0, 2.0, 1.5, 2.5],
        "high": [1.0, 2.0, 1.5, 2.5],
        "low": [1.0, 2.0, 1.5, 2.5],
        "volume": [1.0, 2.0, 1.5, 2.5],
    }
).sort(["instrument", "datetime"])

engine = PolarsEngine(df)
ctx = engine._build_context()

expr = "Mul(If(Greater(Rank(Std(Div(Delta(pl.col('close'), 1), Ref(pl.col('close'), 1)), 2)), 0.75), 1, 0), Rank(Corr(Div(Sub(pl.col('high'), If(Greater(pl.col('open'), pl.col('close')), pl.col('open'), pl.col('close'))), Sub(pl.col('high'), pl.col('low'))), Div(pl.col('volume'), Median(pl.col('volume'), 2)), 2)))"

try:
    res, df_out = engine.evaluate(expr)
    print("Eval succeeded!")
    print(df_out.select(res).head())
except Exception as e:
    print(f"Eval failed: {type(e).__name__} - {e}")

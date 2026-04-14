import polars as pl
from core.alphaeval.polars_engine import PolarsEngine

df = pl.DataFrame(
    {
        "instrument": ["A"],
        "datetime": ["2020"],
        "close": [1.0],
        "open": [1.0],
        "high": [1.0],
        "low": [1.0],
        "volume": [1.0],
    }
)
engine = PolarsEngine(df)

ctx = engine._build_context()
print("Corr in ctx:", "Corr" in ctx)

expr = "Mul(If(Greater(Rank(Std(Div(Delta(pl.col('close'), 1), Ref(pl.col('close'), 1)), 20)), 0.75), 1, 0), Rank(Corr(Div(Sub(pl.col('high'), If(Greater(pl.col('open'), pl.col('close')), pl.col('open'), pl.col('close'))), Sub(pl.col('high'), pl.col('low'))), Div(pl.col('volume'), Median(pl.col('volume'), 20)), 3)))"

try:
    eval(expr, ctx)
    print("Eval succeeded!")
except Exception as e:
    print("Eval failed:", type(e).__name__, e)

import polars as pl
import pandas as pd
import numpy as np
from core.alphaeval.polars_engine import PolarsEngine


def test_complex_formula():
    # 创建模拟数据
    dates = pd.date_range("2020-01-01", periods=30)
    instruments = ["A", "B", "C"]
    index = pd.MultiIndex.from_product(
        [dates, instruments], names=["datetime", "instrument"]
    )
    df = pd.DataFrame(
        np.random.rand(len(index), 2), index=index, columns=["close", "volume"]
    )

    pl_df = pl.from_pandas(df.reset_index())
    pl_df = pl_df.with_columns(pl.col("datetime").dt.to_string("%Y-%m-%d"))
    pl_df = pl_df.sort(["instrument", "datetime"])

    engine = PolarsEngine(pl_df)

    # 刚才报错的复杂表达式
    formula = "If(Greater(1 - $close/Ref($close, 3), 0), 1 - $close/Ref($close, 3), 0) * (Mean(Ref($volume, 1), 20) / $volume) * CSRank(Std(Ref(Log($close / Ref($close, 1)), 1), 20))"

    try:
        final_col_ref, updated_df = engine.evaluate(formula)
        res = updated_df.with_columns(factor=final_col_ref)
        print("Success! Result head:")
        print(res.tail(5))
    except Exception as e:
        print(f"Failed again: {e}")
        raise e


if __name__ == "__main__":
    test_complex_formula()

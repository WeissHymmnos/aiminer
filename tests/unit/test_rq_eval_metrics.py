import pandas as pd

from core.alphaeval.rq_eval import RiceQuantEval


def test_daily_rank_ic_uses_cross_sectional_spearman_rank():
    index = pd.MultiIndex.from_product(
        [pd.to_datetime(["2024-01-01", "2024-01-02"]), ["a", "b", "c"]],
        names=["datetime", "instrument"],
    )
    all_data = pd.DataFrame(
        {
            "factor": [1.0, 2.0, 3.0, 1.0, 2.0, 3.0],
            "label": [10.0, 20.0, 30.0, 30.0, 20.0, 10.0],
        },
        index=index,
    )

    rank_ic = RiceQuantEval._daily_rank_ic(all_data)

    assert rank_ic.loc[pd.Timestamp("2024-01-01")] == 1.0
    assert rank_ic.loc[pd.Timestamp("2024-01-02")] == -1.0


def test_pandas_factor_engine_broadcasts_scalar_math_operands():
    dates = pd.date_range("2020-01-01", periods=25)
    instruments = ["a", "b", "c"]
    index = pd.MultiIndex.from_product(
        [dates, instruments], names=["datetime", "instrument"]
    )
    rows = len(index)
    raw_data = pd.DataFrame(
        {
            "close": [10.0 + (i % 25) + (i % 3) for i in range(rows)],
            "volume": [100.0 + (i % 25) * 3 + (i % 3) for i in range(rows)],
        },
        index=index,
    )
    expr = (
        "Mul(Sub(Mul(2, Rank(Div(Cov(Delta(Log($close),1), "
        "Delta(Log($volume),1), 20), Pow(Std(Delta(Log($close),1), 20), 2)))), 1), "
        "Sign(Sub(Mul(Std(Delta(Log($close),1), 20), Sqrt(Div(20,19))), "
        "Ref(Mul(Std(Delta(Log($close),1), 20), Sqrt(Div(20,19))), 5))))"
    )
    evaluator = RiceQuantEval.__new__(RiceQuantEval)
    evaluator.engine = "pandas"
    evaluator.raw_data = raw_data
    evaluator.factor_expressions = [expr]
    evaluator.weights = [1.0]
    evaluator.daily_normalize = True

    evaluator.compute_factors()

    assert expr in evaluator.factor_data.columns
    assert len(evaluator.factor_data) == rows

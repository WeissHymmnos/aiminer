"""Cross-engine consistency unit tests: verify numerical agreement between Pandas
Matrix Engine and Polars Engine across representative factor expressions.
"""

import numpy as np
import pandas as pd
import pytest

from aiminer.core.alphaeval.rq_eval import RiceQuantEval

pl = pytest.importorskip("polars")


@pytest.fixture
def mock_ohlcv_data():
    np.random.seed(42)
    dates = pd.date_range("2021-01-01", periods=30)
    instruments = ["000001.XSHE", "000002.XSHE", "600000.XSHG", "600519.XSHG"]
    idx = pd.MultiIndex.from_product(
        [dates, instruments], names=["datetime", "instrument"]
    )
    n = len(idx)

    close = np.random.uniform(10, 100, size=n)
    open_p = close + np.random.uniform(-1, 1, size=n)
    high = np.maximum(close, open_p) + np.random.uniform(0, 2, size=n)
    low = np.minimum(close, open_p) - np.random.uniform(0, 2, size=n)
    volume = np.random.uniform(1000, 50000, size=n)
    turnover = volume * close

    df = pd.DataFrame(
        {
            "close": close,
            "open": open_p,
            "high": high,
            "low": low,
            "volume": volume,
            "total_turnover": turnover,
        },
        index=idx,
    ).sort_index()

    return df


TEST_EXPRESSIONS = [
    # Basic math
    "Add($close, $open)",
    "Sub($high, $low)",
    "Mul($close, 2)",
    "Div($close, $open)",
    "Abs(Sub($close, $open))",
    "Log($close)",
    "Sign(Sub($close, $open))",
    "Sqrt(Abs($close))",
    "Exp(Div(Sub($close, $open), $close))",
    "Inv($close)",
    "Max($open, $close)",
    "Min($open, $close)",
    # Time-series operators
    "Mean($close, 5)",
    "Std($close, 5)",
    "Sum($volume, 5)",
    "Delta($close, 3)",
    "Ref($close, 2)",
    "Ts_Max($high, 5)",
    "Ts_Min($low, 5)",
    "Corr($close, $volume, 10)",
    "Cov($close, $volume, 10)",
    "Ts_Rank($close, 5)",
    # Cross-sectional operators
    "Rank($close)",
    "CSRank($close)",
    "CSZScore($close)",
    # Logical
    "If(Greater($close, $open), 1.0, 0.0)",
    "If(Less($close, $open), -1.0, 1.0)",
]


@pytest.mark.parametrize("expr", TEST_EXPRESSIONS)
def test_cross_engine_consistency(mock_ohlcv_data, expr):
    # 1. Evaluate with Pandas engine
    ev_pandas = RiceQuantEval(
        factor_expressions=[expr],
        engine="pandas",
        skip_auth=True,
        daily_normalize=False,
    )
    ev_pandas.raw_data = mock_ohlcv_data.copy()
    ev_pandas.compute_factors()
    pandas_factor = ev_pandas.alphacombo.iloc[:, 0].dropna()

    # 2. Evaluate with Polars engine
    ev_polars = RiceQuantEval(
        factor_expressions=[expr],
        engine="polars",
        skip_auth=True,
        daily_normalize=False,
    )
    ev_polars.raw_data = mock_ohlcv_data.copy()
    ev_polars.compute_factors()
    polars_factor = ev_polars.alphacombo.iloc[:, 0].dropna()

    # Align on common non-NaN index
    common_idx = pandas_factor.index.intersection(polars_factor.index)
    assert len(common_idx) > 0, f"No common valid points for expression: {expr}"

    p_vals = pandas_factor.loc[common_idx].to_numpy()
    pol_vals = polars_factor.loc[common_idx].to_numpy()

    # Check numerical close
    np.testing.assert_allclose(
        p_vals,
        pol_vals,
        rtol=1e-4,
        atol=1e-4,
        err_msg=f"Engine discrepancy detected for expression: {expr}",
    )


def test_dry_run_syntax_and_operators():
    """Verify that dry_run executes all operators without errors and adheres to constraints."""
    for expr in TEST_EXPRESSIONS:
        ok, msg = RiceQuantEval.dry_run(expr)
        assert ok, f"dry_run failed for expression '{expr}': {msg}"

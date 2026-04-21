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

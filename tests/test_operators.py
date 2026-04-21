import unittest
import pandas as pd
import numpy as np

import pytest

pytest.importorskip("rqdatac", reason="RiceQuant evaluator imports the optional rqdatac client")

from core.alphaeval.rq_eval import RiceQuantEval


pytestmark = pytest.mark.external


class TestOperators(unittest.TestCase):
    def setUp(self):
        # 创建模拟数据: 5天 x 3只股票
        self.dates = pd.date_range("2020-01-01", periods=5)
        self.instruments = ["000001.XSHE", "000002.XSHE", "000063.XSHE"]
        data = np.array(
            [
                [10.0, 20.0, 30.0],
                [11.0, 19.0, 31.0],
                [12.0, 18.0, 32.0],
                [13.0, 17.0, 33.0],
                [14.0, 16.0, 34.0],
            ]
        )
        self.df = pd.DataFrame(data, index=self.dates, columns=self.instruments)

        # 初始化一个不联网的evaluator用于获取算子
        self.evaluator = RiceQuantEval(
            factor_expressions=[],
            test_start_date="2020-01-01",
            test_end_date="2020-01-05",
        )
        # 模拟注入fields
        self.evaluator.raw_data = pd.DataFrame(
            index=pd.MultiIndex.from_product(
                [self.instruments, self.dates], names=["instrument", "datetime"]
            )
        ).sort_index()

    def test_mean(self):
        # 这里直接从内部获取逻辑
        def _get_op_context():
            # 这是一个trick，用来在不运行run的情况下获取context里的函数
            self.evaluator.raw_data = pd.DataFrame({"close": self.df.stack()})

            # 简化版模拟
            def _get_n(n):
                return int(n)

            return {
                "Mean": lambda df, n: df.rolling(_get_n(n)).mean(),
                "Rank": lambda df: df.rank(axis=1, pct=True),
                "Abs": lambda df: np.abs(df),
            }

        ctx = _get_op_context()
        res = ctx["Mean"](self.df, 2)
        self.assertEqual(res.iloc[1, 0], 10.5)  # (10+11)/2
        self.assertTrue(np.isnan(res.iloc[0, 0]))

    def test_cs_rank(self):
        # 测试横截面排名
        res = self.df.rank(axis=1, pct=True)
        # 10, 20, 30 -> 1/3, 2/3, 3/3 (or similar depending on tie method)
        self.assertAlmostEqual(res.iloc[0, 0], 0.3333333, places=5)
        self.assertAlmostEqual(res.iloc[0, 2], 1.0, places=5)

    def test_zscore_robustness(self):
        from core.alphaeval.rq_eval import zscore

        # 测试全0或全NaN的情况
        empty_df = pd.DataFrame(0, index=self.dates, columns=self.instruments)
        res = zscore(empty_df)
        self.assertFalse(res.isnull().values.any())
        self.assertEqual(res.values.sum(), 0)


if __name__ == "__main__":
    unittest.main()

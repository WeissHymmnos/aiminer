import unittest
from workflow.state import AlphaMinerState
from workflow.graph import route_after_eval

class TestEarlyStopping(unittest.TestCase):
    def test_high_ic_early_stop(self):
        # 测试绝对阈值早停 (IC >= 0.05)
        state: AlphaMinerState = {
            "iteration": 1,
            "max_iterations": 10,
            "backtest_metrics": {"information_coefficient": 0.06},
            "patience_counter": 0
        }
        next_node = route_after_eval(state)
        self.assertEqual(next_node, "end", "Should stop early if IC is exceptionally high.")

    def test_patience_exhausted_early_stop(self):
        # 测试耐心耗尽早停 (patience >= 3)
        state: AlphaMinerState = {
            "iteration": 5,
            "max_iterations": 10,
            "backtest_metrics": {"information_coefficient": 0.01},
            "patience_counter": 3
        }
        next_node = route_after_eval(state)
        self.assertEqual(next_node, "end", "Should stop early if patience is exhausted.")

    def test_normal_increment(self):
        # 正常情况下应该进入下一轮迭代
        state: AlphaMinerState = {
            "iteration": 2,
            "max_iterations": 5,
            "backtest_metrics": {"information_coefficient": 0.02},
            "patience_counter": 1
        }
        next_node = route_after_eval(state)
        self.assertEqual(next_node, "increment", "Should increment to next iteration normally.")

    def test_max_iterations_reached(self):
        # 达到最大迭代次数应结束
        state: AlphaMinerState = {
            "iteration": 5,
            "max_iterations": 5,
            "backtest_metrics": {"information_coefficient": 0.01},
            "patience_counter": 1
        }
        next_node = route_after_eval(state)
        self.assertEqual(next_node, "end", "Should end when max iterations are reached.")

if __name__ == "__main__":
    unittest.main()

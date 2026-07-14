import unittest
from aiminer.agents.factor_agent import FactorAgent


class TestAgentValidation(unittest.TestCase):
    def setUp(self):
        self.agent = FactorAgent()

    def test_valid_expressions(self):
        cases = [
            "$close / Ref($close, 1) - 1",
            "Mean($close, 10)",
            "CSRank(Corr($close, $volume, 5))",
            "Ts_Percentile($close, 20, 50)",
            "If(Greater($close, $open), 1.0, -1.0)",
        ]
        for expr in cases:
            is_valid, msg = self.agent._validate_qlib_expression(expr)
            self.assertTrue(is_valid, f"Expression '{expr}' should be valid: {msg}")

    def test_invalid_expressions(self):
        cases = [
            "Mean($close)",  # 缺少参数n
            "InvalidOp($close, 10)",  # 白名单外算子
            "$close + $unknown_field",  # 白名单外字段
            "CSRank($close",  # 括号不匹配
            "Cannot be expressed: I'm just an LLM...",  # LLM拒绝响应的情况
            "np.mean($close)",  # LLM试图直接写Python
        ]
        for expr in cases:
            is_valid, msg = self.agent._validate_qlib_expression(expr)
            self.assertFalse(is_valid, f"Expression '{expr}' should be INVALID: {msg}")


if __name__ == "__main__":
    unittest.main()

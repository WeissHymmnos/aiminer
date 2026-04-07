import unittest
from core.alphaeval.rq_eval import RiceQuantEval

class TestDryRun(unittest.TestCase):
    def test_dry_run_success(self):
        # 合法的表达式应该返回 True
        exprs = [
            "Mean($close, 5) / $volume",
            "Rank(Std($close, 20))",
            "If(Greater($high, $low), 1, 0)",
            "CSRank(Ts_Percentile($close, 10, 50))"
        ]
        for expr in exprs:
            success, msg = RiceQuantEval.dry_run(expr)
            self.assertTrue(success, f"Expression {expr} should pass dry run, but got: {msg}")

    def test_dry_run_failures(self):
        # 非法的表达式应该在模拟执行时报错
        exprs = [
            ("Mean($close)", "missing 1 required positional argument"), # 缺少参数
            ("InvalidOp($close)", "name 'InvalidOp' is not defined") # 未定义算子
        ]
        for expr, expected_err_keyword in exprs:
            success, msg = RiceQuantEval.dry_run(expr)
            self.assertFalse(success, f"Expression {expr} should fail dry run.")
            if "InvalidOp" in expr or "Mean" in expr:
                self.assertIn(expected_err_keyword.lower(), msg.lower())

if __name__ == "__main__":
    unittest.main()

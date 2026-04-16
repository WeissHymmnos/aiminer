import unittest

from pdf_repro_agent.local_minute_eval import LocalMinuteEvaluator
from pdf_repro_agent.report_reproducer_agent import ReportReproducerAgent


class TestPdfExpressionValidation(unittest.TestCase):
    def test_extract_referenced_fields(self):
        fields = LocalMinuteEvaluator.extract_referenced_fields(
            "Use close momentum with volume confirmation.",
            "Signal compares closing price and VWAP.",
        )
        self.assertEqual(fields, ["$close", "$volume", "$vwap"])

    def test_validate_expression_rejects_unextracted_field(self):
        is_valid, msg = LocalMinuteEvaluator.validate_expression_syntax(
            "Mean($close, 5) + Rank($open)",
            allowed_fields=["$close"],
        )
        self.assertFalse(is_valid)
        self.assertIn("was not extracted", msg)

    def test_validate_expression_accepts_allowed_fields(self):
        is_valid, msg = LocalMinuteEvaluator.validate_expression_syntax(
            "CSRank(Delta($close, 5)) * Sign($volume)",
            allowed_fields=["$close", "$volume"],
        )
        self.assertTrue(is_valid, msg)

    def test_fallback_expression_is_syntactically_valid(self):
        agent = ReportReproducerAgent.__new__(ReportReproducerAgent)
        expression = agent._build_fallback_expression(["$close", "$volume", "$vwap"])
        is_valid, msg = LocalMinuteEvaluator.validate_expression_syntax(
            expression,
            allowed_fields=["$close", "$volume", "$vwap"],
        )
        self.assertTrue(is_valid, msg)


if __name__ == "__main__":
    unittest.main()

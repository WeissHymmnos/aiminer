import unittest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from agents.summary_agent import SummaryAgent
from core.settings import AiminerSettings


class TestSummaryAgent(unittest.TestCase):
    def setUp(self):
        # 初始化并在测试中mock LLM避免实际网络调用
        self.agent = SummaryAgent()

    @patch("agents.summary_agent.ChatPromptTemplate")
    def test_generate_markdown_report(self, mock_prompt):
        # 配置Mock LLM的行为
        # chain = prompt | self.llm
        mock_chain = MagicMock()
        mock_chain.invoke.return_value.content = "Mocked economic analysis."
        mock_prompt.from_messages.return_value.__or__.return_value = mock_chain

        # 准备伪造的测试数据
        dummy_returns = pd.Series(
            [0.01, -0.005, 0.02], index=pd.date_range("2020-01-01", periods=3)
        )
        factor_data = {
            "id": "test_alpha_001",
            "hypothesis": "Test Hypothesis",
            "code": "Rank($close)",
            "metrics": {"information_coefficient": 0.03, "rank_ic": 0.04, "rre": 0.8},
            "returns": dummy_returns,
        }

        # 生成报告
        report_path = self.agent.generate_markdown_report(factor_data)

        # 验证文件是否存在
        self.assertTrue(
            os.path.exists(report_path), "Markdown report file should be created."
        )
        self.assertTrue(
            os.path.exists("results/charts/test_alpha_001_curve.png"),
            "Equity curve chart should be created.",
        )

        # 验证Markdown内容
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Test Hypothesis", content)
        self.assertIn("0.0300", content)
        self.assertIn("Mocked economic analysis", content)

    def tearDown(self):
        # 清理测试生成的文件
        if os.path.exists("results/reports/test_alpha_001.md"):
            os.remove("results/reports/test_alpha_001.md")
        if os.path.exists("results/charts/test_alpha_001_curve.png"):
            os.remove("results/charts/test_alpha_001_curve.png")


def test_summary_agent_uses_settings_paths_and_dict_returns(tmp_path):
    settings = AiminerSettings(results_dir=str(tmp_path / "results"))
    with patch("agents.summary_agent.get_llm", return_value=MagicMock()):
        agent = SummaryAgent(settings=settings)

    mock_chain = MagicMock()
    mock_chain.invoke.return_value.content = "Mocked economic analysis."
    with patch("agents.summary_agent.ChatPromptTemplate") as mock_prompt:
        mock_prompt.from_messages.return_value.__or__.return_value = mock_chain
        report_path = agent.generate_markdown_report(
            {
                "id": "dict_returns_factor",
                "hypothesis": "Dictionary returns should plot.",
                "code": "Rank($close)",
                "metrics": {
                    "information_coefficient": 0.02,
                    "rank_ic": 0.03,
                    "oos_ic": 0.01,
                    "sharpe": 1.0,
                    "max_drawdown": -0.05,
                },
                "returns": {
                    "2024-01-01": 0.01,
                    "2024-01-02": -0.002,
                    "2024-01-03": 0.004,
                },
            }
        )

    expected_report = settings.report_dir / "dict_returns_factor.md"
    expected_chart = settings.chart_dir / "dict_returns_factor_curve.png"
    assert report_path == str(expected_report.resolve())
    assert expected_report.exists()
    assert expected_chart.exists()


if __name__ == "__main__":
    unittest.main()

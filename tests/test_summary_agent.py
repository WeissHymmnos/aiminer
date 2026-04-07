import unittest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from agents.summary_agent import SummaryAgent

class TestSummaryAgent(unittest.TestCase):
    def setUp(self):
        # 初始化并在测试中mock LLM避免实际网络调用
        self.agent = SummaryAgent()

    @patch('agents.summary_agent.ChatPromptTemplate')
    def test_generate_markdown_report(self, mock_prompt):
        # 配置Mock LLM的行为
        # chain = prompt | self.llm
        mock_chain = MagicMock()
        mock_chain.invoke.return_value.content = "Mocked economic analysis."
        mock_prompt.from_messages.return_value.__or__.return_value = mock_chain
        
        # 准备伪造的测试数据
        dummy_returns = pd.Series([0.01, -0.005, 0.02], index=pd.date_range("2020-01-01", periods=3))
        factor_data = {
            "id": "test_alpha_001",
            "hypothesis": "Test Hypothesis",
            "code": "Rank($close)",
            "metrics": {"information_coefficient": 0.03, "rank_ic": 0.04, "rre": 0.8},
            "returns": dummy_returns
        }
        
        # 生成报告
        report_path = self.agent.generate_markdown_report(factor_data)
        
        # 验证文件是否存在
        self.assertTrue(os.path.exists(report_path), "Markdown report file should be created.")
        self.assertTrue(os.path.exists("results/charts/test_alpha_001_curve.png"), "Equity curve chart should be created.")
        
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

if __name__ == "__main__":
    unittest.main()

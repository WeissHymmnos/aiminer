import os
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any
from loguru import logger
from core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate

class SummaryAgent:
    """
    SummaryAgent generates comprehensive factor research reports.
    Includes economic analysis, risk metrics, and equity curve visualization.
    """
    def __init__(self, provider: str = None, model: str = None):
        self.llm = get_llm(temperature=0.3, provider=provider, model_name=model)
        os.makedirs("results/reports", exist_ok=True)
        os.makedirs("results/charts", exist_ok=True)

    def generate_equity_curve(self, returns: pd.Series, factor_id: str) -> str:
        """Plot cumulative returns and save to a file."""
        if returns.empty:
            return ""
        
        plt.figure(figsize=(10, 6))
        cumulative_returns = (1 + returns).cumprod()
        cumulative_returns.plot(title=f"Factor Cumulative Returns - {factor_id}", grid=True)
        plt.xlabel("Date")
        plt.ylabel("Cumulative Returns")
        
        chart_path = f"results/charts/{factor_id}_curve.png"
        plt.savefig(chart_path)
        plt.close()
        return chart_path

    def generate_markdown_report(self, factor_data: Dict[str, Any]) -> str:
        """Write a research report for a single factor."""
        factor_id = factor_data.get("id", "factor_unknown")
        hypothesis = factor_data.get("hypothesis", "N/A")
        code = factor_data.get("code", "N/A")
        metrics = factor_data.get("metrics", {})
        returns = factor_data.get("returns", pd.Series())

        # Generate chart
        chart_path = self.generate_equity_curve(returns, factor_id)

        # Build analysis via LLM
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a senior quantitative research director. Based on the factor hypothesis, code, and metrics, write a concise professional summary in Markdown format. Explain the economic intuition behind the results."),
            ("user", "Hypothesis: {hypothesis}\nCode: {code}\nMetrics: {metrics}\n\nPlease include an 'Economic Rationale Analysis' section.")
        ])
        
        chain = prompt | self.llm
        try:
            analysis = chain.invoke({
                "hypothesis": hypothesis,
                "code": code,
                "metrics": str(metrics)
            }).content
        except Exception as e:
            logger.error(f"Failed to generate LLM summary: {e}")
            analysis = "Economic analysis generation failed."

        report_md = (
            f"# Alpha Factor Research Report: {factor_id}\n\n"
            f"## 1. Specification\n"
            f"- **Hypothesis**: {hypothesis}\n"
            f"- **Implementation**: `{code}`\n\n"
            f"## 2. Performance Metrics\n"
            f"| Metric | Value |\n"
            f"| :--- | :--- |\n"
            f"| Information Coefficient (IC) | {metrics.get('information_coefficient', 0.0):.4f} |\n"
            f"| Rank IC | {metrics.get('rank_ic', 0.0):.4f} |\n"
            f"| Realized Return Efficiency | {metrics.get('rre', 0.0):.4f} |\n\n"
            f"## 3. Equity Curve\n"
            f"![Equity Curve](../../{chart_path})\n\n"
            f"## 4. Professional Analysis\n"
            f"{analysis}\n"
        )

        report_path = f"results/reports/{factor_id}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        
        return report_path

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
        """Plot cumulative returns and save to a file. Returns absolute path or empty string."""
        if returns is None or (hasattr(returns, "empty") and returns.empty):
            logger.warning(
                f"[SummaryAgent] Empty returns for {factor_id}; skipping equity curve."
            )
            return ""

        plt.figure(figsize=(10, 6))
        cumulative_returns = (1 + returns).cumprod()
        cumulative_returns.plot(
            title=f"Factor Cumulative Returns - {factor_id}", grid=True
        )
        plt.xlabel("Date")
        plt.ylabel("Cumulative Returns")

        chart_path = os.path.abspath(f"results/charts/{factor_id}_curve.png")
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
        plot_paths = factor_data.get("plot_paths", {})

        # Build analysis via LLM
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a senior quantitative research director. Based on the factor hypothesis, code, and metrics, write a concise professional summary in Markdown format. Explain the economic intuition behind the results.",
                ),
                (
                    "user",
                    "Hypothesis: {hypothesis}\nCode: {code}\nMetrics: {metrics}\n\nPlease include an 'Economic Rationale Analysis' section.",
                ),
            ]
        )

        chain = prompt | self.llm
        try:
            analysis = chain.invoke(
                {"hypothesis": hypothesis, "code": code, "metrics": str(metrics)}
            ).content
        except Exception as e:
            logger.error(f"Failed to generate LLM summary: {e}")
            analysis = "Economic analysis generation failed."

        # Build chart section with IS/OOS and Layered images
        chart_section = "## 3. Backtest Visualization\n\n"
        if plot_paths.get("equity"):
            chart_section += f"### Cumulative Returns (IS/OOS)\n![Equity Curve]({plot_paths['equity']})\n\n"
        if plot_paths.get("layers"):
            chart_section += f"### Layered Returns (G1-G5)\n![Layered Curves]({plot_paths['layers']})\n\n"
        if not plot_paths:
            chart_section += "_No visualization available._\n\n"

        report_md = (
            f"# Alpha Factor Research Report: {factor_id}\n\n"
            f"## 1. Specification\n"
            f"- **Hypothesis**: {hypothesis}\n"
            f"- **Implementation**: `{code}`\n\n"
            f"## 2. Performance Metrics\n"
            f"| Metric | Value |\n"
            f"| :--- | :--- |\n"
            f"| Information Coefficient (Full IC) | {metrics.get('information_coefficient', 0.0):.4f} |\n"
            f"| Out-of-Sample IC (OOS) | {metrics.get('oos_ic', 0.0):.4f} |\n"
            f"| Rank IC | {metrics.get('rank_ic', 0.0):.4f} |\n"
            f"| Sharpe Ratio | {metrics.get('sharpe', 0.0):.4f} |\n"
            f"| Max Drawdown | {metrics.get('max_drawdown', 0.0):.4f} |\n\n"
            f"{chart_section}"
            f"## 4. Professional Analysis\n"
            f"{analysis}\n"
        )

        report_path = f"results/reports/{factor_id}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        return report_path

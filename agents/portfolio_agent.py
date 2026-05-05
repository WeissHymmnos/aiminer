import json
import re
import pandas as pd
from typing import List, Dict, Any
from loguru import logger
from pydantic import BaseModel, Field
from core.llm import get_llm

class PortfolioDecision(BaseModel):
    method: str = Field(
        ..., 
        description="The chosen portfolio construction method. Must be one of: 'equal', 'inverse_vol', 'risk_parity'."
    )
    rationale: str = Field(
        ..., 
        description="Detailed explanation of why this method was chosen based on the factor metrics and correlation matrix."
    )

class PortfolioAgent:
    """
    PortfolioAgent analyzes the selected top factors, their metrics, and their 
    correlation matrix to dynamically recommend the optimal portfolio weighting scheme.
    """

    def __init__(
        self,
        provider: str = None,
        model: str = None,
        base_url: str = None,
        reasoning_effort: str = None,
    ):
        self._llm_args = {
            "temperature": 0.1,
            "provider": provider,
            "model_name": model,
            "base_url": base_url,
            "reasoning_effort": reasoning_effort,
        }
        self.llm = None
        self._base_llm = None

    def _raw_llm(self):
        if self._base_llm is None:
            self._base_llm = get_llm(**self._llm_args)
        return self._base_llm

    def _decision_llm(self):
        if self.llm is None:
            self.llm = self._raw_llm().with_structured_output(PortfolioDecision)
        return self.llm

    def _supports_structured_output(self) -> bool:
        provider = str(self._llm_args.get("provider") or "").lower()
        model = str(self._llm_args.get("model_name") or "").lower()
        return provider != "deepseek" and "deepseek" not in model

    @staticmethod
    def _strip_markdown_json(text: str) -> str:
        text = text.strip()
        match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text

    @classmethod
    def _parse_decision_response(cls, response: Any) -> PortfolioDecision:
        if isinstance(response, PortfolioDecision):
            return response
        if isinstance(response, dict):
            return PortfolioDecision.model_validate(response)

        content = getattr(response, "content", response)
        if isinstance(content, PortfolioDecision):
            return content
        if isinstance(content, dict):
            return PortfolioDecision.model_validate(content)

        text = cls._strip_markdown_json(str(content))
        try:
            return PortfolioDecision.model_validate_json(text)
        except ValueError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                payload = json.loads(text[start : end + 1], strict=False)
                return PortfolioDecision.model_validate(payload)

        lowered = text.lower()
        for method in ("risk_parity", "inverse_vol", "equal"):
            if method in lowered:
                return PortfolioDecision(method=method, rationale=text[:500] or "Parsed from plain LLM response.")

        raise ValueError("Portfolio decision response did not contain a supported method.")

    @staticmethod
    def _normalize_method(decision: PortfolioDecision) -> PortfolioDecision:
        if decision.method not in ["equal", "inverse_vol", "risk_parity"]:
            logger.warning(
                f"[PortfolioAgent] LLM suggested invalid method '{decision.method}', falling back to risk_parity."
            )
            return PortfolioDecision(
                method="risk_parity",
                rationale=f"Fallback because LLM suggested invalid method: {decision.method}",
            )
        return decision

    def select_method(self, factors: List[Dict[str, Any]], returns_df: pd.DataFrame) -> PortfolioDecision:
        """
        Evaluate factors and their correlation to select a portfolio construction method.
        """
        if not factors or returns_df.empty:
            logger.warning("[PortfolioAgent] Empty factors or returns, defaulting to equal weight.")
            return PortfolioDecision(method="equal", rationale="Fallback due to empty inputs.")
            
        # Calculate correlation matrix
        corr_matrix = returns_df.corr().round(4).to_dict()
        
        # Summarize factor metrics
        factor_summaries = []
        for f in factors:
            fid = f.get("id", "unknown")
            metrics = f.get("metrics", {})
            factor_summaries.append({
                "id": fid,
                "hypothesis": f.get("hypothesis", ""),
                "ic": metrics.get("information_coefficient", 0.0),
                "sharpe": metrics.get("sharpe", 0.0)
            })

        prompt_text = f"""
You are an expert quantitative portfolio manager. Your task is to select the optimal portfolio construction method for a given set of alpha factors.

Available methods:
1. 'equal': Equal weight (1/N). Best when factors have similar risk profiles and low correlation, or when estimation error in covariance is high.
2. 'inverse_vol': Inverse volatility weighting. Best when factors have varying volatilities but correlations are generally low or negligible.
3. 'risk_parity': Risk parity optimization (Equal Risk Contribution). Best when factors have varying volatilities and meaningful non-zero correlations, requiring sophisticated risk balancing.

Here are the selected factors and their key metrics:
{factor_summaries}

        Here is the cross-sectional correlation matrix of their daily returns:
{corr_matrix}

Based on the factor count, their individual performance (IC, Sharpe), and the correlation structure, which method will maximize the out-of-sample risk-adjusted return (e.g., Diversification Ratio and Sharpe)?
Provide your decision and a concise rationale. Return only JSON with keys "method" and "rationale".
"""
        
        try:
            logger.info("[PortfolioAgent] Consulting LLM for portfolio construction method...")
            decision = None
            if self._supports_structured_output():
                try:
                    decision = self._decision_llm().invoke(prompt_text)
                except Exception as structured_err:
                    logger.warning(
                        "[PortfolioAgent] Structured method selection unavailable; "
                        f"retrying with plain JSON response. Details: {structured_err}"
                    )

            if decision is None:
                decision = self._raw_llm().invoke(prompt_text)

            decision = self._normalize_method(self._parse_decision_response(decision))
            logger.info(f"[PortfolioAgent] Selected method: {decision.method} | Rationale: {decision.rationale}")
            return decision
        except Exception as e:
            logger.warning(f"[PortfolioAgent] Failed to select method via LLM, falling back to risk_parity: {e}")
            return PortfolioDecision(method="risk_parity", rationale="Fallback due to LLM error.")

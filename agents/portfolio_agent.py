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

    def __init__(self, provider: str = None, model: str = None, base_url: str = None):
        self.llm = get_llm(
            temperature=0.1,
            provider=provider,
            model_name=model,
            base_url=base_url,
        ).with_structured_output(PortfolioDecision)

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
Provide your decision and a concise rationale.
"""
        
        try:
            logger.info("[PortfolioAgent] Consulting LLM for portfolio construction method...")
            decision = self.llm.invoke(prompt_text)
            
            # Validate method
            if decision.method not in ["equal", "inverse_vol", "risk_parity"]:
                logger.warning(f"[PortfolioAgent] LLM suggested invalid method '{decision.method}', falling back to risk_parity.")
                decision.method = "risk_parity"
                
            logger.info(f"[PortfolioAgent] Selected method: {decision.method} | Rationale: {decision.rationale}")
            return decision
        except Exception as e:
            logger.error(f"[PortfolioAgent] Failed to invoke LLM for method selection: {e}")
            return PortfolioDecision(method="risk_parity", rationale="Fallback due to LLM error.")

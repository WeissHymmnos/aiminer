from unittest.mock import MagicMock
import pandas as pd
import pytest
from agents.portfolio_agent import PortfolioAgent, PortfolioDecision

def test_portfolio_agent_select_method(monkeypatch):
    # Mock LLM to return a predefined decision
    mock_llm = MagicMock()
    mock_decision = PortfolioDecision(method="inverse_vol", rationale="Test rationale")
    mock_llm.invoke.return_value = mock_decision
    
    # Mock get_llm
    def mock_get_llm(*args, **kwargs):
        mock_with_structured = MagicMock()
        mock_with_structured.with_structured_output.return_value = mock_llm
        return mock_with_structured
        
    monkeypatch.setattr("agents.portfolio_agent.get_llm", mock_get_llm)
    
    agent = PortfolioAgent()
    
    factors = [
        {"id": "f1", "hypothesis": "H1", "metrics": {"information_coefficient": 0.05}},
        {"id": "f2", "hypothesis": "H2", "metrics": {"information_coefficient": 0.04}},
    ]
    returns = pd.DataFrame({"f1": [0.01, -0.01], "f2": [-0.01, 0.01]})
    
    decision = agent.select_method(factors, returns)
    
    assert decision.method == "inverse_vol"
    assert decision.rationale == "Test rationale"
    mock_llm.invoke.assert_called_once()
    
def test_portfolio_agent_fallback_empty_factors():
    agent = PortfolioAgent()
    decision = agent.select_method([], pd.DataFrame())
    assert decision.method == "equal"
    assert "Fallback" in decision.rationale

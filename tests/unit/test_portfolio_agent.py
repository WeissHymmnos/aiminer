from unittest.mock import MagicMock
import pandas as pd
import pytest
from aiminer.agents.portfolio_agent import PortfolioAgent, PortfolioDecision

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
        
    monkeypatch.setattr("aiminer.agents.portfolio_agent.get_llm", mock_get_llm)
    
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


def test_portfolio_agent_uses_plain_json_for_deepseek(monkeypatch):
    base_llm = MagicMock()
    base_llm.invoke.return_value.content = '{"method": "equal", "rationale": "Plain JSON rationale"}'

    monkeypatch.setattr("aiminer.agents.portfolio_agent.get_llm", lambda *args, **kwargs: base_llm)

    agent = PortfolioAgent(provider="deepseek", model="deepseek-v4-flash")
    factors = [{"id": "f1", "metrics": {"information_coefficient": 0.05, "sharpe": 1.0}}]
    returns = pd.DataFrame({"f1": [0.01, -0.01, 0.02]})

    decision = agent.select_method(factors, returns)

    assert decision.method == "equal"
    assert decision.rationale == "Plain JSON rationale"
    base_llm.with_structured_output.assert_not_called()
    base_llm.invoke.assert_called_once()


def test_portfolio_agent_retries_plain_json_when_structured_fails(monkeypatch):
    base_llm = MagicMock()
    structured_llm = MagicMock()
    structured_llm.invoke.side_effect = ValueError("response_format unavailable")
    base_llm.with_structured_output.return_value = structured_llm
    base_llm.invoke.return_value.content = '{"method": "risk_parity", "rationale": "Retry rationale"}'

    monkeypatch.setattr("aiminer.agents.portfolio_agent.get_llm", lambda *args, **kwargs: base_llm)

    agent = PortfolioAgent(provider="openai", model="model-without-structured-output")
    factors = [{"id": "f1", "metrics": {"information_coefficient": 0.05, "sharpe": 1.0}}]
    returns = pd.DataFrame({"f1": [0.01, -0.01, 0.02]})

    decision = agent.select_method(factors, returns)

    assert decision.method == "risk_parity"
    assert decision.rationale == "Retry rationale"
    structured_llm.invoke.assert_called_once()
    base_llm.invoke.assert_called_once()

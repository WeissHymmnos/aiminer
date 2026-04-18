import pytest
import numpy as np
import pandas as pd
from core.portfolio import (
    calculate_equal_weights,
    calculate_inverse_volatility_weights,
    calculate_risk_parity_weights,
    calculate_diversification_ratio,
    construct_portfolio
)

@pytest.fixture
def sample_returns():
    # Create a simple returns DataFrame with 3 assets and 100 days
    np.random.seed(42)
    # Asset 1: Low vol, Asset 2: Med vol, Asset 3: High vol
    returns = np.random.randn(100, 3) * np.array([0.01, 0.02, 0.03])
    df = pd.DataFrame(returns, columns=["A", "B", "C"])
    return df

def test_equal_weights(sample_returns):
    weights = calculate_equal_weights(sample_returns)
    assert len(weights) == 3
    assert np.allclose(weights, [1/3, 1/3, 1/3])
    assert np.isclose(weights.sum(), 1.0)

def test_inverse_vol_weights(sample_returns):
    weights = calculate_inverse_volatility_weights(sample_returns)
    assert len(weights) == 3
    assert np.isclose(weights.sum(), 1.0)
    
    # Asset A has lowest vol, so it should have the highest weight
    assert weights["A"] > weights["B"]
    assert weights["B"] > weights["C"]

def test_risk_parity_weights(sample_returns):
    weights = calculate_risk_parity_weights(sample_returns)
    assert len(weights) == 3
    assert np.isclose(weights.sum(), 1.0)
    
    # Calculate risk contributions
    cov = sample_returns.cov().values
    w = weights.values
    port_var = np.dot(w.T, np.dot(cov, w))
    marginal_risk = np.dot(cov, w)
    risk_contribution = w * marginal_risk / port_var
    
    # All risk contributions should be approximately equal to 1/N
    assert np.allclose(risk_contribution, 1/3, atol=1e-3)

def test_diversification_ratio(sample_returns):
    weights = pd.Series([1/3, 1/3, 1/3], index=["A", "B", "C"])
    cov_matrix = sample_returns.cov()
    dr = calculate_diversification_ratio(weights, cov_matrix)
    
    # Since assets are independent (randomly generated), DR should be > 1
    assert dr >= 1.0

def test_construct_portfolio(sample_returns):
    returns_dict = {col: sample_returns[col] for col in sample_returns.columns}
    
    result = construct_portfolio(returns_dict, method="equal")
    assert "weights" in result
    assert "portfolio_returns" in result
    assert "diversification_ratio" in result
    assert result["method"] == "equal"
    assert len(result["portfolio_returns"]) == 100
    assert np.isclose(sum(result["weights"].values()), 1.0)

    result_iv = construct_portfolio(returns_dict, method="inverse_vol")
    assert result_iv["method"] == "inverse_vol"

    result_rp = construct_portfolio(returns_dict, method="risk_parity")
    assert result_rp["method"] == "risk_parity"

def test_construct_portfolio_error_handling(sample_returns):
    returns_dict = {col: sample_returns[col] for col in sample_returns.columns}
    with pytest.raises(ValueError, match="Unknown portfolio construction method"):
        construct_portfolio(returns_dict, method="unknown_method")

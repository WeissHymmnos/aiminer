import numpy as np
import pandas as pd
import cvxpy as cp
from typing import Dict, Any, List

def calculate_equal_weights(returns_df: pd.DataFrame) -> pd.Series:
    n = returns_df.shape[1]
    weights = np.ones(n) / n
    return pd.Series(weights, index=returns_df.columns)

def calculate_inverse_volatility_weights(returns_df: pd.DataFrame) -> pd.Series:
    vols = returns_df.std()
    inv_vols = 1.0 / vols
    weights = inv_vols / inv_vols.sum()
    return weights

def calculate_risk_parity_weights(returns_df: pd.DataFrame) -> pd.Series:
    n = returns_df.shape[1]
    cov = returns_df.cov().values
    
    x = cp.Variable(n)
    # The risk parity problem can be formulated as:
    # minimize (1/2) * x.T * cov * x - sum(log(x))
    objective = cp.Minimize(0.5 * cp.quad_form(x, cov) - sum(cp.log(x)))
    constraints = [x >= 1e-8]
    
    prob = cp.Problem(objective, constraints)
    prob.solve(solver=cp.SCS)
    
    if x.value is None:
        raise ValueError("Risk Parity optimization failed to converge.")
        
    x_val = x.value
    weights = x_val / np.sum(x_val)
    return pd.Series(weights, index=returns_df.columns)

def calculate_diversification_ratio(weights: pd.Series, cov_matrix: pd.DataFrame) -> float:
    """
    Diversification Ratio = (w^T * vol) / sqrt(w^T * cov * w)
    where vol is the vector of individual asset volatilities.
    """
    w = weights.values
    vols = np.sqrt(np.diag(cov_matrix.values))
    weighted_vol_sum = np.dot(w, vols)
    portfolio_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix.values, w)))
    if portfolio_vol < 1e-8:
        return 1.0
    return float(weighted_vol_sum / portfolio_vol)

def construct_portfolio(returns_dict: Dict[str, pd.Series], method: str = "risk_parity") -> Dict[str, Any]:
    """
    Given a dictionary of strategy returns (keyed by factor/strategy ID),
    construct a portfolio and return its weights and aggregate returns.
    """
    # Align dates
    df = pd.DataFrame(returns_dict)
    # Fill missing with 0 temporarily for cov calculation, or dropna? 
    # Usually better to dropna to ensure valid cov matrix, but if there's mismatch, maybe fillna(0)
    df_clean = df.dropna()
    if df_clean.empty:
        raise ValueError("No overlapping dates found for the provided returns.")
    
    if method == "equal":
        weights = calculate_equal_weights(df_clean)
    elif method == "inverse_vol":
        weights = calculate_inverse_volatility_weights(df_clean)
    elif method == "risk_parity":
        try:
            weights = calculate_risk_parity_weights(df_clean)
        except Exception:
            weights = calculate_inverse_volatility_weights(df_clean)
    else:
        raise ValueError(f"Unknown portfolio construction method: {method}")
        
    # Calculate portfolio returns
    # We can use the full df (fillna(0) for missing parts) to compute the actual timeline
    df_full = df.fillna(0.0)
    portfolio_returns = (df_full * weights).sum(axis=1)
    
    cov_matrix = df_clean.cov()
    div_ratio = calculate_diversification_ratio(weights, cov_matrix)
    
    return {
        "weights": weights.to_dict(),
        "portfolio_returns": portfolio_returns,
        "diversification_ratio": div_ratio,
        "method": method
    }

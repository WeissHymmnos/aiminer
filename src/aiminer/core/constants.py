"""
Core constants for the AI Alpha Miner system.

This module centralizes all magic numbers and configuration defaults used across
the system to ensure consistency and ease of maintenance.
"""

# Sentinel value representing a missing or invalid Information Coefficient (IC)
MISSING_IC_SENTINEL: float = -999.0

# Standard number of trading days in a year for annualized metrics calculation
TRADING_DAYS_PER_YEAR: int = 252

# Threshold for accepting a factor in the workflow graph quality gate (graph.py)
# Note: This is semantically distinct from IC_CULL_THRESHOLD, even though they
# share the same numeric value, as they control different stages of the pipeline.
IC_ACCEPT_THRESHOLD: float = 0.005

# Threshold for culling/filtering factors during orthogonalization in the manager (manager.py)
# Note: This is semantically distinct from IC_ACCEPT_THRESHOLD, even though they
# share the same numeric value, as they control different stages of the pipeline.
IC_CULL_THRESHOLD: float = 0.005

# Threshold above which a factor's IC is considered exceptional, triggering early exit
EXCEPTIONAL_IC_THRESHOLD: float = 0.05

DEFAULT_PATIENCE: int = 4

# Default port for the API server
DEFAULT_API_PORT: int = 8000

# Default host address for the API server
DEFAULT_API_HOST: str = "127.0.0.1"

# Default benchmark index code (CSI 300)
DEFAULT_BENCHMARK_INDEX: str = "000300.XSHG"

# Default market name for Qlib evaluation
DEFAULT_QLIB_MARKET: str = "csi300"

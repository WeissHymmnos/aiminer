from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

class AlphaMinerState(TypedDict, total=False):
    # Core tracking
    iteration: int
    max_iterations: int
    
    # Context
    rag_context: str
    market_regime_summary: str
    macro_news_summary: str
    
    # IdeaAgent
    hypothesis_name: str
    hypothesis_description: str
    rationale: str
    
    # FactorAgent
    math_formula: str
    variables_defined: Dict[str, str]
    code_expression: str
    is_valid_syntax: bool
    
    # EvalAgent
    backtest_metrics: Dict[str, float]
    daily_returns: Dict[str, float]
    review_summary: str
    is_effective: bool
    suggested_improvements: str
    is_simulated: bool  # True when backtest used fallback/simulated metrics
    
    best_ic: float
    patience_counter: int
    
    # Control flow & History
    evaluation_mode: str # "qlib" or "ricequant"
    
    # Market Analysis Parameters
    market_analysis_start_date: Optional[str]
    market_analysis_end_date: Optional[str]
    market_analysis_lookback_days: Optional[int]
    
    error: Optional[str]
    messages: Annotated[List[str], operator.add]

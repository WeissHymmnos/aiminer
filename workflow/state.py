from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

class AlphaMinerState(TypedDict, total=False):
    # Core tracking
    iteration: int
    max_iterations: int
    
    # Context
    rag_context: str
    
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
    review_summary: str
    is_effective: bool
    suggested_improvements: str
    is_simulated: bool  # True when backtest used fallback/simulated metrics
    
    # Control flow & History
    error: Optional[str]
    messages: Annotated[List[str], operator.add]

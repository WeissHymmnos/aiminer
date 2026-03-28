from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

class AlphaMinerState(TypedDict, total=False):
    # Core tracking
    iteration: int
    max_iterations: int
    
    # Context
    rag_context: str
    
    # 1. IdeaAgent Outputs
    hypothesis_name: str
    hypothesis_description: str
    rationale: str
    
    # 2. FactorAgent Outputs
    math_formula: str
    variables_defined: Dict[str, str]
    code_expression: str
    is_valid_syntax: bool
    
    # 3. EvalAgent Outputs
    backtest_metrics: Dict[str, float]
    review_summary: str
    is_effective: bool
    suggested_improvements: str
    
    # Control flow & History
    error: Optional[str]
    messages: Annotated[List[str], operator.add]

from typing import TypedDict, Annotated, List, Dict, Optional
import operator


class AlphaMinerState(TypedDict, total=False):
    run_id: str
    agent_id: str
    llm_provider: Optional[str]
    llm_model: Optional[str]
    llm_base_url: Optional[str]

    # Core tracking
    iteration: int
    max_iterations: int

    # Context
    rag_context: str
    wiki_context: str
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
    factor_metrics: Dict[str, float]
    daily_returns: Dict[str, float]
    review_summary: str
    is_effective: bool
    factor_is_effective: bool
    suggested_improvements: str
    is_simulated: bool  # True when backtest used fallback/simulated metrics

    # Strategy stage
    strategy_candidates: List[Dict[str, object]]
    strategy_results: List[Dict[str, object]]
    best_strategy_config: Dict[str, object]
    best_strategy_metrics: Dict[str, float]
    best_strategy_id: Optional[str]
    best_strategy_result: Dict[str, object]
    strategy_daily_returns: Dict[str, float]
    execution_style: Optional[str]
    strategy_failure_reason: Optional[str]
    selection_score: float

    # Strategy reflexion (critic) stage
    strategy_refinement_round: int
    max_strategy_refinement_rounds: int
    strategy_refinement_history: List[Dict[str, object]]

    best_ic: float
    best_code_expression: Optional[str]
    patience_counter: int

    # Control flow & History
    role_prompt: Optional[str]
    evaluation_mode: str  # "qlib" or "ricequant"
    evaluation_engine: str  # "pandas" or "polars"
    data_backend: str  # "ricequant" | "qlib" | "local"
    market_mode: str  # "single" | "batch" | "mixed"
    market_profile: str
    market_profiles: List[str]
    local_data_path: Optional[str]
    local_data_layout: Optional[str]

    # Market Analysis Parameters
    market_analysis_start_date: Optional[str]
    market_analysis_end_date: Optional[str]
    market_analysis_lookback_days: Optional[int]

    error: Optional[str]
    messages: Annotated[List[str], operator.add]

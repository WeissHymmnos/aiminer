from typing import Dict, Literal
from pydantic import BaseModel, Field


class HypothesisOutput(BaseModel):
    """Structured output for market hypothesis generation."""

    hypothesis_name: str = Field(
        description="A short, catchy name for the factor/strategy hypothesis."
    )
    hypothesis_description: str = Field(
        description="A detailed description of the market hypothesis."
    )
    rationale: str = Field(
        description="The financial logic and rationale behind the hypothesis."
    )


class FormalizationOutput(BaseModel):
    """Structured output for mathematical formalization."""

    math_formula: str = Field(
        description="The formal mathematical formula representing the hypothesis."
    )
    variables_defined: Dict[str, str] = Field(
        description="Dictionary explaining each variable in the formula."
    )


class ImplementationOutput(BaseModel):
    """Structured output for code implementation."""

    code_expression: str = Field(
        description="The implemented code or Qlib Alpha158 expression."
    )
    is_valid_syntax: bool = Field(
        description="Whether the expression is syntactically valid in Qlib."
    )


class ReflexiveReviewOutput(BaseModel):
    """Structured output for the evaluation and review phase."""

    review_summary: str = Field(
        description="Summary analysis of the backtest results and whether the hypothesis holds. Include specific metric values in your analysis."
    )
    is_effective: bool = Field(
        description="True if the factor shows positive efficacy: IC > 0.02 AND Rank IC > 0.02. False otherwise."
    )
    suggested_improvements: str = Field(
        description="Specific, actionable suggestions for the next iteration. Include concrete changes to the formula or approach, not generic advice."
    )


class StrategyProposalOutput(BaseModel):
    """Structured output for strategy proposal generation."""

    template_name: str = Field(description="Name of the selected strategy template.")
    strategy_mode: Literal["cross_sectional", "time_series"] = Field(
        description="Whether the strategy uses cross-sectional selection or time-series timing."
    )
    direction: Literal["long_only", "long_short", "long_flat"] = Field(
        description="The directionality of the strategy."
    )
    selection_rule: Literal["top_n", "bottom_n", "top_bottom_n", "threshold"] = Field(
        description="How signals are converted into positions."
    )
    rebalance_freq: Literal["daily", "weekly", "monthly"] = Field(
        description="How often the portfolio rebalances."
    )
    thresholds: Dict[str, float] = Field(
        default_factory=dict,
        description="Threshold-style parameters such as long/short/exit thresholds.",
    )
    counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Selection counts such as top_n and bottom_n.",
    )
    holding_constraints: Dict[str, float | int] = Field(
        default_factory=dict,
        description="Constraints such as max positions, max weight, and minimum holding days.",
    )
    cost_model: Dict[str, float] = Field(
        default_factory=dict,
        description="Trading cost assumptions in basis points.",
    )
    rationale: str = Field(
        description="Why this strategy structure is appropriate for the proposed factor."
    )

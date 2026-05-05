import math
from typing import Any, Dict
from pydantic import BaseModel, Field, field_validator


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


def _is_numeric_dict_value(value) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, str):
        try:
            return math.isfinite(float(value))
        except ValueError:
            return False
    return False


class StrategyCandidateOutput(BaseModel):
    """Structured output for a single strategy proposal."""

    template_name: str = Field(description="Closest built-in template name or generated strategy family label.")
    strategy_mode: str = Field(description="cross_sectional or time_series")
    direction: str = Field(description="long_only, long_short, or long_flat")
    selection_rule: str | Dict[str, Any] = Field(description="top_n, bottom_n, top_bottom_n, or threshold")
    rebalance_freq: str = Field(description="daily, weekly, or monthly")
    thresholds: Dict[str, float] = Field(default_factory=dict)
    counts: Dict[str, int | float] = Field(default_factory=dict)
    holding_constraints: Dict[str, float | int] = Field(default_factory=dict)
    cost_model: Dict[str, float] = Field(default_factory=dict)
    rationale: str = Field(description="Why this execution style matches the factor.")

    @field_validator(
        "template_name",
        "strategy_mode",
        "direction",
        "selection_rule",
        "rebalance_freq",
        "rationale",
        mode="before",
    )
    @classmethod
    def _coerce_scalar_text(cls, value):
        if value is None:
            return value
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        return value

    @field_validator(
        "thresholds",
        "counts",
        "holding_constraints",
        "cost_model",
        mode="before",
    )
    @classmethod
    def _coerce_optional_dict(cls, value):
        if value is None:
            return {}
        if isinstance(value, dict):
            return {
                key: item
                for key, item in value.items()
                if item is not None
                and not isinstance(item, (dict, list, tuple, set))
                and _is_numeric_dict_value(item)
            }
        return value


class StrategyProposalBatchOutput(BaseModel):
    """Structured output for strategy candidate generation."""

    execution_style: str = Field(description="Short execution summary, e.g. cs_long_short or ts_trend.")
    candidates: list[StrategyCandidateOutput] = Field(default_factory=list)


class RefinementProposalOutput(BaseModel):
    """Structured output for the StrategyCritic reflexion step."""

    failure_modes: list[str] = Field(
        default_factory=list,
        description="Concise tags for the dominant problems observed in the current best strategy "
        "(e.g. 'high_turnover', 'deep_drawdown_2020Q1', 'negative_sharpe_in_bear_2022').",
    )
    proposals: list[StrategyCandidateOutput] = Field(
        default_factory=list,
        description="Up to 2 refined strategy candidates that target the failure modes. "
        "Only the strategy_config-relevant fields should change (do NOT alter the factor expression).",
    )
    should_continue: bool = Field(
        description="False when the critic believes further refinement is unlikely to help.",
    )
    rationale: str = Field(
        description="One-paragraph explanation of why these proposals address the failure modes."
    )

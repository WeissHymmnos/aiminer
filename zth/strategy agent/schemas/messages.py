from typing import Dict
from pydantic import BaseModel, Field

class HypothesisOutput(BaseModel):
    """Structured output for market hypothesis generation."""
    hypothesis_name: str = Field(description="A short, catchy name for the factor/strategy hypothesis.")
    hypothesis_description: str = Field(description="A detailed description of the market hypothesis.")
    rationale: str = Field(description="The financial logic and rationale behind the hypothesis.")

class FormalizationOutput(BaseModel):
    """Structured output for mathematical formalization."""
    math_formula: str = Field(description="The formal mathematical formula representing the hypothesis.")
    variables_defined: Dict[str, str] = Field(description="Dictionary explaining each variable in the formula.")

class ImplementationOutput(BaseModel):
    """Structured output for code implementation."""
    code_expression: str = Field(description="The implemented factor expression for the RiceQuant matrix engine.")
    is_valid_syntax: bool = Field(description="Whether the expression is syntactically valid for the supported factor engine.")

class ReflexiveReviewOutput(BaseModel):
    """Structured output for the evaluation and review phase."""
    review_summary: str = Field(description="Summary analysis of the backtest results and whether the hypothesis holds. Include specific metric values in your analysis.")
    is_effective: bool = Field(description="True if the factor shows positive efficacy: IC > 0.02 AND Rank IC > 0.02. False otherwise.")
    suggested_improvements: str = Field(description="Specific, actionable suggestions for the next iteration. Include concrete changes to the formula or approach, not generic advice.")

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
    code_expression: str = Field(description="The implemented code or Qlib Alpha158 expression.")
    is_valid_syntax: bool = Field(description="Whether the expression is syntactically valid in Qlib.")

class ReflexiveReviewOutput(BaseModel):
    """Structured output for the evaluation and review phase."""
    review_summary: str = Field(description="Summary analysis of the backtest results and whether the hypothesis holds.")
    is_effective: bool = Field(description="True if the factor shows positive efficacy (e.g., IC > 0.02, Sharpe > 0.5).")
    suggested_improvements: str = Field(description="Actionable suggestions for future iterations based on these results.")

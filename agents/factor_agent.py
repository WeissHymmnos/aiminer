from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
import re
from loguru import logger
from workflow.state import AlphaMinerState
from core.llm import get_llm
from schemas.messages import FormalizationOutput, ImplementationOutput

class FactorAgent:
    """
    FactorAgent translates the market hypothesis into executable code.
    It contains Formalization (hypothesis -> math) and Implementation (math -> code).
    """
    # Known Qlib operators and fields for basic syntax validation
    QLIB_OPERATORS = {
        "Ref", "Mean", "Std", "Rank", "Max", "Min", "Sum", "Abs",
        "Log", "Sign", "Power", "Corr", "Cov", "Delta", "Delay",
        "Ts_Rank", "Ts_Min", "Ts_Max", "Ts_ArgMax", "Ts_ArgMin",
        "WMA", "EMA", "If", "Greater", "Less",
    }
    QLIB_FIELDS = {"$close", "$open", "$high", "$low", "$volume", "$vwap", "$turn", "$factor"}

    def __init__(self):
        # We might use a lower temp for math/coding tasks
        self.llm = get_llm(temperature=0.2)
    
    @staticmethod
    def _strip_markdown_json(text: str) -> str:
        """Remove markdown code block wrapper from JSON response."""
        text = text.strip()
        if text.startswith("```json"):
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        elif text.startswith("```"):
            text = re.sub(r'^```\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        return text.strip()

    @staticmethod
    def _validate_qlib_expression(expr: str) -> tuple:
        """Basic syntax validation for Qlib expressions."""
        if not expr or not expr.strip():
            return False, "Expression is empty."
        
        # Check balanced parentheses
        depth = 0
        for ch in expr:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if depth < 0:
                return False, "Unbalanced parentheses: extra closing ')'."
        if depth != 0:
            return False, f"Unbalanced parentheses: {depth} unclosed '('."
        
        # Check that it contains at least one $ field reference
        if '$' not in expr:
            return False, "Expression contains no Qlib field references (e.g., $close)."
        
        return True, "OK"

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        hypothesis_desc = state.get("hypothesis_description", "")
        rationale = state.get("rationale", "")
        
        logger.info("[FactorAgent] Starting formalization and implementation")

        if not hypothesis_desc:
            return {"error": "No hypothesis found in state.", "messages": ["[FactorAgent] Error: Missing hypothesis."]}

        # 1. Formalization Module: Convert text to math language
        try:
            form_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a quantitative researcher expert in mathematics and statistics. "
                           "Convert the given financial hypothesis into a strict mathematical formula. "
                           "Clearly define each variable. "
                           "You MUST respond with valid JSON only, no markdown, no explanations."),
                ("user", "Hypothesis: {hypothesis}\nRationale: {rationale}\n\n"
                         "Return ONLY valid JSON matching this exact schema:\n"
                         '{{"math_formula": "string", "variables_defined": {{"var": "definition"}}}}\n\n'
                         "Do not include markdown code blocks or any other text.")
            ])
            form_chain = form_prompt | self.llm
            raw_form_response = form_chain.invoke({
                "hypothesis": hypothesis_desc,
                "rationale": rationale
            })
            cleaned_form_json = self._strip_markdown_json(raw_form_response.content)
            form_result = FormalizationOutput.model_validate_json(cleaned_form_json)
            
            logger.info(f"[FactorAgent] Formalized Math: {form_result.math_formula}")
            
            # 2. Implementation Module: Convert math to Qlib Alpha158 expressions
            impl_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert Qlib developer. Convert the following mathematical formula into a syntactically correct Qlib Alpha158 expression. "
                           "Qlib expressions use operators like Rank(), Ref(), Mean(), Std(), and fields like $close, $volume, $open, $high, $low, $vwap. "
                           "You MUST respond with valid JSON only, no markdown, no explanations."),
                ("user", "Mathematical Formula: {math_formula}\nVariables: {variables}\n\n"
                         "Return ONLY valid JSON matching this exact schema:\n"
                         '{{"code_expression": "string", "is_valid_syntax": boolean}}\n\n'
                         "Do not include markdown code blocks or any other text.")
            ])
            impl_chain = impl_prompt | self.llm
            raw_impl_response = impl_chain.invoke({
                "math_formula": form_result.math_formula,
                "variables": str(form_result.variables_defined)
            })
            cleaned_impl_json = self._strip_markdown_json(raw_impl_response.content)
            impl_result = ImplementationOutput.model_validate_json(cleaned_impl_json)
            
            logger.info(f"[FactorAgent] Implemented Code: {impl_result.code_expression}")
            
            # Validate the expression independently of LLM's self-assessment
            is_valid, validation_msg = self._validate_qlib_expression(impl_result.code_expression)
            if not is_valid:
                logger.warning(f"[FactorAgent] Syntax validation failed: {validation_msg}")
            
            # Use AND of LLM's assessment and our validation
            final_valid = impl_result.is_valid_syntax and is_valid

            return {
                "math_formula": form_result.math_formula,
                "variables_defined": form_result.variables_defined,
                "code_expression": impl_result.code_expression,
                "is_valid_syntax": final_valid,
                "messages": [
                    f"[FactorAgent] Math: {form_result.math_formula}",
                    f"[FactorAgent] Code: {impl_result.code_expression}",
                    f"[FactorAgent] Valid: {final_valid} (LLM={impl_result.is_valid_syntax}, Check={is_valid}: {validation_msg})"
                ]
            }

        except Exception as e:
            logger.error(f"[FactorAgent] Failed to process factor: {e}")
            return {
                "error": str(e),
                "messages": [f"[FactorAgent] Error: {e}"]
            }

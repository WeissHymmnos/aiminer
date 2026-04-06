from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
import re
from loguru import logger
from workflow.state import AlphaMinerState
from core.llm import get_llm
from schemas.messages import FormalizationOutput, ImplementationOutput

class FactorAgent:
    """
    FactorAgent translates the market hypothesis into executable code (Formalization and Implementation).
    """
    # Verified Whitelist of supported Qlib operators in our Matrix Engine (rq_eval.py)
    QLIB_OPERATORS = {
        "Rank", "CSRank", "CSZScore", "Mean", "Std", "Median", "EMA", "Abs",
        "Ref", "Log", "Sum", "If", "Greater", "Less", "And", "Or", "Delta",
        "Corr", "Correlation", "Cov", "Ts_Rank", "Ts_ArgMax", "Ts_ArgMin",
        "Ts_Percentile", "Winsorize", "GroupNeutral", "Percentile", "Clip",
        "Count", "Sign", "Sqrt"
    }
    # Verified Whitelist of supported data fields
    QLIB_FIELDS = {"$close", "$open", "$high", "$low", "$volume", "$vwap"}

    def __init__(self, provider: str = None, model: str = None):
        self.llm = get_llm(temperature=0.1, provider=provider, model_name=model) # Lower temperature for strictness

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
        # Basic syntax validation for Qlib expressions.
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
        
        # Check $ 
        if '$' not in expr:
            return False, "Expression contains no Qlib field references (e.g., $close)."
        
        return True, "OK"

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        hypothesis_desc = state.get("hypothesis_description", "")
        rationale = state.get("rationale", "")
        
        logger.info("[FactorAgent] Starting formalization and implementation")

        if not hypothesis_desc:
            return {"error": "No hypothesis found in state.", "messages": ["[FactorAgent] Error: Missing hypothesis."]}

        # 1. Convert text to math language (Single pass)
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
            
            # 2. Implementation with Self-Correction Retry Loop
            max_retries = 2
            current_retry = 0
            code_expression = ""
            is_valid_syntax = False
            error_feedback = ""
            
            # Seed the conversation for implementation
            messages = [
                ("system", "You are an expert Qlib developer. Convert the following mathematical formula into a syntactically correct Qlib Alpha158 expression.\n\n"
                           "### STRICT WHITELIST OF SUPPORTED OPERATORS:\n"
                           f"{', '.join(sorted(list(self.QLIB_OPERATORS)))}\n\n"
                           "### ALLOWED DATA FIELDS:\n"
                           f"{', '.join(sorted(list(self.QLIB_FIELDS)))}\n\n"
                           "### MANDATORY RULES:\n"
                           "1. DO NOT use any function, operator, or field not in the whitelists above.\n"
                           "2. If a logic requires an unlisted operator, simplify it using the allowed ones.\n"
                           "3. Use functional style: Op(args) instead of infix (except basic math + - * /).\n"
                           "4. You MUST respond with valid JSON only, no markdown, no explanations."),
                ("user", "Mathematical Formula: {math_formula}\nVariables: {variables}\n\n"
                         "Return ONLY valid JSON matching this exact schema:\n"
                         '{{"code_expression": "string", "is_valid_syntax": boolean}}\n\n'
                         "Do not include markdown code blocks or any other text.")
            ]

            while current_retry <= max_retries:
                if current_retry > 0:
                    logger.warning(f"[FactorAgent] Retry {current_retry}/{max_retries} due to syntax error: {error_feedback}")
                    # Keep history: append the previous wrong answer and the error feedback
                    messages.append(("assistant", f'{{"code_expression": "{code_expression}", "is_valid_syntax": false}}'))
                    messages.append(("user", f"The code you generated has a syntax error: {error_feedback}. Please FIX IT and return only the valid JSON."))

                impl_prompt = ChatPromptTemplate.from_messages(messages)
                impl_chain = impl_prompt | self.llm
                
                raw_impl_response = impl_chain.invoke({
                    "math_formula": form_result.math_formula,
                    "variables": str(form_result.variables_defined)
                })
                
                cleaned_impl_json = self._strip_markdown_json(raw_impl_response.content)
                impl_result = ImplementationOutput.model_validate_json(cleaned_impl_json)
                
                code_expression = impl_result.code_expression
                
                # Independent validation
                is_valid, validation_msg = self._validate_qlib_expression(code_expression)
                
                if is_valid:
                    is_valid_syntax = True
                    logger.info(f"[FactorAgent] Implemented Code (Success): {code_expression}")
                    break
                else:
                    error_feedback = validation_msg
                    current_retry += 1

            if not is_valid_syntax:
                logger.error(f"[FactorAgent] Failed to fix syntax after {max_retries} retries.")

            return {
                "math_formula": form_result.math_formula,
                "variables_defined": form_result.variables_defined,
                "code_expression": code_expression,
                "is_valid_syntax": is_valid_syntax,
                "messages": [
                    f"[FactorAgent] Math: {form_result.math_formula}",
                    f"[FactorAgent] Code: {code_expression}",
                    f"[FactorAgent] Final Valid: {is_valid_syntax}"
                ]
            }

        except Exception as e:
            logger.error(f"[FactorAgent] Failed to process factor: {e}")
            return {
                "error": str(e),
                "messages": [f"[FactorAgent] Error: {e}"]
            }

        except Exception as e:
            logger.error(f"[FactorAgent] Failed to process factor: {e}")
            return {
                "error": str(e),
                "messages": [f"[FactorAgent] Error: {e}"]
            }

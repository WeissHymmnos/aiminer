from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from workflow.state import AlphaMinerState
from core.llm import get_llm
from schemas.messages import FormalizationOutput, ImplementationOutput

class FactorAgent:
    """
    FactorAgent translates the market hypothesis into executable code.
    It contains Formalization (hypothesis -> math) and Implementation (math -> code).
    """
    def __init__(self):
        # We might use a lower temp for math/coding tasks
        self.llm = get_llm(temperature=0.2)
        self.formalization_llm = self.llm.with_structured_output(FormalizationOutput)
        self.implementation_llm = self.llm.with_structured_output(ImplementationOutput)

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
                           "Clearly define each variable."),
                ("user", "Hypothesis: {hypothesis}\\nRationale: {rationale}\\n\\n"
                         "Provide the mathematical formula and define all variables.")
            ])
            form_chain = form_prompt | self.formalization_llm
            form_result: FormalizationOutput = form_chain.invoke({
                "hypothesis": hypothesis_desc,
                "rationale": rationale
            })
            
            logger.info(f"[FactorAgent] Formalized Math: {form_result.math_formula}")
            
            # 2. Implementation Module: Convert math to Qlib Alpha158 expressions
            impl_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert Qlib developer. Convert the following mathematical formula into a syntactically correct Qlib Alpha158 expression. "
                           "Qlib expressions use operators like Rank(), Ref(), Mean(), Std(), and fields like $close, $volume, $open, $high, $low, $vwap. "
                           "Return the code expression and a boolean indicating if you believe the syntax is 100% valid Qlib syntax."),
                ("user", "Mathematical Formula: {math_formula}\\nVariables: {variables}\\n\\n"
                         "Provide the Qlib Alpha158 expression.")
            ])
            impl_chain = impl_prompt | self.implementation_llm
            impl_result: ImplementationOutput = impl_chain.invoke({
                "math_formula": form_result.math_formula,
                "variables": str(form_result.variables_defined)
            })
            
            logger.info(f"[FactorAgent] Implemented Code: {impl_result.code_expression}")

            return {
                "math_formula": form_result.math_formula,
                "variables_defined": form_result.variables_defined,
                "code_expression": impl_result.code_expression,
                "is_valid_syntax": impl_result.is_valid_syntax,
                "messages": [
                    f"[FactorAgent] Math: {form_result.math_formula}",
                    f"[FactorAgent] Code: {impl_result.code_expression}"
                ]
            }

        except Exception as e:
            logger.error(f"[FactorAgent] Failed to process factor: {e}")
            return {
                "error": str(e),
                "messages": [f"[FactorAgent] Error: {e}"]
            }

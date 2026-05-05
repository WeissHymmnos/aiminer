from types import SimpleNamespace

from agents.factor_agent import FactorAgent
from langchain_core.runnables import RunnableLambda


def test_parse_llm_json_repairs_latex_backslashes():
    raw = (
        r'{"math_formula": "\max_{t} x_t + \rho_5", '
        r'"variables_defined": {"\rho_5": "correlation"}}'
    )

    parsed = FactorAgent._parse_llm_json(raw)

    assert parsed["math_formula"] == r"\max_{t} x_t + \rho_5"
    assert parsed["variables_defined"][r"\rho_5"] == "correlation"


def test_parse_llm_json_preserves_escaped_quotes_while_repairing_latex():
    raw = (
        r'{"math_formula": "signal \"quoted\" + \alpha", '
        r'"variables_defined": {"alpha": "weight"}}'
    )

    parsed = FactorAgent._parse_llm_json(raw)

    assert parsed["math_formula"] == r'signal "quoted" + \alpha'


def test_repair_unclosed_parentheses_appends_only_missing_closers():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_unclosed_parentheses(
        "Rank(Mul($close, Ref($close, 1))"
    )

    assert repaired == "Rank(Mul($close, Ref($close, 1)))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_parentheses_removes_trailing_extra_closers():
    agent = FactorAgent.__new__(FactorAgent)
    expression = "Rank($close))"

    repaired = agent._repair_parentheses(expression)

    assert repaired == "Rank($close)"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_trailing_extra_parentheses_does_not_hide_embedded_extra_closer():
    agent = FactorAgent.__new__(FactorAgent)
    expression = "Rank($close)) + Mean($volume, 5)"

    assert agent._repair_trailing_extra_parentheses(expression) == expression
    assert agent._validate_qlib_expression(expression)[0] is False


def test_repair_common_arity_issues_converts_unary_sub_to_neg():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Sub($close))")

    assert repaired == "Rank(Neg($close))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_expands_unary_if_to_indicator():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Sum(If(Greater($close, Ref($close, 1))), 20)")

    assert repaired == "Sum(If(Greater($close, Ref($close, 1)), 1, 0), 20)"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_expands_binary_if_with_zero_else():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Sum(If(Greater($close, Ref($close, 1)), $volume), 20)")

    assert repaired == "Sum(If(Greater($close, Ref($close, 1)), $volume, 0), 20)"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_drops_cross_sectional_zscore_window():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("CSZScore(Rank($close), 3)")

    assert repaired == "CSZScore(Rank($close))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_adds_default_window_to_unary_mean():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Mean($close))")

    assert repaired == "Rank(Mean($close, 20))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_adds_default_lag_to_unary_ref_delta():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Add(Delta($volume), Ref($close)))")

    assert repaired == "Rank(Add(Delta($volume, 1), Ref($close, 1)))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_normalizes_med_and_adds_window():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Med($volume))")

    assert repaired == "Rank(Median($volume, 20))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_adds_default_corr_window():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Corr($close, $volume))")

    assert repaired == "Rank(Corr($close, $volume, 20))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_folds_variadic_arithmetic_ops():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues(
        "Rank(Add(Mul($close, $volume, $open), Div($high, $low, Ref($close, 1))))"
    )

    assert repaired == (
        "Rank(Add(Mul(Mul($close, $volume), $open), "
        "Div(Div($high, $low), Ref($close, 1))))"
    )
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_validate_rejects_unrepaired_variadic_binary_ops():
    agent = FactorAgent.__new__(FactorAgent)
    valid, message = agent._validate_qlib_expression("Div($close, $open, $volume)")

    assert valid is False
    assert "takes exactly 2 positional arguments" in message


def test_validate_rejects_tuple_expression_from_bad_auto_repair():
    agent = FactorAgent.__new__(FactorAgent)
    expression = "(Rank(Mul($close, $volume)), 1)"

    valid, message = agent._validate_qlib_expression(expression)

    assert valid is False
    assert "single factor expression" in message or "one factor series" in message


def test_ricequant_dry_run_accepts_count_with_window():
    from core.alphaeval.rq_eval import RiceQuantEval

    ok, message = RiceQuantEval.dry_run("Count($close, 20)")

    assert ok is True, message


def test_ricequant_dry_run_broadcasts_scalar_log_input():
    from core.alphaeval.rq_eval import RiceQuantEval

    ok, message = RiceQuantEval.dry_run("Log(1)")

    assert ok is True, message


def test_validate_rejects_dynamic_rolling_window():
    agent = FactorAgent.__new__(FactorAgent)
    valid, message = agent._validate_qlib_expression("Mean($close, Sub($volume, 1))")

    assert valid is False
    assert "window must be a positive constant integer" in message


def test_repair_common_arity_issues_replaces_dynamic_rolling_window():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Mean($close, Sub($volume, 1)))")

    assert repaired == "Rank(Mean($close, 20))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_replaces_dynamic_ref_window():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Ref($close, Mean($volume, 20)))")

    assert repaired == "Rank(Ref($close, 1))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_replaces_dynamic_corr_window():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Corr($close, $volume, Mean($volume, 5)))")

    assert repaired == "Rank(Corr($close, $volume, 20))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_repair_common_arity_issues_replaces_dynamic_ts_percentile_args():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Ts_Percentile($close, Mean($volume, 5), $volume))")

    assert repaired == "Rank(Ts_Percentile($close, 20, 50))"
    assert agent._validate_qlib_expression(repaired)[0] is True


def test_validate_rejects_extra_cross_sectional_zscore_arg():
    agent = FactorAgent.__new__(FactorAgent)
    valid, message = agent._validate_qlib_expression("CSZScore(Rank($close), 3)")

    assert valid is False
    assert "takes exactly 1 argument" in message


def test_repair_common_arity_issues_drops_cross_sectional_rank_window_for_ricequant():
    agent = FactorAgent.__new__(FactorAgent)
    repaired = agent._repair_common_arity_issues("Rank(Mean($close, 20), 20)")

    assert repaired == "Rank(Mean($close, 20))"
    assert agent._validate_qlib_expression(repaired, evaluation_mode="ricequant")[0] is True


def test_repair_common_arity_issues_preserves_rank_window_for_qlib():
    agent = FactorAgent.__new__(FactorAgent)
    expression = "Rank(Mean($close, 20), 20)"

    assert agent._repair_common_arity_issues(expression, evaluation_mode="qlib") == expression


def test_call_retries_implementation_json_parse_failure():
    responses = [
        '{"math_formula": "rank close", "variables_defined": {"x": "$close"}}',
        '{"code_expression" "Rank($close)", "is_valid_syntax": true}',
        '{"code_expression": "Rank($close)", "is_valid_syntax": true}',
    ]
    agent = FactorAgent.__new__(FactorAgent)
    agent.llm = RunnableLambda(lambda _prompt: SimpleNamespace(content=responses.pop(0)))

    result = agent(
        {
            "hypothesis_description": "Rank close cross-sectionally.",
            "rationale": "Higher close ranks higher.",
            "evaluation_mode": "ricequant",
        }
    )

    assert result["is_valid_syntax"] is True
    assert result["code_expression"] == "Rank($close)"
    assert responses == []


def test_call_returns_controlled_invalid_factor_after_formalization_json_failures():
    responses = ['{"math_formula" "rank close"}'] * 3
    agent = FactorAgent.__new__(FactorAgent)
    agent.llm = RunnableLambda(lambda _prompt: SimpleNamespace(content=responses.pop(0)))

    result = agent(
        {
            "hypothesis_description": "Rank close cross-sectionally.",
            "rationale": "Higher close ranks higher.",
            "evaluation_mode": "ricequant",
        }
    )

    assert "error" not in result
    assert result["is_valid_syntax"] is False
    assert result["code_expression"] == "Const(0)"
    assert "Formalization JSON parse/validation failed" in result["syntax_error"]

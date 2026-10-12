from __future__ import annotations

import pytest

from aiminer.core.alphaeval.expr_validator import validate_factor_expression
from aiminer.core.alphaeval.factor_mutation import (
    SemanticMutator,
    add_decay,
    cross_sectional_ranking_wrapper,
    macro_condition_gating,
    mutate_ast_parameters,
    non_linear_transformation,
)


def test_add_decay():
    expr = "Mean($close, 5)"
    res = add_decay(expr, window=10, decay_type="WMA")
    assert res == "WMA(Mean($close, 5), 10)"
    validate_factor_expression(res)


def test_cross_sectional_ranking_wrapper():
    expr = "Delta($close, 5)"
    res = cross_sectional_ranking_wrapper(expr, operator="CSRank")
    assert res == "CSRank(Delta($close, 5))"
    validate_factor_expression(res)

    res2 = cross_sectional_ranking_wrapper(expr, operator="Rank")
    assert res2 == "Rank(Delta($close, 5))"
    validate_factor_expression(res2)


def test_non_linear_transformation():
    expr = "Mean($close, 10)"

    log_res = non_linear_transformation(expr, transform="LogAbs")
    assert log_res == "Log(Abs(Mean($close, 10)) + 1)"
    validate_factor_expression(log_res)

    pow_res = non_linear_transformation(expr, transform="Power", power=2)
    assert pow_res == "Sign(Mean($close, 10)) * Pow(Abs(Mean($close, 10)), 2)"
    validate_factor_expression(pow_res)

    scale_res = non_linear_transformation(expr, transform="Scale")
    assert scale_res == "Scale(Mean($close, 10))"
    validate_factor_expression(scale_res)

    with pytest.raises(ValueError, match="Unsupported non-linear transform"):
        non_linear_transformation(expr, transform="unknown_transform")


def test_macro_condition_gating():
    expr = "Delta($close, 5)"

    # Default volume surge gating
    res = macro_condition_gating(expr, regime_name="volume_surge")
    assert "If(Greater($volume, Mean($volume, 20)), Delta($close, 5), 0)" in res
    validate_factor_expression(res)

    # Volatility gating
    res_vol = macro_condition_gating(expr, regime_name="high_volatility")
    assert "Greater(Std($close, 20), Mean(Std($close, 20), 60))" in res_vol
    validate_factor_expression(res_vol)

    # Custom condition
    res_custom = macro_condition_gating(
        expr, condition="Greater($close, $open)", fallback="-1"
    )
    assert res_custom == "If(Greater($close, $open), Delta($close, 5), -1)"
    validate_factor_expression(res_custom)


def test_mutate_ast_parameters():
    expr = "Mean($close, 10) + Delta($open, 20)"
    mutated = mutate_ast_parameters(expr, multiplier=2.0)
    # 10 * 2 = 20, 20 * 2 = 40
    assert "20" in mutated
    assert "40" in mutated
    assert "$close" in mutated
    assert "$open" in mutated
    validate_factor_expression(mutated)


def test_semantic_mutator_deterministic_and_batch():
    mutator = SemanticMutator(seed=42)

    # Single mutation
    expr = "Delta($close, 5)"
    mutated = mutator.mutate(expr)
    assert mutated != expr
    validate_factor_expression(mutated)

    # Batch mutation
    expressions = [
        "Mean($close, 5)",
        "Delta($close, 10)",
        "Std($close, 20)",
    ]
    batch = mutator.batch_mutate(expressions, count=4)
    assert len(batch) >= 1
    for item in batch:
        validate_factor_expression(item)


def test_semantic_mutator_custom_operator():
    mutator = SemanticMutator()
    mutator.register_operator("double", lambda e: f"Add({e}, {e})")

    res = mutator.mutate("Mean($close, 5)", mutation_type="double")
    assert res == "Add(Mean($close, 5), Mean($close, 5))"
    validate_factor_expression(res)

    with pytest.raises(ValueError, match="Unknown mutation operator"):
        mutator.mutate("Mean($close, 5)", mutation_type="nonexistent")

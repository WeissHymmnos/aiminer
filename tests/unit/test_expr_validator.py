"""Tests for the structural allow-list in expr_validator and its wiring."""

import pytest

from aiminer.core.alphaeval.expr_validator import (
    MAX_EXPRESSION_CHARS,
    ExpressionValidationError,
    validate_factor_expression,
)
from aiminer.core.alphaeval.rq_eval import RiceQuantEval

VALID = [
    "Rank(Delta($close, 5))",
    "Mean($close, 5) / Std($close, 20) - 1",
    "-Corr($close, $volume, 10)",
    "If(Greater($close, Ref($close, 1)), 1, -1)",
    "GroupNeutral(Rank($close), sector)",
    "GroupNeutral(Rank($close), 'sector')",
    "Ts_Percentile($close, 20, p=80)",
    "($close > $open) & ($volume < Mean($volume, 5))",
    "~($close == $open)",
    "Pow($close, 2) + $close ** 0.5",
    "Rank(  Delta( $close ,\n 5 ) )",
]

INVALID = [
    ("", "empty"),
    ("   ", "empty"),
    (
        "Mean($close, 5) + 0 * ().__class__.__base__.__subclasses__().__len__()",
        "Attribute",
    ),
    ("$close.rolling(5).mean()", "Attribute"),
    ("np.log($close)", "call on"),
    ("fields['close']", "Subscript"),
    ("(lambda x: x)($close)", "Lambda"),
    ("[x for x in $close]", "ListComp"),
    ("$close if $close > 0 else $open", "IfExp"),
    ("$close > 0 and $open > 0", "BoolOp"),
    ("Mean(*[$close, 5])", "Starred"),
    ("Max([$close, $open])", "List"),
    ("Mean(__builtins__, 5)", "leading underscore"),
    ("Mean($close, **{'n': 5})", "keyword"),
    ("$close(5)", "cannot be called"),
    ("9 ** 9 ** 9", "exponent"),
    ("$close ** (10 ** 10)", "exponent"),
    ("'a' * 1000000000", "string literals"),
    ("Mean($close, 5", "Syntax error"),
    ("Mean($, 5)", "Stray '$'"),
]


@pytest.mark.parametrize("expr", VALID)
def test_valid_expressions_pass(expr):
    validate_factor_expression(expr)


@pytest.mark.parametrize("expr,needle", INVALID)
def test_invalid_expressions_rejected(expr, needle):
    with pytest.raises(ExpressionValidationError) as exc:
        validate_factor_expression(expr)
    assert needle.lower() in str(exc.value).lower()


def test_length_limit():
    expr = "+".join(["$close"] * (MAX_EXPRESSION_CHARS // 6 + 1))
    with pytest.raises(ExpressionValidationError, match="too long"):
        validate_factor_expression(expr)


def test_node_limit():
    # Wide rather than deep: Python's parser caps nesting depth itself.
    expr = "+".join(["Abs($close)"] * 900)
    assert len(expr) < MAX_EXPRESSION_CHARS
    with pytest.raises(ExpressionValidationError, match="too complex"):
        validate_factor_expression(expr)


def test_data_dependent_exponent_allowed():
    validate_factor_expression("2 ** Rank($close) + $close ** -2")


def test_dry_run_rejects_attribute_escape():
    ok, msg = RiceQuantEval.dry_run(
        "Mean($close, 5) + 0 * ().__class__.__base__.__subclasses__().__len__()"
    )
    assert ok is False
    assert "Attribute" in msg


def test_dry_run_still_accepts_normal_factor():
    ok, msg = RiceQuantEval.dry_run("Rank(Delta($close, 5))")
    assert ok, msg


def test_polars_engine_rejects_attribute_escape():
    pl = pytest.importorskip("polars")
    pytest.importorskip("polars_plugins")
    from aiminer.core.alphaeval.polars_engine import PolarsEngine

    engine = PolarsEngine(pl.DataFrame({"close": [1.0, 2.0]}))
    with pytest.raises(ExpressionValidationError):
        engine.evaluate("$close.__class__")

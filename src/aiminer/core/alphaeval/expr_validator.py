"""Structural allow-list validation for Qlib-style factor expressions.

Every factor engine in this package (Pandas matrix engine, Polars engine and
the 10x10 ``dry_run`` mock) evaluates expressions with Python ``eval``. Before
that happens, :func:`validate_factor_expression` checks the *raw* expression
(``$field`` syntax) against a small grammar:

* operator calls ``Op(...)`` where ``Op`` is a bare name,
* bare names (fields, operator names, or symbolic constants such as
  ``sector`` that the engines turn into strings),
* numeric / string / bool constants,
* arithmetic, comparison, bitwise ``& | ~`` and unary ``+ -`` operators,
* keyword arguments (``Ts_Percentile($close, 20, p=80)``).

Anything else -- attribute access, subscripts, lambdas, comprehensions,
conditional expressions, containers, names starting with ``_`` -- is
rejected. This keeps ``dry_run`` consistent with the real engines (the
real engines only understand this grammar anyway) and stops non-factor
Python from slipping through validation.
"""

from __future__ import annotations

import ast
import re

__all__ = [
    "ExpressionValidationError",
    "MAX_EXPRESSION_CHARS",
    "MAX_AST_NODES",
    "validate_factor_expression",
]

MAX_EXPRESSION_CHARS = 12000
MAX_AST_NODES = 5000
_MAX_CONST_POW_EXPONENT = 64

_FIELD_RE = re.compile(r"\$(\w+)")
_FIELD_PREFIX = "FIELD__"

_ALLOWED_BINOPS = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.BitAnd,
    ast.BitOr,
)
_ALLOWED_UNARYOPS = (ast.USub, ast.UAdd, ast.Invert)
_ALLOWED_CMPOPS = (ast.Gt, ast.Lt, ast.GtE, ast.LtE, ast.Eq, ast.NotEq)
_ALLOWED_NODES = (
    ast.Expression,
    ast.Call,
    ast.Name,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.keyword,
    ast.Load,
    *_ALLOWED_BINOPS,
    *_ALLOWED_UNARYOPS,
    *_ALLOWED_CMPOPS,
)


class ExpressionValidationError(ValueError):
    """Raised when a factor expression falls outside the allowed grammar."""


def _describe(node: ast.AST) -> str:
    return type(node).__name__


def validate_factor_expression(expression: str) -> None:
    """Validate a raw Qlib-style factor expression.

    Args:
      expression: Expression using ``$field`` references, e.g.
        ``"Rank(Delta($close, 5))"``.

    Raises:
      ExpressionValidationError: If the expression is empty, too large,
        not parseable, or uses syntax outside the allowed grammar.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ExpressionValidationError("Expression is empty.")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise ExpressionValidationError(
            f"Expression is too long ({len(expression)} chars; "
            f"limit {MAX_EXPRESSION_CHARS})."
        )

    source = _FIELD_RE.sub(lambda m: _FIELD_PREFIX + m.group(1), expression)
    if "$" in source:
        raise ExpressionValidationError(
            "Stray '$' that is not followed by a field name."
        )
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError as exc:
        raise ExpressionValidationError(f"Syntax error: {exc.msg}") from exc

    node_count = 0
    for node in ast.walk(tree):
        node_count += 1
        if node_count > MAX_AST_NODES:
            raise ExpressionValidationError(
                f"Expression is too complex (more than {MAX_AST_NODES} "
                "syntax nodes)."
            )
        if not isinstance(node, _ALLOWED_NODES):
            raise ExpressionValidationError(
                f"Unsupported syntax '{_describe(node)}'. Factor expressions "
                "may only use operator calls, $fields, numbers and "
                "arithmetic/comparison operators."
            )
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ExpressionValidationError(
                    "Only plain operator calls like Op(...) are allowed "
                    f"(got a call on '{_describe(node.func)}')."
                )
            if node.func.id.startswith(_FIELD_PREFIX):
                raise ExpressionValidationError(
                    f"Field '${node.func.id[len(_FIELD_PREFIX) :]}' "
                    "cannot be called like a function."
                )
        elif isinstance(node, ast.Name):
            if node.id.startswith("_"):
                raise ExpressionValidationError(
                    f"Name '{node.id}' is not allowed (leading underscore)."
                )
        elif isinstance(node, ast.keyword):
            if node.arg is None or node.arg.startswith("_"):
                raise ExpressionValidationError(
                    "Only simple keyword arguments (name=value) are allowed."
                )
        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float, str, bool)):
                raise ExpressionValidationError(
                    f"Unsupported constant type {type(node.value).__name__}."
                )
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            _check_pow_exponent(node.right)

    _check_string_positions(tree)


def _is_constant_only(node: ast.AST) -> bool:
    """True if the subtree contains no names/calls (pure literal math)."""
    return not any(isinstance(n, (ast.Name, ast.Call)) for n in ast.walk(node))


def _literal_number(node: ast.AST):
    """Return the numeric value of ``5`` / ``-5`` / ``+5``, else None."""
    if isinstance(node, ast.UnaryOp) and isinstance(
        node.op, (ast.USub, ast.UAdd)
    ):
        inner = _literal_number(node.operand)
        if inner is None:
            return None
        return -inner if isinstance(node.op, ast.USub) else inner
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ):
        return node.value
    return None


def _check_pow_exponent(exponent: ast.AST) -> None:
    # A data-dependent exponent ($close, Mean(...)) is evaluated element-wise
    # by numpy and is fine. A pure-literal exponent is evaluated by Python at
    # eval time, so ``9 ** 9 ** 9`` would hang: require a small literal.
    if not _is_constant_only(exponent):
        return
    value = _literal_number(exponent)
    if value is None or abs(value) > _MAX_CONST_POW_EXPONENT:
        raise ExpressionValidationError(
            "Constant exponent must be a literal number with absolute value "
            f"<= {_MAX_CONST_POW_EXPONENT}."
        )


def _check_string_positions(tree: ast.AST) -> None:
    # String literals are only meaningful as operator arguments (e.g. the
    # group name in GroupNeutral(x, 'sector')). Inside arithmetic they can
    # only produce errors or huge allocations ('a' * 10**9).
    allowed = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            allowed.update(id(a) for a in node.args)
            allowed.update(id(k.value) for k in node.keywords)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in allowed
        ):
            raise ExpressionValidationError(
                "String literals are only allowed as operator arguments."
            )

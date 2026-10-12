from __future__ import annotations

import ast
import random
import re
from typing import Any, Callable

from aiminer.core.alphaeval.expr_validator import validate_factor_expression


def _normalize_expr(expr: str) -> str:
    return expr.strip()


def add_decay(
    expr: str,
    *,
    window: int = 10,
    decay_type: str = "WMA",
) -> str:
    """Wrap expression with a time-series decay operator (e.g. WMA)."""
    norm = _normalize_expr(expr)
    decay_op = decay_type.strip()
    return f"{decay_op}({norm}, {int(window)})"


def cross_sectional_ranking_wrapper(
    expr: str,
    *,
    operator: str = "CSRank",
) -> str:
    """Wrap expression with cross-sectional ranking / scale normalization."""
    norm = _normalize_expr(expr)
    op = operator.strip()
    return f"{op}({norm})"


def non_linear_transformation(
    expr: str,
    *,
    transform: str = "LogAbs",
    power: float = 2.0,
) -> str:
    """Apply non-linear transformations to accentuate or compress tails."""
    norm = _normalize_expr(expr)
    t = transform.strip().lower()
    if t in {"logabs", "log"}:
        return f"Log(Abs({norm}) + 1)"
    if t in {"power", "signed_power"}:
        p_val = int(power) if float(power).is_integer() else power
        return f"Sign({norm}) * Pow(Abs({norm}), {p_val})"
    if t in {"scale", "cszscore"}:
        return f"Scale({norm})"
    if t in {"sign"}:
        return f"Sign({norm})"
    raise ValueError(f"Unsupported non-linear transform: {transform}")


DEFAULT_REGIME_CONDITIONS = {
    "volume_surge": "Greater($volume, Mean($volume, 20))",
    "uptrend": "Greater($close, Mean($close, 20))",
    "high_volatility": "Greater(Std($close, 20), Mean(Std($close, 20), 60))",
    "momentum_positive": "Greater(Delta($close, 10), 0)",
}


def macro_condition_gating(
    expr: str,
    *,
    condition: str | None = None,
    regime_name: str | None = None,
    fallback: str = "0",
) -> str:
    """Gate an alpha factor conditionally based on macro or regime filters."""
    norm = _normalize_expr(expr)
    if condition is not None:
        cond_str = condition.strip()
    elif regime_name in DEFAULT_REGIME_CONDITIONS:
        cond_str = DEFAULT_REGIME_CONDITIONS[regime_name]
    else:
        cond_str = DEFAULT_REGIME_CONDITIONS["volume_surge"]

    return f"If({cond_str}, {norm}, {fallback})"


class _WindowParamTransformer(ast.NodeTransformer):
    """Mutate numeric integer parameters in AST representing window sizes."""

    def __init__(self, multiplier: float = 2.0):
        super().__init__()
        self.multiplier = multiplier

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, int) and node.value >= 2:
            new_val = max(2, int(round(node.value * self.multiplier)))
            return ast.copy_location(ast.Constant(value=new_val), node)
        return node


def mutate_ast_parameters(expr: str, *, multiplier: float = 2.0) -> str:
    """Mutate window parameter integers inside factor expression AST."""
    norm = _normalize_expr(expr)
    # Temporarily substitute $field so ast.parse is valid Python syntax
    field_re = re.compile(r"\$(\w+)")
    placeholders: dict[str, str] = {}

    def _replace(match: re.Match) -> str:
        name = match.group(1)
        ph = f"FIELD_{name}"
        placeholders[ph] = f"${name}"
        return ph

    py_expr = field_re.sub(_replace, norm)
    tree = ast.parse(py_expr, mode="eval")
    transformer = _WindowParamTransformer(multiplier=multiplier)
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    mutated = ast.unparse(new_tree)

    for ph, orig in placeholders.items():
        mutated = re.sub(rf"\b{ph}\b", orig, mutated)
    return mutated


class SemanticMutator:
    """Evolutionary AST mutation manager for alpha factor expressions."""

    def __init__(self, *, seed: int | None = None):
        self.rng = random.Random(seed)
        self.operators: dict[str, Callable[..., str]] = {
            "decay": lambda e: add_decay(
                e,
                window=self.rng.choice([5, 10, 20]),
                decay_type="WMA",
            ),
            "rank": lambda e: cross_sectional_ranking_wrapper(
                e, operator=self.rng.choice(["CSRank", "Rank"])
            ),
            "non_linear": lambda e: non_linear_transformation(
                e,
                transform=self.rng.choice(["LogAbs", "Power", "Scale"]),
                power=2.0,
            ),
            "regime_gate": lambda e: macro_condition_gating(
                e,
                regime_name=self.rng.choice(
                    list(DEFAULT_REGIME_CONDITIONS.keys())
                ),
            ),
            "param_mutation": lambda e: mutate_ast_parameters(
                e, multiplier=self.rng.choice([0.5, 1.5, 2.0])
            ),
        }

    def register_operator(
        self, name: str, fn: Callable[..., str]
    ) -> None:
        """Register a custom semantic mutation operator."""
        self.operators[name] = fn

    def mutate(
        self,
        expr: str,
        *,
        mutation_type: str | None = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> str:
        """Apply a semantic mutation to an expression and validate grammar."""
        if mutation_type is not None:
            if mutation_type not in self.operators:
                raise ValueError(
                    f"Unknown mutation operator '{mutation_type}'. "
                    f"Available: {list(self.operators.keys())}"
                )
            op_fn = self.operators[mutation_type]
        else:
            op_name = self.rng.choice(list(self.operators.keys()))
            op_fn = self.operators[op_name]

        mutated = op_fn(expr, **kwargs) if kwargs else op_fn(expr)
        if validate:
            validate_factor_expression(mutated)
        return mutated

    def batch_mutate(
        self,
        expressions: list[str],
        *,
        count: int = 5,
        max_attempts: int = 20,
    ) -> list[str]:
        """Generate diverse valid mutated factor expressions."""
        if not expressions:
            return []

        results: set[str] = set()
        attempts = 0
        while len(results) < count and attempts < max_attempts:
            attempts += 1
            base = self.rng.choice(expressions)
            try:
                cand = self.mutate(base, validate=True)
                if cand not in expressions:
                    results.add(cand)
            except Exception:
                continue

        return sorted(results)

import polars as pl
import polars_plugins as lib
from polars.plugins import register_plugin_function
import math
from loguru import logger
import os


# Find the binary plugin path
def get_plugin_path():
    lib_dir = os.path.dirname(lib.__file__)
    # Maturin usually puts the .so in the package dir
    for f in os.listdir(lib_dir):
        if f.endswith(".so"):
            return os.path.join(lib_dir, f)
    # Fallback to lib.__file__ if no .so found (might fail later)
    return lib.__file__


PLUGIN_PATH = get_plugin_path()


def register_ts_rank(expr, window_size):
    return register_plugin_function(
        plugin_path=PLUGIN_PATH,
        function_name="ts_rank",
        args=[expr],
        kwargs={"window_size": int(window_size)},
        is_elementwise=False,
    )


def register_ts_argmax(expr, window_size):
    return register_plugin_function(
        plugin_path=PLUGIN_PATH,
        function_name="ts_argmax",
        args=[expr],
        kwargs={"window_size": int(window_size)},
        is_elementwise=False,
    )


def register_ts_argmin(expr, window_size):
    return register_plugin_function(
        plugin_path=PLUGIN_PATH,
        function_name="ts_argmin",
        args=[expr],
        kwargs={"window_size": int(window_size)},
        is_elementwise=False,
    )


# Operators that map Qlib functions to Polars Expressions
# Applied in grouped context (over 'instrument' or 'datetime')


def Rank(x, n=None):
    if isinstance(x, (int, float)):
        return pl.lit(0.5)
    return x.rank(method="average").over("datetime") / x.count().over("datetime")


def CSRank(x):
    if isinstance(x, (int, float)):
        return pl.lit(0.5)
    return x.rank(method="average").over("datetime") / x.count().over("datetime")


def CSZScore(x, n=None):
    if isinstance(x, (int, float)):
        return pl.lit(0.0)
    # Cross-sectional normalization (n is ignored — accepted for LLM compatibility)
    mean = x.mean().over("datetime")
    std = x.std().over("datetime")
    std_safe = pl.when(std == 0).then(pl.lit(1.0)).otherwise(std)
    return (x - mean) / std_safe


def _get_int(n, op_name="Operator"):
    try:
        if isinstance(n, pl.Expr):
            raise ValueError(f"{op_name} expects a constant integer for the period argument, not a dynamic series. Fix the formula to use a fixed number (e.g., 5, 10, 20).")
        return int(float(n))
    except (ValueError, TypeError) as e:
        if "expects a constant" in str(e): raise e
        raise ValueError(f"Invalid period value '{n}' for {op_name}. Must be an integer.")


def Mean(x, n=None):
    if isinstance(x, (int, float)): return pl.lit(float(x))
    if n is None:
        return x.mean().over("datetime")
    return x.rolling_mean(window_size=_get_int(n, "Mean")).over("instrument")


def Std(x, n=None):
    if isinstance(x, (int, float)): return pl.lit(0.0)
    if n is None:
        return x.std().over("datetime")
    return x.rolling_std(window_size=_get_int(n, "Std")).over("instrument")


def Median(x, n=None):
    if isinstance(x, (int, float)): return pl.lit(float(x))
    if n is None:
        return x.median().over("datetime")
    return x.rolling_median(window_size=_get_int(n, "Median")).over("instrument")


def Sum(x, n):
    if isinstance(x, (int, float)): return pl.lit(float(x) * _get_int(n, "Sum"))
    return x.rolling_sum(window_size=_get_int(n, "Sum")).over("instrument")


def Ref(x, n):
    if isinstance(x, (int, float)): return pl.lit(float(x))
    return x.shift(_get_int(n, "Ref")).over("instrument")


def Delta(x, n):
    if isinstance(x, (int, float)): return pl.lit(0.0)
    return (x - x.shift(_get_int(n, "Delta"))).over("instrument")


def _ensure_expr(x):
    """Wrap a native Python numeric into pl.lit() so Polars methods can be called on it."""
    if isinstance(x, (int, float)):
        return pl.lit(float(x))
    return x


def Abs(x):
    return _ensure_expr(x).abs()


def Log(x):
    return _ensure_expr(x).log(base=math.e)


def Sign(x):
    if isinstance(x, (int, float)):
        return pl.lit(1.0 if x > 0 else (-1.0 if x < 0 else 0.0))
    return _ensure_expr(x).sign()


def Sqrt(x):
    return _ensure_expr(x).sqrt()


def Exp(x):
    return _ensure_expr(x).exp()


def Ceil(x):
    return _ensure_expr(x).ceil()


def Floor(x):
    return _ensure_expr(x).floor()


def Round(x, decimals=0):
    return _ensure_expr(x).round(int(decimals))


def Sin(x):
    return _ensure_expr(x).sin()


def Cos(x):
    return _ensure_expr(x).cos()


def Tan(x):
    return _ensure_expr(x).tan()


def Not(x):
    return ~_ensure_expr(x)


def If(cond, a, b):
    return pl.when(cond).then(a).otherwise(b)


def Greater(a, b):
    return a > b


def Less(a, b):
    return a < b


def GreaterEqual(a, b):
    return a >= b


def LessEqual(a, b):
    return a <= b


def Equal(a, b):
    return a == b


def NotEqual(a, b):
    return a != b


def And(*args):
    from functools import reduce

    return reduce(lambda a, b: a & b, args)


def Or(*args):
    from functools import reduce

    return reduce(lambda a, b: a | b, args)


def Corr(x, y, n):
    return pl.rolling_corr(x, y, window_size=_get_int(n, "Corr")).over("instrument")


def Cov(x, y, n):
    return pl.rolling_cov(x, y, window_size=_get_int(n, "Cov")).over("instrument")


def Var(x, n=None):
    if n is None:
        return x.var().over("datetime")
    return x.rolling_var(window_size=_get_int(n, "Var")).over("instrument")


def Skew(x, n):
    return x.rolling_skew(window_size=_get_int(n, "Skew")).over("instrument")


def Kurt(x, n):
    return x.rolling_kurtosis(window_size=_get_int(n, "Kurt")).over("instrument")


def Mad(x, n):
    # Mean Absolute Deviation
    n_int = _get_int(n, "Mad")
    mean_x = x.rolling_mean(window_size=n_int).over("instrument")
    return (x - mean_x).abs().rolling_mean(window_size=n_int).over("instrument")


def Scale(x, a=1):
    # Scale x such that sum(abs(x)) = a
    return (x / x.abs().sum().over("datetime")) * float(a)


def WMA(x, n):
    return x.ewm_mean(span=_get_int(n, "WMA")).over("instrument")


def Ts_Rank(x, n):
    return register_ts_rank(x, _get_int(n, "Ts_Rank")).over("instrument")


def Ts_Max(x, n):
    return x.rolling_max(window_size=_get_int(n, "Ts_Max")).over("instrument")


def Ts_Min(x, n):
    return x.rolling_min(window_size=_get_int(n, "Ts_Min")).over("instrument")


def Ts_ArgMax(x, n):
    return register_ts_argmax(x, _get_int(n, "Ts_ArgMax")).over("instrument")


def Ts_ArgMin(x, n):
    return register_ts_argmin(x, _get_int(n, "Ts_ArgMin")).over("instrument")


# Aliases for compiler mapping (in case compiler generates function calls instead of operators)
Add = lambda a, b: a + b
Sub = lambda a, b: a - b
Mul = lambda a, b: a * b
Div = lambda a, b: a / b
Mult = lambda a, b: a * b
Divi = lambda a, b: a / b
Plus = lambda a, b: a + b
Minus = lambda a, b: a - b


def EMA(x, n):
    return x.ewm_mean(span=_get_int(n, "EMA")).over("instrument")


def Winsorize(x, pct=0.05):
    # Cross-sectional winsorization
    lower = x.quantile(float(pct)).over("datetime")
    upper = x.quantile(1.0 - float(pct)).over("datetime")
    return x.clip(lower, upper)


def GroupNeutral(x):
    # Neutralize against market (cross-sectional mean)
    return x - x.mean().over("datetime")


def Percentile(x):
    return (x.rank() / x.count()).over("datetime")


def Clip(x, lower, upper):
    return x.clip(lower, upper)


def Count(x=None):
    # Usually counts instruments in cross-section
    if x is None:
        return pl.lit(1.0).count().over("datetime")
    return x.count().over("datetime")


def Ts_Percentile(x, n, p=50):
    return x.rolling_quantile(quantile=float(p) / 100.0, window_size=int(n)).over(
        "instrument"
    )


# Math aliases
Pow = lambda a, b: a**b
Neg = lambda a: -a
Inv = lambda a: 1.0 / a
Max = lambda a, b: pl.max_horizontal(a, b)
Min = lambda a, b: pl.min_horizontal(a, b)

# Extended aliases for LLM-generated expressions
Divide = lambda a, b: a / b
Multiply = lambda a, b: a * b
Subtract = lambda a, b: a - b
Negate = lambda a: -a


class _ColFallback(dict):
    """eval() namespace that returns pl.col(name) for any unknown identifier.
    This replaces the fragile string-regex approach: instead of rewriting
    "$field" → "pl.col('field')" (which breaks inside string literals and
    on complex nested expressions), we just strip the '$' prefix and let the
    eval environment map unknown names to column references at runtime."""

    def __missing__(self, key: str):
        return pl.col(key)


def _python_compile_alpha(expression: str) -> str:
    """Strip Qlib '$field' prefixes so the expression is valid Python syntax.
    Unknown names are resolved to pl.col(name) by _ColFallback at eval time,
    or by the ast.Name fallback in _eval_ast_node during eager evaluation."""
    import re as _re

    return _re.sub(r"\$(\w+)", r"\1", expression)


def _preprocess_expression(expression: str) -> str:
    """Normalize expression quirks that the Rust parser cannot handle."""
    expr = expression.strip()
    # Remove stray outer whitespace/newlines
    expr = " ".join(expr.split())
    return expr


class PolarsEngine:
    def __init__(self, df: pl.DataFrame = None):
        self.df = df
        self.context = {
            "pl": pl,
            "Rank": Rank,
            "CSRank": CSRank,
            "CSZScore": CSZScore,
            "Mean": Mean,
            "Std": Std,
            "Median": Median,
            "Sum": Sum,
            "Ref": Ref,
            "Delta": Delta,
            "Abs": Abs,
            "Log": Log,
            "If": If,
            "Greater": Greater,
            "Less": Less,
            "And": And,
            "Or": Or,
            "Corr": Corr,
            "Cov": Cov,
            "Ts_Rank": Ts_Rank,
            "Ts_Max": Ts_Max,
            "Ts_Min": Ts_Min,
            "Ts_ArgMax": Ts_ArgMax,
            "Ts_ArgMin": Ts_ArgMin,
            "Sign": Sign,
            "Sqrt": Sqrt,
            "Add": Add,
            "Sub": Sub,
            "Mul": Mul,
            "Div": Div,
            "Mult": Mult,
            "Divi": Divi,
            "Plus": Plus,
            "Minus": Minus,
            "GreaterEqual": GreaterEqual,
            "LessEqual": LessEqual,
            "Equal": Equal,
            "NotEqual": NotEqual,
            "Not": Not,
            "EMA": EMA,
            "Winsorize": Winsorize,
            "GroupNeutral": GroupNeutral,
            "Percentile": Percentile,
            "Clip": Clip,
            "Count": Count,
            "Ts_Percentile": Ts_Percentile,
            "Pow": Pow,
            "Neg": Neg,
            "Inv": Inv,
            "Max": Max,
            "Min": Min,
            "Correlation": Corr,
            "Exp": Exp,
            "Ceil": Ceil,
            "Floor": Floor,
            "Round": Round,
            "Sin": Sin,
            "Cos": Cos,
            "Tan": Tan,
            "Var": Var,
            "Skew": Skew,
            "Kurt": Kurt,
            "Mad": Mad,
            "Scale": Scale,
            "WMA": WMA,
            "Divide": Divide,
            "Multiply": Multiply,
            "Subtract": Subtract,
            "Negate": Negate,
            "Const": lambda x: pl.lit(x),
        }

    def evaluate(self, expression: str):
        """
        Evaluate a Qlib expression on a Polars DataFrame.
        Returns a polars.Expr.
        """
        expression = _preprocess_expression(expression)

        # 1. Try the Rust compiler first
        compiled = lib.compile_alpha(expression)
        use_fallback = False
        if compiled.startswith("Error:"):
            logger.warning(
                f"Rust compiler failed for: {expression}. Error: {compiled}. Trying Python fallback..."
            )
            use_fallback = True

        _ns = _ColFallback(self.context)

        if not use_fallback:
            try:
                expr = eval(compiled, {"__builtins__": {}}, _ns)
                if isinstance(expr, pl.Expr):
                    return expr.cast(pl.Float64)
                return expr
            except Exception as e:
                logger.warning(
                    f"Rust-compiled eval failed: {compiled}. Error: {e}. Trying Python fallback..."
                )
                use_fallback = True

        # 2. Python fallback compiler — strips '$' prefixes; unknown names
        #    resolve to pl.col(name) via _ColFallback.__missing__.
        if use_fallback:
            compiled = _python_compile_alpha(expression)
            logger.debug(f"Python fallback compiled: {compiled}")
            try:
                expr = eval(compiled, {"__builtins__": {}}, _ns)
                if isinstance(expr, pl.Expr):
                    return expr.cast(pl.Float64)
                return expr
            except Exception as e:
                logger.error(
                    f"Python fallback also failed for: {expression}. Compiled: {compiled}. Error: {e}"
                )
                raise

    def compute_all(self, df: pl.DataFrame, expressions: list):
        """
        Compute multiple factors on a DataFrame.
        Uses step-by-step eager evaluation to avoid Polars' limitation of
        chaining .over('instrument') and .over('datetime') in a single lazy
        expression (which produces all-null output).
        """
        result = df
        for e in expressions:
            try:
                result = self._eager_eval(result, e)
            except Exception as exc:
                logger.warning(f"[PolarsEngine] Failed to evaluate '{e}': {exc}")
                result = result.with_columns(pl.lit(None).cast(pl.Float64).alias(e))
        return result

    # ------------------------------------------------------------------ #
    # Eager step-by-step evaluator                                         #
    # ------------------------------------------------------------------ #
    # Cross-sectional operators that apply .rank()/.std().over('datetime')
    _CS_OPS = frozenset(
        {
            "Rank",
            "CSRank",
            "CSZScore",
            "GroupNeutral",
            "Winsorize",
            "Percentile",
            "Scale",
        }
    )
    # Time-series plugin operators that use register_plugin_function — they
    # receive an expression fed into a Rust plugin and cannot handle compound
    # nested expressions directly.  Materialise their first argument as a
    # temporary column so the plugin always receives a bare pl.col() reference.
    _TS_PLUGIN_OPS = frozenset(
        {
            "Ts_Rank",
            "Ts_ArgMax",
            "Ts_ArgMin",
        }
    )

    def _eager_eval(self, df: pl.DataFrame, expr_str: str) -> pl.DataFrame:
        """
        Parse *expr_str* into an AST, walk it bottom-up, and materialize
        intermediate results as temporary columns whenever a cross-sectional
        operator wraps a non-trivial (compound) expression.  This avoids the
        Polars limitation where chaining .over('instrument') inside an
        expression that then calls .over('datetime') produces all-null output.

        Returns *df* with the final result stored under column *expr_str*.
        Temporary intermediate columns are cleaned up before returning.
        """
        import ast as _ast

        # Strip '$' prefixes so the expression is valid Python for ast.parse().
        # The AST walker resolves unknown names to pl.col(name) via the
        # ast.Name fallback in _eval_ast_node — no string-level pl.col() needed.
        compiled = lib.compile_alpha(expr_str)
        if compiled.startswith("Error:"):
            compiled = _python_compile_alpha(expr_str)

        try:
            tree = _ast.parse(compiled, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Cannot parse expression '{expr_str}': {e}") from e

        tmp_cols: list[str] = []
        df_container = [df]

        pl_expr = self._eval_ast_node(tree.body, df_container, tmp_cols)
        df = df_container[0]

        if isinstance(pl_expr, pl.Expr):
            df = df.with_columns(pl_expr.cast(pl.Float64).alias(expr_str))
        else:
            df = df.with_columns(pl.lit(pl_expr).cast(pl.Float64).alias(expr_str))

        # Drop all intermediate temporary columns
        cols_to_drop = [c for c in tmp_cols if c in df.columns]
        if cols_to_drop:
            df = df.drop(cols_to_drop)

        return df

    def _eval_ast_node(
        self,
        node,
        df_container: list[pl.DataFrame],
        tmp_cols: list,
    ):
        """Recursively evaluate an AST node, materializing CS ops eagerly."""
        import ast as _ast

        # ---- Constant / literal ----
        if isinstance(node, _ast.Constant):
            return node.value

        # ---- Attribute (e.g. pl.lit, pl.col) ----
        if isinstance(node, _ast.Attribute):
            obj = self._eval_ast_node(node.value, df_container, tmp_cols)
            return getattr(obj, node.attr)

        # ---- Name (variable / function reference) ----
        if isinstance(node, _ast.Name):
            return self.context.get(node.id, pl.col(node.id))

        # ---- UnaryOp ----
        if isinstance(node, _ast.UnaryOp):
            operand = self._eval_ast_node(node.operand, df_container, tmp_cols)
            if isinstance(node.op, _ast.USub):
                return -operand if isinstance(operand, pl.Expr) else -operand
            if isinstance(node.op, _ast.UAdd):
                return operand
            if isinstance(node.op, _ast.Not):
                return ~operand
            raise ValueError(f"Unsupported unary op: {type(node.op)}")

        # ---- BinOp ----
        if isinstance(node, _ast.BinOp):
            left = self._eval_ast_node(node.left, df_container, tmp_cols)
            right = self._eval_ast_node(node.right, df_container, tmp_cols)
            op = node.op
            if isinstance(op, _ast.Add):
                return left + right
            if isinstance(op, _ast.Sub):
                return left - right
            if isinstance(op, _ast.Mult):
                return left * right
            if isinstance(op, _ast.Div):
                return left / right
            if isinstance(op, _ast.Pow):
                return left**right
            if isinstance(op, _ast.BitAnd):
                return left & right
            if isinstance(op, _ast.BitOr):
                return left | right
            raise ValueError(f"Unsupported binary op: {type(op)}")

        # ---- Compare ----
        if isinstance(node, _ast.Compare):
            left = self._eval_ast_node(node.left, df_container, tmp_cols)
            result = left
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_ast_node(comparator, df_container, tmp_cols)
                if isinstance(op, _ast.Gt):
                    result = result > right
                elif isinstance(op, _ast.Lt):
                    result = result < right
                elif isinstance(op, _ast.GtE):
                    result = result >= right
                elif isinstance(op, _ast.LtE):
                    result = result <= right
                elif isinstance(op, _ast.Eq):
                    result = result == right
                elif isinstance(op, _ast.NotEq):
                    result = result != right
                else:
                    raise ValueError(f"Unsupported compare op: {type(op)}")
            return result

        # ---- Call ----
        if isinstance(node, _ast.Call):
            func_name: str | None = None
            if isinstance(node.func, _ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, _ast.Attribute):
                # e.g. pl.col('close')
                obj = self._eval_ast_node(node.func.value, df_container, tmp_cols)
                args = [self._eval_ast_node(a, df_container, tmp_cols) for a in node.args]
                kw = {
                    kw.arg: self._eval_ast_node(kw.value, df_container, tmp_cols)
                    for kw in node.keywords
                }
                return getattr(obj, node.func.attr)(*args, **kw)

            func = self.context.get(func_name)
            if func is None:
                raise ValueError(f"Unknown function '{func_name}'")

            is_cs = func_name in self._CS_OPS
            is_ts_plugin = func_name in self._TS_PLUGIN_OPS

            # Evaluate arguments (recursively)
            args = []
            for arg_idx, arg_node in enumerate(node.args):
                arg_val = self._eval_ast_node(arg_node, df_container, tmp_cols)

                # For CS ops: if the argument is a complex Polars expression
                # (not a bare column reference), materialize it first so we
                # don't chain .over() inside .over().
                if (
                    is_cs
                    and isinstance(arg_val, pl.Expr)
                    and not self._is_bare_col(arg_node)
                ):
                    tmp = f"__cs_arg_{len(tmp_cols)}__"
                    df_container[0] = df_container[0].with_columns(arg_val.alias(tmp))
                    tmp_cols.append(tmp)
                    arg_val = pl.col(tmp)

                # For TS plugin ops: materialize only the first (data) argument
                # if it is a compound expression.  The plugin function passes
                # the series into Rust and cannot accept nested lazy expressions.
                elif (
                    is_ts_plugin
                    and arg_idx == 0
                    and isinstance(arg_val, pl.Expr)
                    and not self._is_bare_col(arg_node)
                ):
                    tmp = f"__ts_arg_{len(tmp_cols)}__"
                    df_container[0] = df_container[0].with_columns(arg_val.alias(tmp))
                    tmp_cols.append(tmp)
                    arg_val = pl.col(tmp)

                args.append(arg_val)

            kw = {
                kw.arg: self._eval_ast_node(kw.value, df_container, tmp_cols)
                for kw in node.keywords
            }
            return func(*args, **kw)

        raise ValueError(f"Unsupported AST node type: {type(node).__name__}")

    @staticmethod
    def _is_bare_col(node) -> bool:
        """Return True if the AST node is a bare pl.col(...) call (no nesting)."""
        import ast as _ast

        # pl.col('name')
        if isinstance(node, _ast.Call):
            if (
                isinstance(node.func, _ast.Attribute)
                and node.func.attr == "col"
                and isinstance(node.func.value, _ast.Name)
                and node.func.value.id == "pl"
            ):
                return True
        return False

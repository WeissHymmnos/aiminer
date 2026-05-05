"""
Custom Qlib operators that are NOT registered in stock qlib but are
listed in FactorAgent's QLIB_OPERATORS whitelist.

Registration happens after auto_init(), via register_custom_ops().
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import List, Type

from qlib.data.ops import (
    ExpressionOps,
    Expression,
    ElemOperator,
    PairOperator,
    Rolling,
    Operators,
    Abs,
    Sign,
    Log,
    Not,
    Power,
    Add,
    Sub,
    Mul,
    Div,
    Greater,
    Less,
    Gt,
    Ge,
    Lt,
    Le,
    Eq,
    Ne,
    And,
    Or,
    Max,
    Min,
    Med,
    Corr,
    Cov,
)


# ---------------------------------------------------------------------------
# Unary math operators
# ---------------------------------------------------------------------------


class Neg(ElemOperator):
    """Negate: -df"""

    def __init__(self, feature):
        super().__init__(feature)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        return -series


class Inv(ElemOperator):
    """Reciprocal: 1/df"""

    def __init__(self, feature):
        super().__init__(feature)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        with np.errstate(divide="ignore", invalid="ignore"):
            result = 1.0 / series
        result.replace([np.inf, -np.inf], np.nan, inplace=True)
        return result


class Sqrt(ElemOperator):
    """Square root: sqrt(df)"""

    def __init__(self, feature):
        super().__init__(feature)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        return np.sqrt(series.astype(np.float64))


class Exp(ElemOperator):
    """Exponential: exp(df)"""

    def __init__(self, feature):
        super().__init__(feature)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        return np.exp(series.astype(np.float64))


class Ceil(ElemOperator):
    """Ceiling: ceil(df)"""

    def __init__(self, feature):
        super().__init__(feature)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        return np.ceil(series)


class Floor(ElemOperator):
    """Floor: floor(df)"""

    def __init__(self, feature):
        super().__init__(feature)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        return np.floor(series)


# ---------------------------------------------------------------------------
# Time-series operators
# ---------------------------------------------------------------------------


class Ts_Rank(Rolling):
    """Time-series percentile rank of current value within the past n days."""

    def __init__(self, feature, N):
        super().__init__(feature, N, None)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        if self.N == 0:
            return series.expanding(min_periods=1).apply(
                lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=True
            )
        return series.rolling(self.N, min_periods=1).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=True
        )


class Ts_ArgMax(Rolling):
    """Days since the maximum value in the past n days (0 = today is max)."""

    def __init__(self, feature, N):
        super().__init__(feature, N, None)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        if self.N == 0:
            return series.expanding(min_periods=1).apply(
                lambda x: len(x) - 1 - x.argmax(), raw=True
            )
        return series.rolling(self.N, min_periods=1).apply(
            lambda x: len(x) - 1 - x.argmax(), raw=True
        )


class Ts_ArgMin(Rolling):
    """Days since the minimum value in the past n days (0 = today is min)."""

    def __init__(self, feature, N):
        super().__init__(feature, N, None)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        if self.N == 0:
            return series.expanding(min_periods=1).apply(
                lambda x: len(x) - 1 - x.argmin(), raw=True
            )
        return series.rolling(self.N, min_periods=1).apply(
            lambda x: len(x) - 1 - x.argmin(), raw=True
        )


class Ts_Percentile(Rolling):
    """p-th percentile value over the past n days (p in 0-100)."""

    def __init__(self, feature, N, p):
        super().__init__(feature, N, "quantile")
        self.p = p

    def __str__(self):
        return "{}({},{},{})".format(type(self).__name__, self.feature, self.N, self.p)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        q = self.p / 100.0
        if self.N == 0:
            return series.expanding(min_periods=1).quantile(q)
        return series.rolling(self.N, min_periods=1).quantile(q)


# ---------------------------------------------------------------------------
# Math binary aliases (different name, same behaviour as stock qlib ops)
# ---------------------------------------------------------------------------


class Mult(Mul):
    pass


class Divi(Div):
    pass


class Plus(Add):
    pass


class Minus(Sub):
    pass


class Multiply(Mul):
    pass


class Divide(Div):
    pass


class Subtract(Sub):
    pass


class Negate(Neg):
    pass


class Pow(Power):
    pass


# ---------------------------------------------------------------------------
# Comparison / logic aliases
# ---------------------------------------------------------------------------


class GreaterEqual(Ge):
    pass


class LessEqual(Le):
    pass


class Equal(Eq):
    pass


class NotEqual(Ne):
    pass


# ---------------------------------------------------------------------------
# Time-series aliases (Ts_Max ≡ Max, Ts_Min ≡ Min, Median ≡ Med)
# ---------------------------------------------------------------------------


class Ts_Max(Max):
    pass


class Ts_Min(Min):
    pass


class Median(Med):
    pass


# ---------------------------------------------------------------------------
# Correlation alias
# ---------------------------------------------------------------------------


class Correlation(Corr):
    pass


# ---------------------------------------------------------------------------
# Clip: clamp values to [lower, upper]
# ---------------------------------------------------------------------------


class Clip(PairOperator):
    """Clip(df, lower, upper): clamp values to [lower, upper]."""

    def __init__(self, feature, lower, upper):
        super().__init__(feature, None)
        self.lower = lower
        self.upper = upper

    def __str__(self):
        return "{}({},{},{})".format(
            type(self).__name__, self.feature_left, self.lower, self.upper
        )

    def get_longest_back_rolling(self):
        if isinstance(self.feature_left, (Expression,)):
            return self.feature_left.get_longest_back_rolling()
        return 0

    def get_extended_window_size(self):
        if isinstance(self.feature_left, (Expression,)):
            return self.feature_left.get_extended_window_size()
        return 0, 0

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature_left.load(instrument, start_index, end_index, *args)
        return series.clip(lower=self.lower, upper=self.upper)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

CUSTOM_OPS: List[Type[ExpressionOps]] = [
    # Unary math
    Neg,
    Inv,
    Sqrt,
    Exp,
    Ceil,
    Floor,
    # Time-series
    Ts_Rank,
    Ts_ArgMax,
    Ts_ArgMin,
    Ts_Percentile,
    # Binary math aliases
    Mult,
    Divi,
    Plus,
    Minus,
    Multiply,
    Divide,
    Subtract,
    Negate,
    Pow,
    # Comparison aliases
    GreaterEqual,
    LessEqual,
    Equal,
    NotEqual,
    # Time-series aliases
    Ts_Max,
    Ts_Min,
    Median,
    # Correlation alias
    Correlation,
    # Misc
    Clip,
]


def register_custom_ops():
    """Register all custom operators with Qlib's global Operators registry.

    Must be called AFTER auto_init() / register_all_ops().
    """
    Operators.register(CUSTOM_OPS)

from __future__ import annotations

import ast
import os
from typing import Any, List, Optional

from dotenv import load_dotenv
from loguru import logger
import numpy as np
import pandas as pd

from aiminer.core.alphaeval.expr_validator import validate_factor_expression
from aiminer.core.alphaeval.holdout import resolve_split_dates, segment_stats
from aiminer.core.constants import TRADING_DAYS_PER_YEAR

try:
    import matplotlib
except ImportError:  # plots are optional for local child eval
    matplotlib = None  # type: ignore[assignment]

if matplotlib is not None:
    matplotlib.use("Agg", force=True)

try:
    import rqdatac as rq
except ImportError:  # local-data / skip_auth paths do not need RiceQuant
    rq = None

# Load environment variables
load_dotenv()


# --- AST Safety Transformer ---


class SafeEvalTransformer(ast.NodeTransformer):
    def __init__(self, known_names):
        self.known_names = set(known_names)

    def visit_Call(self, node):
        # Recursively visit arguments first
        node.args = [self.visit(arg) for arg in node.args]
        node.keywords = [self.visit(kw) for kw in node.keywords]

        # If the function name itself is unknown, we handle it
        if (
            isinstance(node.func, ast.Name)
            and node.func.id not in self.known_names
        ):
            logger.warning(
                f"Function '{node.func.id}' is unknown. It might fail or needs a fallback."
            )
            # We keep it as a Name, but we could also wrap it or map it.
            # For now, let's just visit it normally.
        return node

    def visit_Name(self, node):
        # Only transform to string if it's NOT a known function/field
        # AND it's not the function being called in a Call node (handled by visit_Call)
        if node.id not in self.known_names:
            # Transform unknown Name nodes into string literals (e.g., 'sector')
            return ast.Constant(value=node.id)
        return node


def zscore(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    means = df.mean(axis=0, skipna=True)
    stds = df.std(axis=0, skipna=True).replace(0, np.nan)
    res = df.sub(means, axis=1)
    res = res.div(stds, axis=1).fillna(0)
    return res


_rq_initialized = False


def init_rq_auth():
    global _rq_initialized
    if _rq_initialized:
        return
    if rq is None:
        raise ImportError(
            "rqdatac is required for RiceQuant live data but is not installed"
        )

    token = os.getenv("RQ_TOKEN")
    username = os.getenv("RQ_USER")
    password = os.getenv("RQ_PASS")

    # 1. Try Token Mode (Priority)
    if token and len(token.strip()) > 50:
        tk = token.strip()
        logger.info(f"Attempting RiceQuant License Auth (Length: {len(tk)})...")
        try:
            rq.init(token=tk)
            logger.info("RiceQuant Token Auth sequence completed.")
            _rq_initialized = True
            return
        except Exception as e:
            logger.warning(
                f"RiceQuant Token Auth failed: {e}. Trying Password fallback..."
            )

    # 2. Try User/Pass Mode (Confirmed working in test_rq.py)
    if username and password and "your-" not in username.lower():
        logger.info(f"Attempting RiceQuant Password Auth (User: {username})...")
        try:
            rq.init(username=username.strip(), password=password.strip())
            logger.info("RiceQuant Password Auth Successful!")
            _rq_initialized = True
            return
        except Exception as e:
            logger.error(f"RiceQuant Password Auth failed: {e}")
            raise

    raise ValueError(
        "RiceQuant Auth Failed: No valid credentials found or accepted."
    )


from pathlib import Path

try:
    from matplotlib import font_manager
    import matplotlib.pyplot as plt
except ImportError:
    font_manager = None  # type: ignore[assignment]
    plt = None  # type: ignore[assignment]


class RiceQuantEval:
    """
    RiceQuant-compatible evaluator with IS/OOS split, layered analysis, and plotting.
    """

    def __init__(
        self,
        factor_expressions: List[str],
        weights: Optional[List[float]] = None,
        train_start_date: str = "2010-01-01",
        train_end_date: str = "2016-12-31",
        test_start_date: str = "2018-01-01",
        test_end_date: str = "2025-12-31",
        market: str = "000300.XSHG",  # CSI 300
        daily_normalize: bool = True,
        engine: str = "pandas",
        noise_level: float = 0.0,
        output_dir: str = "results/reports",
        skip_auth: bool = False,
        valid_split_date: Optional[str] = None,
        oos_split_date: Optional[str] = None,
        cost_bps: float = 5.0,
        slippage_model: str = "fixed",
        impact_gamma: float = 0.1,
        portfolio_value: float = 1e7,
        impact_model: Any | None = None,
    ):
        self.factor_expressions = factor_expressions
        self.weights = weights if weights else [1.0] * len(factor_expressions)
        self.test_start_date = test_start_date
        self.test_end_date = test_end_date
        self._explicit_valid_split_date = valid_split_date
        self._explicit_oos_split_date = oos_split_date
        self.valid_split_date, self.oos_split_date = resolve_split_dates(
            test_start_date, test_end_date, valid_split_date, oos_split_date
        )
        self.market = market
        self.daily_normalize = daily_normalize
        self.engine = engine
        self.noise_level = noise_level
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cost_bps = float(cost_bps)
        self.slippage_model_name = str(slippage_model)
        self.impact_gamma = float(impact_gamma)
        self.portfolio_value = float(portfolio_value)
        if impact_model is not None:
            self.impact_model = impact_model
        else:
            from aiminer.core.alphaeval.market_impact import build_impact_model

            self.impact_model = build_impact_model(
                self.slippage_model_name,
                cost_bps=self.cost_bps,
                impact_gamma=self.impact_gamma,
                portfolio_value=self.portfolio_value,
            )
        self.effective_cost_bps: float = self.cost_bps
        self.total_cost_drag: float = 0.0
        self.turnover_series: pd.Series = pd.Series(dtype=float)
        self.mean_turnover: float = 0.0
        self.turnover: float = 0.0
        self.gross_daily_returns_series: pd.Series = pd.Series(dtype=float)
        self.daily_returns_series: pd.Series = pd.Series(dtype=float)

        # Full-window metrics (manual backtests / reports).
        self.ic = 0.0
        self.rankic = 0.0
        self.sharpe = 0.0
        self.gross_sharpe = 0.0
        self.max_dd = 0.0
        self.gross_max_dd = 0.0
        # Per-segment metrics. ``None`` means the segment has no data; it is
        # never back-filled with another window's value.
        self.is_ic: Optional[float] = None
        self.is_rankic: Optional[float] = None
        self.is_sharpe: Optional[float] = None
        self.is_gross_sharpe: Optional[float] = None
        self.is_max_dd: Optional[float] = None
        self.is_turnover: Optional[float] = None
        self.val_ic: Optional[float] = None
        self.val_rankic: Optional[float] = None
        self.val_sharpe: Optional[float] = None
        self.val_gross_sharpe: Optional[float] = None
        self.val_turnover: Optional[float] = None
        self.oos_ic: Optional[float] = None
        self.oos_rankic: Optional[float] = None
        self.oos_sharpe: Optional[float] = None
        self.oos_gross_sharpe: Optional[float] = None
        self.oos_max_dd: Optional[float] = None
        self.oos_turnover: Optional[float] = None
        self.segment_metrics: dict = {}
        self.rre = 0.0
        self.plot_paths = {}

        self._configure_matplotlib()
        if not skip_auth:
            init_rq_auth()

    @staticmethod
    def _daily_rank_ic(all_data: pd.DataFrame) -> pd.Series:
        """Compute per-date Spearman rank IC with sparse cross-section guards."""

        def _corr(group: pd.DataFrame) -> float:
            factor = group["factor"].replace([np.inf, -np.inf], np.nan)
            label = group["label"].replace([np.inf, -np.inf], np.nan)
            valid = pd.concat([factor, label], axis=1).dropna()
            if len(valid) < 2:
                return np.nan
            if valid.iloc[:, 0].nunique(dropna=True) < 2:
                return np.nan
            if valid.iloc[:, 1].nunique(dropna=True) < 2:
                return np.nan
            return float(valid.iloc[:, 0].rank().corr(valid.iloc[:, 1].rank()))

        return all_data.groupby(level="datetime").apply(_corr)

    def _configure_matplotlib(self):
        if font_manager is None or plt is None:
            return
        preferred_fonts = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
        installed = {font.name for font in font_manager.fontManager.ttflist}
        for f in preferred_fonts:
            if f in installed:
                plt.rcParams["font.family"] = f
                break
        plt.rcParams["axes.unicode_minus"] = False

    def calculate_layered_returns(self, all_data, n_groups=5):
        """Compute returns for n_groups sorted by factor value."""
        max_cross_section = int(all_data.groupby(level="datetime").size().max())
        effective_groups = min(n_groups, max_cross_section)
        if effective_groups < 2:
            return pd.DataFrame()
        labels = [f"G{i + 1}" for i in range(effective_groups)]

        def assign_groups(x):
            if len(x) < effective_groups:
                return pd.Series(np.nan, index=x.index)
            try:
                return pd.qcut(
                    x.rank(method="first"), effective_groups, labels=labels
                )
            except ValueError:
                return pd.Series(np.nan, index=x.index)

        all_data = all_data.copy()
        all_data["group"] = all_data.groupby("datetime", group_keys=False)[
            "factor"
        ].apply(assign_groups)
        layer_ret = (
            all_data.groupby(["datetime", "group"])["label"]
            .mean()
            .unstack("group")
        )

        return layer_ret

    def generate_plots(
        self,
        daily_ret: pd.Series,
        layer_ret: pd.DataFrame,
        factor_name: str,
        gross_ret: Optional[pd.Series] = None,
        turnover_series: Optional[pd.Series] = None,
    ):
        """Generate and save backtest plots."""
        if plt is None:
            logger.warning("matplotlib not installed; skipping plots.")
            return {}
        safe_name = "".join(
            [c if (c.isalnum() or c in "._-") else "_" for c in factor_name]
        )[:50]
        plot_paths = {}

        gross_s = (
            gross_ret
            if gross_ret is not None
            else getattr(self, "gross_daily_returns_series", None)
        )
        to_s = (
            turnover_series
            if turnover_series is not None
            else getattr(self, "turnover_series", None)
        )
        has_turnover = to_s is not None and not to_s.empty
        has_gross = gross_s is not None and not gross_s.empty

        # 1. Cumulative Returns (Net vs Gross Equity & Turnover)
        if has_turnover:
            fig, (ax1, ax2) = plt.subplots(
                2,
                1,
                figsize=(10, 7),
                sharex=True,
                gridspec_kw={"height_ratios": [3, 1]},
            )
        else:
            fig, ax1 = plt.subplots(1, 1, figsize=(10, 5))
            ax2 = None

        cum_net = (1 + daily_ret.fillna(0)).cumprod()
        cost_bps_val = getattr(self, "cost_bps", 5.0)
        ax1.plot(
            cum_net.index,
            cum_net.values,
            label=f"Net Equity ({cost_bps_val:.1f} bps)",
            color="#1f77b4",
            linewidth=1.8,
        )

        if has_gross:
            cum_gross = (1 + gross_s.fillna(0)).cumprod()
            ax1.plot(
                cum_gross.index,
                cum_gross.values,
                label="Gross Equity",
                color="#7f7f7f",
                linestyle="--",
                linewidth=1.4,
                alpha=0.85,
            )

        if getattr(self, "oos_split_date", None):
            ax1.axvline(
                x=pd.to_datetime(self.oos_split_date),
                color="r",
                linestyle="--",
                label="OOS Split",
            )
            if ax2 is not None:
                ax2.axvline(
                    x=pd.to_datetime(self.oos_split_date),
                    color="r",
                    linestyle="--",
                )

        ax1.set_title(f"Factor Equity Curve: {factor_name}")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)

        if ax2 is not None:
            ax2.plot(
                to_s.index,
                to_s.values,
                label="Turnover",
                color="#ff7f0e",
                linewidth=1.2,
            )
            mean_to = float(to_s.mean())
            ax2.axhline(
                y=mean_to,
                color="#2ca02c",
                linestyle=":",
                label=f"Mean Turnover: {mean_to:.2%}",
            )
            ax2.set_ylabel("Turnover")
            ax2.legend(loc="upper left")
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        eq_path = self.output_dir / f"{safe_name}_equity.png"
        plt.savefig(eq_path, dpi=120)
        plt.close()
        plot_paths["equity"] = str(eq_path.resolve())

        # Also save standalone turnover plot if turnover is available
        if has_turnover:
            plt.figure(figsize=(10, 4))
            to_s.plot(
                title=f"Turnover — {factor_name}", color="#ff7f0e", grid=True
            )
            plt.axhline(
                y=float(to_s.mean()),
                color="#2ca02c",
                linestyle=":",
                label=f"Mean: {float(to_s.mean()):.2%}",
            )
            if getattr(self, "oos_split_date", None):
                plt.axvline(
                    x=pd.to_datetime(self.oos_split_date),
                    color="r",
                    linestyle="--",
                    label="OOS Split",
                )
            plt.legend()
            to_path = self.output_dir / f"{safe_name}_turnover.png"
            plt.savefig(to_path, dpi=120)
            plt.close()
            plot_paths["turnover"] = str(to_path.resolve())

        # 2. Layered Returns
        if (
            not layer_ret.empty
            and not layer_ret.select_dtypes(include=[np.number]).empty
        ):
            plt.figure(figsize=(10, 5))
            layer_cum = (1 + layer_ret.fillna(0)).cumprod()
            layer_cum.plot(title="Layered Cumulative Returns")
            if getattr(self, "oos_split_date", None):
                plt.axvline(
                    x=pd.to_datetime(self.oos_split_date),
                    color="r",
                    linestyle="--",
                    label="OOS Split",
                )
            plt.legend()
            plt.grid(True, alpha=0.3)
            lay_path = self.output_dir / f"{safe_name}_layers.png"
            plt.savefig(lay_path, dpi=120)
            plt.close()
            plot_paths["layers"] = str(lay_path.resolve())

        return plot_paths

    def fetch_data(self):
        """Fetch price data from RiceQuant."""
        logger.info(
            f"Fetching data for {self.market} from {self.test_start_date} to {self.test_end_date}"
        )

        # Get instruments
        instruments = rq.index_components(self.market, self.test_end_date)

        # Fetch OHLCV + Turnover
        fields = ["close", "open", "high", "low", "volume", "total_turnover"]
        df = rq.get_price(
            instruments,
            start_date=self.test_start_date,
            end_date=self.test_end_date,
            frequency="1d",
            fields=fields,
        )

        # rqdatac returns a multi-index DataFrame (order_book_id, date)
        # We want to match qlib's (datetime, instrument)
        df.index.names = ["instrument", "datetime"]
        df = df.reorder_levels(["datetime", "instrument"]).sort_index()

        # Inject noise if requested
        if self.noise_level > 0:
            logger.info(
                f"Injecting Gaussian noise (level={self.noise_level}) into raw data."
            )
            for col in df.columns:
                if df[col].dtype in [np.float64, np.float32]:
                    # Add noise proportional to the standard deviation of each feature
                    std = df[col].std()
                    noise = np.random.normal(
                        0, std * self.noise_level, size=df[col].shape
                    )
                    df[col] = df[col] + noise

        self.raw_data = df

        # Calculate label (next day return)
        # We MUST shift within each instrument to avoid cross-instrument leak
        # and to ensure the last date for each instrument is NaN.
        df_sorted = df.sort_index(level=["instrument", "datetime"])
        label_s = df_sorted.groupby(level="instrument", group_keys=False)[
            "close"
        ].apply(lambda x: x.shift(-1) / x - 1)
        self.label_data = (
            label_s.to_frame(name="label")
            .reorder_levels(["datetime", "instrument"])
            .sort_index()
        )

        # Ensure consistent datetime type
        if not pd.api.types.is_datetime64_any_dtype(
            self.label_data.index.get_level_values("datetime")
        ):
            idx = self.label_data.index
            new_dt = pd.to_datetime(idx.get_level_values("datetime"))
            self.label_data.index = pd.MultiIndex.from_arrays(
                [new_dt, idx.get_level_values("instrument")],
                names=["datetime", "instrument"],
            )

        logger.info("Data fetching done.")

    def _normalize_factors(self, df):
        if self.daily_normalize:
            return (
                df.groupby(level="datetime", group_keys=False)
                .apply(zscore)
                .replace([np.inf, -np.inf], np.nan)
                .replace(np.nan, 0)
            )
        return df.fillna(0)

    # --- Factor Computation ---
    def compute_factors(self):
        """
        Compute factors using unstacked matrix operations for Qlib-style expressions.
        """
        if self.engine == "polars":
            self.compute_factors_polars()
            return

        logger.info("Computing factors using Matrix Engine (Pandas)...")

        # 1. Unstack fields into matrices (Index: datetime, Columns: instrument)
        fields = {}
        for col in self.raw_data.columns:
            fields[col] = self.raw_data[col].unstack()

        # Add vwap: total_turnover / volume
        if "total_turnover" in fields and "volume" in fields:
            fields["vwap"] = fields["total_turnover"] / fields[
                "volume"
            ].replace(0, np.nan)
            fields["vwap"] = fields["vwap"].ffill().fillna(fields["close"])

        ref_field = fields["close"]

        def _ensure_df(value):
            if isinstance(value, (int, float, np.integer, np.floating)):
                return pd.DataFrame(
                    float(value),
                    index=ref_field.index,
                    columns=ref_field.columns,
                )
            return value

        # Define local helper functions for the eval engine
        def Rank(df):
            df = _ensure_df(df)
            return df.rank(axis=1, pct=True)

        def Mean(df, n=None):
            df = _ensure_df(df)
            if n is None:
                res = df.mean(axis=1)
                return pd.DataFrame(
                    np.repeat(res.values[:, np.newaxis], df.shape[1], axis=1),
                    index=df.index,
                    columns=df.columns,
                )
            return df.rolling(max(1, _get_n(n))).mean()

        def Std(df, n=None):
            df = _ensure_df(df)
            if n is None:
                res = df.std(axis=1)
                return pd.DataFrame(
                    np.repeat(res.values[:, np.newaxis], df.shape[1], axis=1),
                    index=df.index,
                    columns=df.columns,
                )
            return df.rolling(max(1, _get_n(n))).std()

        def Median(df, n=None):
            df = _ensure_df(df)
            if n is None:
                res = df.median(axis=1)
                return pd.DataFrame(
                    np.repeat(res.values[:, np.newaxis], df.shape[1], axis=1),
                    index=df.index,
                    columns=df.columns,
                )
            return df.rolling(max(1, _get_n(n))).median()

        def EMA(df, n):
            df = _ensure_df(df)
            return df.ewm(span=max(1, _get_n(n))).mean()

        def Abs(df):
            df = _ensure_df(df)
            return np.abs(df)

        def _get_n(n):
            if isinstance(n, (pd.Series, pd.DataFrame)):
                try:
                    val = n.iloc[-1]
                    if isinstance(val, pd.Series):
                        val = val.iloc[-1]
                    return int(val)
                except (TypeError, ValueError, AttributeError, IndexError):
                    return 20  # Fallback
            try:
                return int(float(n))
            except (TypeError, ValueError):
                return 20

        def Ref(df, n):
            df = _ensure_df(df)
            return df.shift(_get_n(n))

        def Log(df):
            df = _ensure_df(df)
            return np.log(df.replace(0, np.nan))

        def Sum(df, n):
            df = _ensure_df(df)
            return df.rolling(max(1, _get_n(n))).sum()

        def If(cond, a, b):
            cond = _ensure_df(cond)
            # If 'a' is scalar, convert to DF to match cond
            if isinstance(a, (int, float)):
                a = pd.DataFrame(a, index=cond.index, columns=cond.columns)
            if isinstance(b, (int, float)):
                b = pd.DataFrame(b, index=cond.index, columns=cond.columns)
            return a.where(cond, b)

        def Greater(a, b):
            return a > b

        def Less(a, b):
            return a < b

        def And(*args):
            from functools import reduce

            return reduce(lambda a, b: a & b, args)

        def Or(*args):
            from functools import reduce

            return reduce(lambda a, b: a | b, args)

        def Delta(df, n):
            df = _ensure_df(df)
            return df.diff(_get_n(n))

        def Corr(df1, df2, n):
            df1 = _ensure_df(df1)
            df2 = _ensure_df(df2)
            return df1.rolling(max(1, _get_n(n))).corr(df2)

        def Cov(df1, df2, n):
            df1 = _ensure_df(df1)
            df2 = _ensure_df(df2)
            return df1.rolling(max(1, _get_n(n))).cov(df2)

        def Ts_Rank(df, n):
            df = _ensure_df(df)
            nn = max(1, _get_n(n))
            if nn == 1:
                return pd.DataFrame(0.5, index=df.index, columns=df.columns)

            # Match Rust ts_rank: rank = count(v <= last) / count(valid) in window.
            # Rust requires window_size total rows (NaN allowed); use min_periods=1 and
            # check window length internally so partial warmup windows return NaN.
            def _ts_rank_row(x):
                if len(x) < nn:  # Warmup: not enough rows yet
                    return np.nan
                last = x.iloc[-1]
                if pd.isna(last):
                    return np.nan
                valid = x.dropna()
                if len(valid) == 0:
                    return np.nan
                return float((valid <= last).sum()) / len(valid)

            return df.rolling(nn, min_periods=1).apply(_ts_rank_row, raw=False)

        def CSRank(df):
            df = _ensure_df(df)
            return df.rank(axis=1, pct=True)

        def Percentile(df, p=50):
            """Cross-sectional percentile rank (p parameter reserved for API compatibility)."""
            df = _ensure_df(df)
            return df.rank(axis=1, pct=True)

        def Clip(df, lower, upper):
            df = _ensure_df(df)
            return df.clip(
                lower=lower,
                upper=upper,
                axis=0 if isinstance(lower, pd.Series) else None,
            )

        def CSZScore(df):
            df = _ensure_df(df)
            return df.sub(df.mean(axis=1), axis=0).div(
                df.std(axis=1).replace(0, 1), axis=0
            )

        def Winsorize(df, pct=0.05):
            df = _ensure_df(df)
            # Simple winsorization on cross-section
            return df.apply(
                lambda x: x.clip(
                    lower=x.quantile(float(pct)),
                    upper=x.quantile(1 - float(pct)),
                ),
                axis=1,
            )

        def GroupNeutral(df, group="sector"):
            df = _ensure_df(df)
            # Simplified neutral: just subtract cross-sectional mean
            return df.sub(df.mean(axis=1), axis=0)

        def Count(df=None, n=20):
            if df is None:
                c = fields["close"].shape[1]
                return pd.DataFrame(
                    c,
                    index=fields["close"].index,
                    columns=fields["close"].columns,
                )
            df = _ensure_df(df)
            return df.rolling(max(1, _get_n(n))).count()

        def Sign(df):
            df = _ensure_df(df)
            return np.sign(df)

        def Sqrt(df):
            df = _ensure_df(df)
            return np.sqrt(df.clip(lower=0))

        def Exp(df):
            df = _ensure_df(df)
            return np.exp(df.clip(upper=500))  # clip to avoid overflow

        def Ceil(df):
            df = _ensure_df(df)
            return np.ceil(df)

        def Floor(df):
            df = _ensure_df(df)
            return np.floor(df)

        def Scale(df, a=1):
            df = _ensure_df(df)
            abs_sum = df.abs().sum(axis=1).replace(0, np.nan)
            return df.div(abs_sum, axis=0) * float(a)

        def WMA(df, n):
            df = _ensure_df(df)
            nn = max(1, _get_n(n))
            weights = np.arange(1, nn + 1, dtype=float)
            weights /= weights.sum()
            return df.rolling(nn, min_periods=1).apply(
                lambda x: (
                    np.dot(x[-len(weights) :], weights[-len(x) :])
                    / weights[-len(x) :].sum()
                ),
                raw=True,
            )

        def Ts_ArgMax(df, n):
            df = _ensure_df(df)
            nn = max(1, _get_n(n))

            # Match Rust: skip NaN, return position of max within full window
            def _row(x):
                if len(x) < nn:
                    return np.nan
                return (
                    float(np.nanargmax(x))
                    if not np.all(np.isnan(x))
                    else np.nan
                )

            return df.rolling(nn, min_periods=1).apply(_row, raw=True)

        def Ts_ArgMin(df, n):
            df = _ensure_df(df)
            nn = max(1, _get_n(n))

            def _row(x):
                if len(x) < nn:
                    return np.nan
                return (
                    float(np.nanargmin(x))
                    if not np.all(np.isnan(x))
                    else np.nan
                )

            return df.rolling(nn, min_periods=1).apply(_row, raw=True)

        def Ts_Percentile(df, n, p=50):
            df = _ensure_df(df)
            # Rolling percentile VALUE (p-th percentile of last n days)
            # Default p=50 (median) if not provided
            return df.rolling(max(1, _get_n(n))).apply(
                lambda x: np.percentile(x, float(p)), raw=True
            )

        # Basic operator aliases for LLM compatibility
        def Add(a, b):
            return a + b

        def Sub(a, b):
            return a - b

        def Mul(a, b):
            return a * b

        def Div(a, b):
            return a / b

        def Pow(a, b):
            return a**b

        def Neg(a):
            return -a

        def Inv(a):
            return 1.0 / a

        def Max(a, b):
            return np.maximum(a, b)

        def Min(a, b):
            return np.minimum(a, b)

        # Build context for eval
        context = {
            "fields": fields,
            "np": np,
            "pd": pd,
            "Rank": Rank,
            "Mean": Mean,
            "Ref": Ref,
            "Abs": Abs,
            "Std": Std,
            "Log": Log,
            "Sum": Sum,
            "If": If,
            "Greater": Greater,
            "Less": Less,
            "And": And,
            "Or": Or,
            "Delta": Delta,
            "Corr": Corr,
            "Cov": Cov,
            "Ts_Rank": Ts_Rank,
            "Median": Median,
            "EMA": EMA,
            "CSRank": CSRank,
            "CSZScore": CSZScore,
            "Winsorize": Winsorize,
            "GroupNeutral": GroupNeutral,
            "Percentile": Percentile,
            "Clip": Clip,
            "Count": Count,
            "Correlation": Corr,
            "Sign": Sign,
            "Sqrt": Sqrt,
            "Ts_ArgMax": Ts_ArgMax,
            "Ts_ArgMin": Ts_ArgMin,
            "Ts_Max": lambda df, n: df.rolling(max(1, _get_n(n))).max(),
            "Ts_Min": lambda df, n: df.rolling(max(1, _get_n(n))).min(),
            "Ts_Percentile": Ts_Percentile,
            "Add": Add,
            "Sub": Sub,
            "Mul": Mul,
            "Div": Div,
            "Mult": lambda a, b: a * b,
            "Divi": lambda a, b: a / b,
            "Plus": lambda a, b: a + b,
            "Minus": lambda a, b: a - b,
            "Pow": Pow,
            "Neg": Neg,
            "Inv": Inv,
            "Max": Max,
            "Min": Min,
            # Extended aliases for Polars compiler / LLM-generated expressions
            "Const": lambda x: x,
            "Divide": lambda a, b: a / b,
            "Multiply": lambda a, b: a * b,
            "Subtract": lambda a, b: a - b,
            "Negate": lambda a: -a,
            "GreaterEqual": lambda a, b: a >= b,
            "LessEqual": lambda a, b: a <= b,
            "Equal": lambda a, b: a == b,
            "NotEqual": lambda a, b: a != b,
            "Not": lambda a: ~a,
            # Math functions missing from original context
            "Exp": Exp,
            "Ceil": Ceil,
            "Floor": Floor,
            "Scale": Scale,
            "WMA": WMA,
        }

        factor_matrices = []

        for expr in self.factor_expressions:
            try:
                validate_factor_expression(expr)
                # Prepare expression for Python eval
                safe_expr = expr
                # Handle standard fields
                for col in fields.keys():
                    safe_expr = safe_expr.replace(f"${col}", f"fields['{col}']")

                # Handle unknown $fields by falling back to closest logical values
                if "$" in safe_expr:
                    import re

                    unknown_fields = re.findall(r"\$\w+", safe_expr)
                    for uf in unknown_fields:
                        logger.warning(
                            f"Field {uf} not found in database. Falling back to default values."
                        )
                        if "vol" in uf.lower():
                            safe_expr = safe_expr.replace(
                                uf, "fields['volume']"
                            )
                        elif "share" in uf.lower():
                            safe_expr = safe_expr.replace(
                                uf, "1.0"
                            )  # Assume unit shares
                        else:
                            safe_expr = safe_expr.replace(uf, "fields['close']")

                # Transform AST to safely handle unknown names (like 'sector') by converting them to strings
                tree = ast.parse(safe_expr, mode="eval")
                transformer = SafeEvalTransformer(context.keys())
                tree = transformer.visit(tree)
                ast.fix_missing_locations(tree)

                # Compile and evaluate with strictly controlled builtins
                compiled_expr = compile(tree, filename="<ast>", mode="eval")
                res_matrix = eval(compiled_expr, {"__builtins__": {}}, context)
                res_matrix = _ensure_df(res_matrix)

                # Stack back to multi-index
                try:
                    res_series = res_matrix.stack(dropna=False)
                except (TypeError, ValueError):
                    res_series = res_matrix.stack()
                factor_matrices.append(res_series)

            except Exception as e:
                raise RuntimeError(
                    f"Factor computation failed for '{expr}': {e}"
                ) from e

        factor_df = pd.concat(factor_matrices, axis=1)
        factor_df.columns = self.factor_expressions
        factor_df.index.names = ["datetime", "instrument"]

        self.factor_data = self._normalize_factors(factor_df)
        self.alphacombo = self.factor_data.dot(self.weights).to_frame(
            name="alphacombo"
        )
        logger.info("Factor computation completed.")

    def compute_factors_polars(self):
        """
        Compute factors using Polars engine.
        """
        logger.info("Computing factors using Polars Engine...")
        import polars as pl

        from .polars_engine import PolarsEngine

        # 1. Prepare Polars DataFrame from raw_data
        # raw_data has index (datetime, instrument)
        pl_df = pl.from_pandas(self.raw_data.reset_index())

        # Ensure datetime is string or date for engine processing
        if pl_df["datetime"].dtype == pl.Datetime:
            pl_df = pl_df.with_columns(
                pl.col("datetime").dt.to_string("%Y-%m-%d")
            )

        # Add vwap
        if "total_turnover" in pl_df.columns and "volume" in pl_df.columns:
            pl_df = pl_df.with_columns(
                vwap=(
                    pl.col("total_turnover") / pl.col("volume").replace(0, None)
                )
            ).with_columns(
                vwap=pl.col("vwap")
                .forward_fill()
                .over("instrument")
                .fill_null(pl.col("close"))
            )

        # Sort by instrument first so time-series rolling ops work correctly
        pl_df = pl_df.sort(["instrument", "datetime"])

        engine = PolarsEngine(pl_df)
        try:
            # Use compute_all for proper two-step materialization of nested expressions
            result_df = engine.compute_all(pl_df, self.factor_expressions)
            result_df = result_df.select(
                ["datetime", "instrument"] + self.factor_expressions
            )
        except Exception as e:
            raise RuntimeError(
                f"Factor computation failed (Polars): {e}"
            ) from e

        # Convert back to Pandas for normalization and downstream
        factor_df = result_df.to_pandas()

        # Ensure datetime is back to datetime64[ns] to match label_data
        if not pd.api.types.is_datetime64_any_dtype(factor_df["datetime"]):
            factor_df["datetime"] = pd.to_datetime(factor_df["datetime"])

        factor_df = factor_df.set_index(["datetime", "instrument"]).sort_index()

        self.factor_data = self._normalize_factors(factor_df)
        self.alphacombo = self.factor_data.dot(self.weights).to_frame(
            name="alphacombo"
        )
        logger.info("Polars Factor computation completed.")

    def get_market_regime(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lookback_days: int = 45,
    ) -> str:
        """
        Fetch market data and return a detailed statistical summary for IdeaAgent.
        Args:
            start_date: Explicit start date (YYYY-MM-DD). If None, uses end_date - lookback_days.
            end_date: Explicit end date (YYYY-MM-DD). If None, uses self.test_end_date.
            lookback_days: Number of days to look back if start_date is not provided.
        """
        target_end = end_date if end_date else self.test_end_date
        if start_date:
            target_start = start_date
        else:
            target_start = (
                pd.to_datetime(target_end) - pd.Timedelta(days=lookback_days)
            ).strftime("%Y-%m-%d")

        logger.info(
            f"Generating market regime summary for {self.market} from {target_start} to {target_end}..."
        )

        try:
            df = rq.get_price(
                self.market,
                start_date=target_start,
                end_date=target_end,
                frequency="1d",
            )

            if df is None or df.empty:
                return f"Market data for {self.market} unavailable in range {target_start} to {target_end}."

            close = df["close"]
            vol = df["volume"]
            returns = close.pct_change().dropna()

            # 1. Trend Analysis
            ma20 = (
                close.rolling(20).mean().iloc[-1]
                if len(close) >= 20
                else close.mean()
            )
            ma5 = (
                close.rolling(5).mean().iloc[-1]
                if len(close) >= 5
                else close.mean()
            )
            last_close = close.iloc[-1]

            if last_close > ma20:
                trend = "Bullish (Above MA20)"
                momentum = "Strong" if ma5 > ma20 else "Weakening"
            else:
                trend = "Bearish (Below MA20)"
                momentum = "Strong" if ma5 < ma20 else "Recovering"

            # 2. Volatility & Distribution
            real_vol = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
            vol_state = (
                "High Volatility"
                if real_vol > 0.25
                else (
                    "Low Volatility" if real_vol < 0.15 else "Normal Volatility"
                )
            )

            skew = returns.skew()
            kurt = returns.kurtosis()
            dist_desc = ""
            if skew > 0.5:
                dist_desc += "Positive Skew (Right-tailed); "
            elif skew < -0.5:
                dist_desc += "Negative Skew (Left-tailed); "
            if kurt > 1:
                dist_desc += "Fat-tailed (High Kurtosis); "

            # 3. Volume & Liquidity
            v_recent = vol.tail(5).mean()
            v_baseline = vol.mean()
            vol_ratio = v_recent / v_baseline if v_baseline > 0 else 1.0
            vol_activity = (
                "Expanding"
                if vol_ratio > 1.2
                else ("Shrinking" if vol_ratio < 0.8 else "Stable")
            )

            # 4. Range & Price Action
            period_return = (close.iloc[-1] / close.iloc[0]) - 1
            max_drawdown = (close / close.cummax() - 1).min()

            summary = (
                f"=== RICEQUANT MARKET ANALYSIS ({self.market}) ===\n"
                f"Period: {target_start} to {target_end}\n"
                f"- Trend: {trend} | Momentum: {momentum}\n"
                f"- Risk: {vol_state} (Ann. Vol: {real_vol:.2%})\n"
                f"- Return Distribution: Skew={skew:.2f}, Kurt={kurt:.2f} | {dist_desc}\n"
                f"- Volume Activity: {vol_activity} (Ratio vs Period Avg: {vol_ratio:.2f})\n"
                f"- Performance: Cumulative Return: {period_return:.2%}, Max Drawdown: {max_drawdown:.2%}\n"
            )
            return summary
        except Exception as e:
            if "Quota exceeded" in str(e) or "rate limit" in str(e).lower():
                logger.warning(
                    f"RiceQuant quota exceeded during market regime fetch: {e}"
                )
                return (
                    f"=== RICEQUANT MARKET ANALYSIS ({self.market}) ===\n"
                    f"Period: {target_start} to {target_end}\n"
                    "Real-time market data unavailable (quota exceeded). Using fallback analysis.\n"
                    "- Trend: Mixed/Sideways\n"
                    "- Risk: Normal Volatility (estimated)\n"
                    "- Volume: Stable\n"
                    "- Note: Hypothesis should focus on robust, cross-cycle economic logic."
                )
            logger.error(f"Failed to generate market regime: {e}")
            return f"RiceQuant Market Insight failed for range {target_start}-{target_end}."

    def run_robustness_test(self):
        """
        Calculates a robustness score by comparing factor performance
        on original data vs noisy data.
        """
        if not hasattr(self, "ic"):
            self.run()

        # Compare on the train segment so RRE (which the research agent
        # sees) carries no holdout information.
        use_train = self.is_ic is not None
        orig_ic = self.is_ic if use_train else self.ic

        # Create a noisy clone
        noisy_eval = RiceQuantEval(
            factor_expressions=self.factor_expressions,
            weights=self.weights,
            test_start_date=self.test_start_date,
            test_end_date=self.test_end_date,
            market=self.market,
            daily_normalize=self.daily_normalize,
            engine=self.engine,
            noise_level=0.05,  # 5% noise injection
            valid_split_date=self.valid_split_date,
            oos_split_date=self.oos_split_date,
        )
        noisy_eval.run()
        noisy_ic = (
            noisy_eval.is_ic
            if use_train and noisy_eval.is_ic is not None
            else noisy_eval.ic
        )

        # Robustness Ratio (RRE): 1.0 means no decay, lower means sensitive to noise
        if abs(orig_ic) < 1e-6:
            self.rre = 0.0
        else:
            # Magnitude of IC retention. The ratio is positive only when the
            # noisy IC keeps the original sign, so negative-IC factors (traded
            # inverted by the manager) are scored the same way.
            self.rre = max(0.0, min(1.0, noisy_ic / orig_ic))

        logger.info(
            f"Robustness Test - Original IC: {orig_ic}, Noisy IC: {noisy_ic}, RRE: {self.rre:.4f}"
        )

    # --- Metrics & Summary ---
    def calculate_pnl(self, all_data):
        """Calculate PnL metrics with turnover tracking and transaction costs."""
        if all_data.empty:
            self.daily_returns_series = pd.Series(dtype=float)
            self.gross_daily_returns_series = pd.Series(dtype=float)
            self.turnover_series = pd.Series(dtype=float)
            self.mean_turnover = 0.0
            self.turnover = 0.0
            self.sharpe = 0.0
            self.gross_sharpe = 0.0
            self.max_dd = 0.0
            self.gross_max_dd = 0.0
            return pd.Series(dtype=float)

        # Unstack factor and label into matrices (datetime x instrument)
        factor_df = (
            all_data["factor"]
            .unstack(level="instrument")
            .sort_index()
            .fillna(0.0)
        )
        label_df = (
            all_data["label"]
            .unstack(level="instrument")
            .sort_index()
            .fillna(0.0)
        )

        # Long-short portfolio weights on day t:
        # weights = factor / (factor.abs().sum() + 1e-8)
        denom = factor_df.abs().sum(axis=1) + 1e-8
        weights_df = factor_df.div(denom, axis=0).fillna(0.0)

        # Gross daily returns
        gross_daily_ret = (weights_df * label_df).sum(axis=1)

        # Daily turnover = sum(|w_t - w_{t-1}|) / 2
        if len(weights_df) > 0:
            turnover_series = weights_df.diff().abs().sum(axis=1) / 2.0
            turnover_series.iloc[0] = 0.0
        else:
            turnover_series = pd.Series(dtype=float, index=weights_df.index)

        # Transaction cost and market impact drag
        daily_drag, _ = self.impact_model.compute_drag(
            weights_df=weights_df,
            raw_data=getattr(self, "raw_data", None),
            label_df=label_df,
        )
        net_daily_ret = gross_daily_ret - daily_drag

        self.daily_returns_series = net_daily_ret
        self.gross_daily_returns_series = gross_daily_ret
        self.turnover_series = turnover_series
        self.mean_turnover = (
            float(turnover_series.mean()) if not turnover_series.empty else 0.0
        )
        self.turnover = self.mean_turnover
        total_to = float(turnover_series.sum())
        total_drag = float(daily_drag.sum())
        self.total_cost_drag = total_drag
        if total_to > 1e-8:
            self.effective_cost_bps = float((total_drag / total_to) * 10000.0)
        else:
            self.effective_cost_bps = float(self.cost_bps)

        if len(gross_daily_ret) >= 2:
            gross_std = gross_daily_ret.std()
            self.gross_sharpe = float(
                (gross_daily_ret.mean() / (gross_std + 1e-8))
                * np.sqrt(TRADING_DAYS_PER_YEAR)
            )
            gross_cum = (1 + gross_daily_ret).cumprod()
            g_dd = (gross_cum / gross_cum.cummax() - 1).min()
            self.gross_max_dd = 0.0 if np.isnan(g_dd) else float(g_dd)

            net_std = net_daily_ret.std()
            self.sharpe = float(
                (net_daily_ret.mean() / (net_std + 1e-8))
                * np.sqrt(TRADING_DAYS_PER_YEAR)
            )
            net_cum = (1 + net_daily_ret).cumprod()
            n_dd = (net_cum / net_cum.cummax() - 1).min()
            self.max_dd = 0.0 if np.isnan(n_dd) else float(n_dd)
        else:
            self.gross_sharpe = 0.0
            self.gross_max_dd = 0.0
            self.sharpe = 0.0
            self.max_dd = 0.0

        return net_daily_ret

    def _compute_segment_metrics(
        self,
        ic_series,
        rank_ic_series,
        daily_ret,
        turnover_series=None,
        gross_daily_ret=None,
    ):
        """Split metrics into train [start, valid), valid [valid, oos) and
        test [oos, end]. Empty segments stay ``None``."""
        to_s = (
            turnover_series
            if turnover_series is not None
            else getattr(self, "turnover_series", None)
        )
        gross_s = (
            gross_daily_ret
            if gross_daily_ret is not None
            else getattr(self, "gross_daily_returns_series", None)
        )

        train = segment_stats(
            ic_series,
            rank_ic_series,
            daily_ret,
            None,
            self.valid_split_date,
            turnover_series=to_s,
            gross_daily_returns=gross_s,
        )
        valid = segment_stats(
            ic_series,
            rank_ic_series,
            daily_ret,
            self.valid_split_date,
            self.oos_split_date,
            turnover_series=to_s,
            gross_daily_returns=gross_s,
        )
        test = segment_stats(
            ic_series,
            rank_ic_series,
            daily_ret,
            self.oos_split_date,
            None,
            turnover_series=to_s,
            gross_daily_returns=gross_s,
        )
        self.segment_metrics = {"train": train, "valid": valid, "test": test}

        def _get(seg, key):
            return seg.get(key) if seg else None

        self.is_ic = _get(train, "ic")
        self.is_rankic = _get(train, "rank_ic")
        self.is_sharpe = _get(train, "sharpe")
        self.is_gross_sharpe = _get(train, "gross_sharpe")
        self.is_max_dd = _get(train, "max_dd")
        self.is_turnover = _get(train, "turnover")

        self.val_ic = _get(valid, "ic")
        self.val_rankic = _get(valid, "rank_ic")
        self.val_sharpe = _get(valid, "sharpe")
        self.val_gross_sharpe = _get(valid, "gross_sharpe")
        self.val_turnover = _get(valid, "turnover")

        self.oos_ic = _get(test, "ic")
        self.oos_rankic = _get(test, "rank_ic")
        self.oos_sharpe = _get(test, "sharpe")
        self.oos_gross_sharpe = _get(test, "gross_sharpe")
        self.oos_max_dd = _get(test, "max_dd")
        self.oos_turnover = _get(test, "turnover")

    # --- Backtest Execution ---
    def run(self):
        self.fetch_data()
        self.compute_factors()

        if self.alphacombo.replace([np.inf, -np.inf], np.nan).dropna().empty:
            raise ValueError(
                "Factor computation produced no valid non-NaN/Inf values."
            )

        if self.label_data.dropna().empty:
            raise ValueError(
                "Label data (returns) is entirely NaN — check test dates and market data availability."
            )

        # Ensure index names match before joining
        self.alphacombo.index.names = ["datetime", "instrument"]
        self.label_data.index.names = ["datetime", "instrument"]

        all_data = self.alphacombo.join(self.label_data, how="inner")
        all_data.columns = ["factor", "label"]
        all_data = all_data.replace([np.inf, -np.inf], np.nan).dropna()

        if all_data.empty:
            raise ValueError("Combined factor and label data is empty.")

        # Core Metrics (IC Series)
        ic_series = (
            all_data.groupby(level="datetime")
            .apply(lambda x: x["factor"].corr(x["label"]))
            .fillna(0)
        )
        rank_ic_series = self._daily_rank_ic(all_data).fillna(0)

        self.ic = round(float(ic_series.mean()), 4)
        self.rankic = round(float(rank_ic_series.mean()), 4)

        # PnL Metrics
        daily_ret = self.calculate_pnl(all_data)
        self.daily_returns = {
            str(k.date() if hasattr(k, "date") else k): float(v)
            for k, v in daily_ret.fillna(0).items()
        }
        self.gross_daily_returns = {
            str(k.date() if hasattr(k, "date") else k): float(v)
            for k, v in self.gross_daily_returns_series.fillna(0).items()
        }
        self.turnover_daily = {
            str(k.date() if hasattr(k, "date") else k): float(v)
            for k, v in self.turnover_series.fillna(0).items()
        }

        self._compute_segment_metrics(ic_series, rank_ic_series, daily_ret)

        # Layered Analysis & Plots
        try:
            layer_ret = self.calculate_layered_returns(all_data)
            self.plot_paths = self.generate_plots(
                daily_ret, layer_ret, self.factor_expressions[0]
            )
        except Exception as e:
            logger.warning(f"Failed to generate backtest plots: {e}")
            self.plot_paths = {}

        logger.info(
            f"RiceQuant Evaluation - IC(full): {self.ic}, IC(train): {self.is_ic}, "
            f"IC(valid): {self.val_ic}, IC(oos): {self.oos_ic}, "
            f"Sharpe(full): {self.sharpe:.2f}, Gross Sharpe: {self.gross_sharpe:.2f}, "
            f"Turnover: {self.mean_turnover:.4f}"
        )

    # --- Expression Parsing ---
    @staticmethod
    def dry_run(expr: str) -> tuple:
        """
        Mock execution of a factor expression using dummy 10x10 matrices.
        Returns (is_success, error_message).
        """
        try:
            validate_factor_expression(expr)
            # 1. Create dummy 10x10 environment
            dates = pd.date_range("2020-01-01", periods=10)
            symbols = [f"S{i:02d}" for i in range(10)]

            def make_dummy():
                return pd.DataFrame(
                    np.random.randn(10, 10), index=dates, columns=symbols
                )

            dummy_fields = {
                "open": make_dummy() + 10,
                "high": make_dummy() + 15,
                "low": make_dummy() + 5,
                "close": make_dummy() + 10,
                "volume": make_dummy() * 1000,
                "total_turnover": make_dummy() * 10000,
                "vwap": make_dummy() + 10,
            }

            def _get_n(n):
                if isinstance(n, (pd.Series, pd.DataFrame)):
                    try:
                        val = n.iloc[-1]
                        if isinstance(val, pd.Series):
                            val = val.iloc[-1]
                        return int(val)
                    except (TypeError, ValueError, AttributeError, IndexError):
                        return 20
                try:
                    return int(float(n))
                except (TypeError, ValueError):
                    return 20

            def If(cond, a, b):
                if isinstance(a, (int, float)):
                    a = pd.DataFrame(a, index=cond.index, columns=cond.columns)
                if isinstance(b, (int, float)):
                    b = pd.DataFrame(b, index=cond.index, columns=cond.columns)
                return a.where(cond, b)

            # Capture reference index/columns for scalar → DataFrame broadcast
            _ref_field = dummy_fields["close"]

            def _ensure_df(x):
                if isinstance(x, (int, float, np.integer, np.floating)):
                    return pd.DataFrame(
                        float(x),
                        index=_ref_field.index,
                        columns=_ref_field.columns,
                    )
                return x

            # Robust variadic operators
            def And(*args):
                res = args[0]
                for a in args[1:]:
                    res = res & a
                return res

            def Or(*args):
                res = args[0]
                for a in args[1:]:
                    res = res | a
                return res

            def _dry_ts_rank(df, n=20):
                df = _ensure_df(df)
                nn = max(1, _get_n(n))
                if nn == 1:
                    return pd.DataFrame(0.5, index=df.index, columns=df.columns)

                def _ts_rank_row(x):
                    if len(x) < nn:
                        return np.nan
                    last = x.iloc[-1]
                    if pd.isna(last):
                        return np.nan
                    valid = x.dropna()
                    if len(valid) == 0:
                        return np.nan
                    return float((valid <= last).sum()) / len(valid)

                return df.rolling(nn, min_periods=1).apply(
                    _ts_rank_row, raw=False
                )

            def _dry_ts_argmax(df, n=20):
                df = _ensure_df(df)
                nn = max(1, _get_n(n))

                def _row(x):
                    if len(x) < nn:
                        return np.nan
                    return (
                        float(np.nanargmax(x))
                        if not np.all(np.isnan(x))
                        else np.nan
                    )

                return df.rolling(nn, min_periods=1).apply(_row, raw=True)

            def _dry_ts_argmin(df, n=20):
                df = _ensure_df(df)
                nn = max(1, _get_n(n))

                def _row(x):
                    if len(x) < nn:
                        return np.nan
                    return (
                        float(np.nanargmin(x))
                        if not np.all(np.isnan(x))
                        else np.nan
                    )

                return df.rolling(nn, min_periods=1).apply(_row, raw=True)

            def _dry_wma(df, n=20):
                df = _ensure_df(df)
                nn = max(1, _get_n(n))
                weights = np.arange(1, nn + 1, dtype=float)
                weights /= weights.sum()
                return df.rolling(nn, min_periods=1).apply(
                    lambda x: (
                        np.dot(x[-len(weights) :], weights[-len(x) :])
                        / weights[-len(x) :].sum()
                    ),
                    raw=True,
                )

            context = {
                "fields": dummy_fields,
                "np": np,
                "pd": pd,
                "Rank": lambda df, *args: df.rank(axis=1, pct=True),
                "CSRank": lambda df, *args: df.rank(axis=1, pct=True),
                "CSZScore": lambda df, *args: df.sub(
                    df.mean(axis=1), axis=0
                ).div(df.std(axis=1).replace(0, 1), axis=0),
                "Mean": lambda df, n=20: df.rolling(max(1, _get_n(n))).mean(),
                "Std": lambda df, n=20: df.rolling(max(1, _get_n(n))).std(),
                "Median": lambda df, n=20: df.rolling(
                    max(1, _get_n(n))
                ).median(),
                "EMA": lambda df, n=20: df.ewm(span=max(1, _get_n(n))).mean(),
                "Abs": np.abs,
                "Log": lambda df: np.log(_ensure_df(df).replace(0, np.nan)),
                "Sum": lambda df, n=20: df.rolling(max(1, _get_n(n))).sum(),
                "Ref": lambda df, n=1: df.shift(_get_n(n)),
                "Delta": lambda df, n=1: df.diff(_get_n(n)),
                "Corr": lambda df1, df2, n=20: df1.rolling(
                    max(1, _get_n(n))
                ).corr(df2),
                "Correlation": lambda df1, df2, n=20: df1.rolling(
                    max(1, _get_n(n))
                ).corr(df2),
                "If": If,
                "And": And,
                "Or": Or,
                "Greater": lambda a, b: a > b,
                "Less": lambda a, b: a < b,
                "Ts_Rank": _dry_ts_rank,
                "Ts_Percentile": lambda df, n=20, p=50: df.rolling(
                    max(1, _get_n(n))
                ).apply(lambda x: np.percentile(x, float(p))),
                "Winsorize": lambda df, pct=0.05: _ensure_df(df).apply(
                    lambda x: x.clip(
                        lower=x.quantile(float(pct)),
                        upper=x.quantile(1 - float(pct)),
                    ),
                    axis=1,
                ),
                "Sign": np.sign,
                "Sqrt": lambda df: np.sqrt(_ensure_df(df).clip(lower=0)),
                "Add": lambda a, b: a + b,
                "Sub": lambda a, b: a - b,
                "Mul": lambda a, b: a * b,
                "Div": lambda a, b: a / b,
                "Mult": lambda a, b: a * b,
                "Divi": lambda a, b: a / b,
                "Plus": lambda a, b: a + b,
                "Minus": lambda a, b: a - b,
                "Pow": lambda a, b: a**b,
                "Neg": lambda a: -a,
                "Inv": lambda a: 1.0 / (a + 1e-9),
                "Max": lambda a, b: np.maximum(a, b),
                "Min": lambda a, b: np.minimum(a, b),
                "Divide": lambda a, b: a / b,
                "Multiply": lambda a, b: a * b,
                "Subtract": lambda a, b: a - b,
                "Negate": lambda a: -a,
                "GreaterEqual": lambda a, b: a >= b,
                "LessEqual": lambda a, b: a <= b,
                "Equal": lambda a, b: a == b,
                "NotEqual": lambda a, b: a != b,
                "Not": lambda a: ~a,
                "Ts_Max": lambda df, n: df.rolling(max(1, _get_n(n))).max(),
                "Ts_Min": lambda df, n: df.rolling(max(1, _get_n(n))).min(),
                "Percentile": lambda df, p=50: df.rank(axis=1, pct=True),
                "GroupNeutral": lambda df: df.sub(df.mean(axis=1), axis=0),
                "Scale": lambda df, a=1: (
                    df.div(df.abs().sum(axis=1), axis=0) * a
                ),
                "Cov": lambda df1, df2, n=20: df1.rolling(
                    max(1, _get_n(n))
                ).cov(df2),
                "Ts_ArgMax": _dry_ts_argmax,
                "Ts_ArgMin": _dry_ts_argmin,
                "Clip": lambda df, lower, upper: _ensure_df(df).clip(
                    lower=lower, upper=upper
                ),
                "Count": lambda df=None, n=20: (
                    pd.DataFrame(
                        _ref_field.shape[1],
                        index=_ref_field.index,
                        columns=_ref_field.columns,
                    )
                    if df is None
                    else _ensure_df(df).rolling(max(1, _get_n(n))).count()
                ),
                "Exp": lambda df: np.exp(_ensure_df(df).clip(upper=500)),
                "Ceil": lambda df: np.ceil(df),
                "Floor": lambda df: np.floor(df),
                "WMA": _dry_wma,
                "Const": lambda x: x,
            }

            safe_expr = expr
            for col in dummy_fields.keys():
                safe_expr = safe_expr.replace(f"${col}", f"fields['{col}']")

            tree = ast.parse(safe_expr, mode="eval")
            transformer = SafeEvalTransformer(context.keys())
            tree = transformer.visit(tree)
            ast.fix_missing_locations(tree)
            compiled_expr = compile(tree, filename="<ast>", mode="eval")
            eval(compiled_expr, {"__builtins__": {}}, context)

            return True, "OK"
        except Exception as e:
            return False, str(e)

    # --- Metrics & Summary ---
    def summary(self):
        logger.info(f"RiceQuant IC: {self.ic}")
        logger.info(f"RiceQuant RankIC: {self.rankic}")
        logger.info(f"RiceQuant Net Sharpe: {self.sharpe:.2f}")
        logger.info(f"RiceQuant Gross Sharpe: {self.gross_sharpe:.2f}")
        logger.info(f"RiceQuant Mean Turnover: {self.mean_turnover:.4f}")

import os
import numpy as np
import pandas as pd
import rqdatac as rq
from typing import List, Optional
from loguru import logger
from dotenv import load_dotenv
import ast

# Load environment variables
load_dotenv()

class SafeEvalTransformer(ast.NodeTransformer):
    def __init__(self, known_names):
        self.known_names = set(known_names)
        
    def visit_Call(self, node):
        # Recursively visit arguments first
        node.args = [self.visit(arg) for arg in node.args]
        node.keywords = [self.visit(kw) for kw in node.keywords]
        
        # If the function name itself is unknown, we handle it
        if isinstance(node.func, ast.Name) and node.func.id not in self.known_names:
            logger.warning(f"Function '{node.func.id}' is unknown. It might fail or needs a fallback.")
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
    if df.empty: return df
    means = df.mean(axis=1)
    stds  = df.std(axis=1).replace(0, np.nan)
    # If std is NaN (all same values), the result after sub will be 0 anyway. 
    # But we need to handle the div by std carefully.
    res = df.sub(means, axis=0)
    # Only divide where std is not NaN and > 0
    res = res.div(stds, axis=0).fillna(0)
    return res

class RiceQuantEval:
    """
    RiceQuant-compatible evaluator that uses rqdatac for data fetching.
    """
    def __init__(
        self,
        factor_expressions: List[str],
        weights: Optional[List[float]] = None,
        train_start_date: str = "2010-01-01",
        train_end_date: str = "2016-12-31",
        test_start_date: str = "2017-01-01",
        test_end_date: str = "2020-10-31",
        market: str = "000300.XSHG", # CSI 300
        daily_normalize: bool = True
    ):
        self.factor_expressions = factor_expressions
        self.weights = weights if weights else [1.0] * len(factor_expressions)
        self.train_start_date = train_start_date
        self.train_end_date = train_end_date
        self.test_start_date = test_start_date
        self.test_end_date = test_end_date
        self.market = market
        self.daily_normalize = daily_normalize
        
        self._init_rq()
        
    def _init_rq(self):
        # Skip check, just try to init
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
                return
            except Exception as e:
                logger.warning(f"RiceQuant Token Auth failed: {e}. Trying Password fallback...")

        # 2. Try User/Pass Mode (Confirmed working in test_rq.py)
        if username and password and "your-" not in username.lower():
            logger.info(f"Attempting RiceQuant Password Auth (User: {username})...")
            try:
                rq.init(username=username.strip(), password=password.strip())
                logger.info("RiceQuant Password Auth Successful!")
                return
            except Exception as e:
                logger.error(f"RiceQuant Password Auth failed: {e}")
                raise
        
        raise ValueError("RiceQuant Auth Failed: No valid credentials found or accepted.")

    def fetch_data(self):
        """Fetch price data from RiceQuant."""
        logger.info(f"Fetching data for {self.market} from {self.test_start_date} to {self.test_end_date}")
        
        # Get instruments
        instruments = rq.index_components(self.market, self.test_end_date)
        
        # Fetch OHLCV + Turnover
        fields = ["close", "open", "high", "low", "volume", "total_turnover"]
        df = rq.get_price(
            instruments,
            start_date=self.test_start_date,
            end_date=self.test_end_date,
            frequency="1d",
            fields=fields
        )
        
        # rqdatac returns a multi-index DataFrame (order_book_id, date)
        # We want to match qlib's (datetime, instrument)
        df.index.names = ["instrument", "datetime"]
        df = df.reorder_levels(["datetime", "instrument"]).sort_index()
        
        self.raw_data = df
        
        # Calculate label (next day return)
        # qlib's label: Ref($close, -1)/$close - 1
        # In Pandas: df['close'].groupby('instrument').shift(-1) / df['close'] - 1
        close = df['close'].unstack()
        returns = close.shift(-1) / close - 1
        self.label_data = returns.stack().to_frame(name="label")
        
        logger.info("Data fetching done.")

    def compute_factors(self):
        """
        Compute factors using unstacked matrix operations for Qlib-style expressions.
        """
        logger.info("Computing factors using Matrix Engine...")
        
        # 1. Unstack fields into matrices (Index: datetime, Columns: instrument)
        fields = {}
        for col in self.raw_data.columns:
            fields[col] = self.raw_data[col].unstack()
        
        # Add vwap: total_turnover / volume
        if 'total_turnover' in fields and 'volume' in fields:
            fields['vwap'] = fields['total_turnover'] / fields['volume'].replace(0, np.nan)
            fields['vwap'] = fields['vwap'].ffill().fillna(fields['close'])

        # Define local helper functions for the eval engine
        def Rank(df):
            return df.rank(axis=1, pct=True)
        
        def Mean(df, n=None):
            if n is None: 
                res = df.mean(axis=1)
                return pd.DataFrame(np.repeat(res.values[:, np.newaxis], df.shape[1], axis=1), index=df.index, columns=df.columns)
            return df.rolling(max(1, _get_n(n))).mean()
        
        def Std(df, n=None):
            if n is None: 
                res = df.std(axis=1)
                return pd.DataFrame(np.repeat(res.values[:, np.newaxis], df.shape[1], axis=1), index=df.index, columns=df.columns)
            return df.rolling(max(1, _get_n(n))).std()
        
        def Median(df, n=None):
            if n is None: 
                res = df.median(axis=1)
                return pd.DataFrame(np.repeat(res.values[:, np.newaxis], df.shape[1], axis=1), index=df.index, columns=df.columns)
            return df.rolling(max(1, _get_n(n))).median()

        def EMA(df, n):
            return df.ewm(span=max(1, _get_n(n))).mean()

        def Abs(df):
            return np.abs(df)
        
        def _get_n(n):
            if isinstance(n, (pd.Series, pd.DataFrame)):
                try:
                    val = n.iloc[-1]
                    if isinstance(val, pd.Series): val = val.iloc[-1]
                    return int(val)
                except:
                    return 20 # Fallback
            try:
                return int(float(n))
            except:
                return 20

        def Ref(df, n):
            return df.shift(_get_n(n))
        
        def Log(df):
            return np.log(df.replace(0, np.nan))
        
        def Sum(df, n):
            return df.rolling(max(1, _get_n(n))).sum()

        def If(cond, a, b):
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

        def And(a, b):
            return a & b
            
        def Or(a, b):
            return a | b

        def Delta(df, n):
            return df.diff(_get_n(n))

        def Corr(df1, df2, n):
            return df1.rolling(max(1, _get_n(n))).corr(df2)

        def Cov(df1, df2, n):
            return df1.rolling(max(1, _get_n(n))).cov(df2)

        def Ts_Rank(df, n):
            nn = max(1, _get_n(n))
            if nn == 1: return pd.DataFrame(0.5, index=df.index, columns=df.columns)
            return df.rolling(nn).apply(lambda x: x.rank(pct=True).iloc[-1], raw=False)

        def CSRank(df):
            return df.rank(axis=1, pct=True)

        def Percentile(df, p):
            return df.rank(axis=1, pct=True)

        def Clip(df, lower, upper):
            return df.clip(lower=lower, upper=upper, axis=0 if isinstance(lower, pd.Series) else None)

        def CSZScore(df):
            return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1).replace(0, 1), axis=0)

        def Winsorize(df, pct=0.05):
            # Simple winsorization on cross-section
            return df.apply(lambda x: x.clip(lower=x.quantile(float(pct)), upper=x.quantile(1-float(pct))), axis=1)

        def GroupNeutral(df, group='sector'):
            # Simplified neutral: just subtract cross-sectional mean
            return df.sub(df.mean(axis=1), axis=0)

        def Count():
            c = fields['close'].shape[1]
            return pd.DataFrame(c, index=fields['close'].index, columns=fields['close'].columns)

        def Sign(df):
            return np.sign(df)

        def Sqrt(df):
            return np.sqrt(df.clip(lower=0))

        def Ts_ArgMax(df, n):
            return df.rolling(max(1, _get_n(n))).apply(lambda x: float(np.argmax(x)), raw=True)

        def Ts_ArgMin(df, n):
            return df.rolling(max(1, _get_n(n))).apply(lambda x: float(np.argmin(x)), raw=True)

        def Ts_Percentile(df, n, p=50):
            # Rolling percentile VALUE (p-th percentile of last n days)
            # Default p=50 (median) if not provided
            return df.rolling(max(1, _get_n(n))).apply(lambda x: np.percentile(x, float(p)), raw=True)

        # Basic operator aliases for LLM compatibility
        def Add(a, b): return a + b
        def Sub(a, b): return a - b
        def Mul(a, b): return a * b
        def Div(a, b): return a / b
        def Pow(a, b): return a ** b
        def Neg(a): return -a
        def Inv(a): return 1.0 / a
        def Max(a, b): return np.maximum(a, b)
        def Min(a, b): return np.minimum(a, b)

        # Build context for eval
        context = {
            "fields": fields, "np": np, "pd": pd,
            "Rank": Rank, "Mean": Mean, "Ref": Ref, "Abs": Abs, 
            "Std": Std, "Log": Log, "Sum": Sum, "If": If, 
            "Greater": Greater, "Less": Less, "And": And, "Or": Or,
            "Delta": Delta, "Corr": Corr, "Cov": Cov, "Ts_Rank": Ts_Rank,
            "Median": Median, "EMA": EMA, "CSRank": CSRank, "CSZScore": CSZScore,
            "Winsorize": Winsorize, "GroupNeutral": GroupNeutral,
            "Percentile": Percentile, "Clip": Clip,
            "Count": Count, "Correlation": Corr, "Sign": Sign, "Sqrt": Sqrt,
            "Ts_ArgMax": Ts_ArgMax, "Ts_ArgMin": Ts_ArgMin, "Ts_Percentile": Ts_Percentile,
            "Add": Add, "Sub": Sub, "Mul": Mul, "Div": Div, "Pow": Pow, 
            "Neg": Neg, "Inv": Inv, "Max": Max, "Min": Min
        }

        factor_matrices = []

        for expr in self.factor_expressions:
            try:
                # Prepare expression for Python eval
                safe_expr = expr
                # Handle standard fields
                for col in fields.keys():
                    safe_expr = safe_expr.replace(f"${col}", f"fields['{col}']")

                # Handle unknown $fields by falling back to closest logical values
                if "$" in safe_expr:
                    import re
                    unknown_fields = re.findall(r'\$\w+', safe_expr)
                    for uf in unknown_fields:
                        logger.warning(f"Field {uf} not found in database. Falling back to default values.")
                        if 'vol' in uf.lower():
                            safe_expr = safe_expr.replace(uf, "fields['volume']")
                        elif 'share' in uf.lower():
                            safe_expr = safe_expr.replace(uf, "1.0") # Assume unit shares
                        else:
                            safe_expr = safe_expr.replace(uf, "fields['close']")

                # Transform AST to safely handle unknown names (like 'sector') by converting them to strings
                tree = ast.parse(safe_expr, mode='eval')
                transformer = SafeEvalTransformer(context.keys())
                tree = transformer.visit(tree)
                ast.fix_missing_locations(tree)
                
                # Compile and evaluate
                compiled_expr = compile(tree, filename="<ast>", mode="eval")
                res_matrix = eval(compiled_expr, context)
                
                # Stack back to multi-index
                res_series = res_matrix.stack(dropna=False)
                factor_matrices.append(res_series)
                
            except Exception as e:
                logger.error(f"Failed to evaluate factor {expr}: {e}")
                # Fallback to zeros
                factor_matrices.append(pd.Series(0, index=self.raw_data.index))
        
        # Combine and normalize
        factor_df = pd.concat(factor_matrices, axis=1)
        factor_df.columns = self.factor_expressions
        factor_df.index.names = ["datetime", "instrument"]
        
        if self.daily_normalize:
            factor_df = (
                factor_df
                .groupby(level="datetime", group_keys=False)
                .apply(zscore)
                .replace([np.inf, -np.inf], np.nan)
                .replace(np.nan, 0)
            )
        
        self.factor_data = factor_df
        self.alphacombo = self.factor_data.dot(self.weights).to_frame(name="alphacombo")
        logger.info("Factor computation completed.")

    def get_market_regime(self, start_date: Optional[str] = None, end_date: Optional[str] = None, lookback_days: int = 45) -> str:
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
            target_start = (pd.to_datetime(target_end) - pd.Timedelta(days=lookback_days)).strftime("%Y-%m-%d")

        logger.info(f"Generating market regime summary for {self.market} from {target_start} to {target_end}...")
        
        try:
            df = rq.get_price(self.market, start_date=target_start, end_date=target_end, frequency="1d")
            
            if df is None or df.empty:
                return f"Market data for {self.market} unavailable in range {target_start} to {target_end}."
            
            close = df['close']
            vol = df['volume']
            returns = close.pct_change().dropna()
            
            # 1. Trend Analysis
            ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else close.mean()
            ma5 = close.rolling(5).mean().iloc[-1] if len(close) >= 5 else close.mean()
            last_close = close.iloc[-1]
            
            if last_close > ma20:
                trend = "Bullish (Above MA20)"
                momentum = "Strong" if ma5 > ma20 else "Weakening"
            else:
                trend = "Bearish (Below MA20)"
                momentum = "Strong" if ma5 < ma20 else "Recovering"
            
            # 2. Volatility & Distribution
            real_vol = returns.std() * np.sqrt(252)
            vol_state = "High Volatility" if real_vol > 0.25 else ("Low Volatility" if real_vol < 0.15 else "Normal Volatility")
            
            skew = returns.skew()
            kurt = returns.kurtosis()
            dist_desc = ""
            if skew > 0.5: dist_desc += "Positive Skew (Right-tailed); "
            elif skew < -0.5: dist_desc += "Negative Skew (Left-tailed); "
            if kurt > 1: dist_desc += "Fat-tailed (High Kurtosis); "

            # 3. Volume & Liquidity
            v_recent = vol.tail(5).mean()
            v_baseline = vol.mean()
            vol_ratio = v_recent / v_baseline if v_baseline > 0 else 1.0
            vol_activity = "Expanding" if vol_ratio > 1.2 else ("Shrinking" if vol_ratio < 0.8 else "Stable")
            
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
            logger.error(f"Failed to generate market regime: {e}")
            return f"RiceQuant Market Insight failed for range {target_start}-{target_end}."
        except Exception as e:
            logger.error(f"Failed to generate market regime: {e}")
            return "RiceQuant Market Insight failed."

    def run(self):
        self.fetch_data()
        self.compute_factors()
        
        # Join with label
        all_data = self.alphacombo.join(self.label_data, how="inner")
        all_data.columns = ["factor", "label"]
        
        # Clean inf and nan in combined data
        all_data = all_data.replace([np.inf, -np.inf], np.nan).dropna()
        
        if all_data.empty:
            logger.warning("All data points were NaN or Inf after factor computation.")
            self.ic = 0.0
            self.rankic = 0.0
            self.daily_returns = {}
            return

        # IC
        ic_series = all_data.groupby(level="datetime").apply(
            lambda x: x["factor"].corr(x["label"])
        )
        # Rank IC
        rank_ic_series = all_data.groupby(level="datetime").apply(
            lambda x: x["factor"].rank().corr(x["label"].rank())
        )
        
        # Fill NaN in series with 0 to prevent final NaN
        self.ic = round(float(ic_series.fillna(0).mean()), 4)
        self.rankic = round(float(rank_ic_series.fillna(0).mean()), 4)
        
        # Calculate daily factor returns (long-short portfolio based on z-scored factor)
        # We assume factor values are portfolio weights, scaled to 1.0 gross leverage
        daily_ret_series = all_data.groupby(level="datetime").apply(
            lambda x: (x["factor"] * x["label"]).sum() / (x["factor"].abs().sum() + 1e-8)
        )
        # Convert datetime index to string keys for JSON serialization in State
        self.daily_returns = {str(k.date() if hasattr(k, 'date') else k): float(v) for k, v in daily_ret_series.fillna(0).items()}
        
        logger.info(f"RiceQuant Evaluation - IC: {self.ic}, RankIC: {self.rankic}")

    def summary(self):
        print(f"RiceQuant IC: {self.ic}")
        print(f"RiceQuant RankIC: {self.rankic}")

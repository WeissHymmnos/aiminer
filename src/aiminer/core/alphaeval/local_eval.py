from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from aiminer.core.alphaeval.rq_eval import RiceQuantEval
from aiminer.core.constants import TRADING_DAYS_PER_YEAR
from aiminer.core.local_data import load_local_ohlcv, resolve_local_profile_path


class LocalDataEval(RiceQuantEval):
    def __init__(
        self,
        factor_expressions: List[str],
        weights: Optional[List[float]] = None,
        test_start_date: str = "2018-01-01",
        test_end_date: str = "2025-12-31",
        market: str = "LOCAL",
        daily_normalize: bool = True,
        engine: str = "pandas",
        noise_level: float = 0.0,
        output_dir: str = "results/reports",
        *,
        local_data_path: str,
        local_data_layout: str = "auto",
        market_profile: str = "cn_stock",
        market_profiles: list[str] | None = None,
        market_mode: str = "single",
    ):
        self.local_data_path = local_data_path
        self.local_data_layout = local_data_layout
        self.market_profile = market_profile
        self.market_profiles = market_profiles or [market_profile]
        self.market_mode = market_mode
        super().__init__(
            factor_expressions=factor_expressions,
            weights=weights,
            test_start_date=test_start_date,
            test_end_date=test_end_date,
            market=market,
            daily_normalize=daily_normalize,
            engine=engine,
            noise_level=noise_level,
            output_dir=output_dir,
            skip_auth=True,
        )

    def _load_profile_frame(self, profile: str, *, prefix_instrument: bool) -> pd.DataFrame:
        data_path = resolve_local_profile_path(self.local_data_path, profile)
        return load_local_ohlcv(
            data_path,
            market_profile=profile,
            layout=self.local_data_layout,
            start_date=self.test_start_date,
            end_date=self.test_end_date,
            instrument_prefix=f"{profile}::" if prefix_instrument else None,
        )

    def fetch_data(self):
        logger.info(
            f"Loading local data for {self.market_mode} mode from {self.local_data_path}"
        )

        prefix_instruments = self.market_mode in {"mixed", "batch"} and len(self.market_profiles) > 1
        frames = [self._load_profile_frame(profile, prefix_instrument=prefix_instruments) for profile in self.market_profiles]
        df = pd.concat(frames).sort_index()

        if self.noise_level > 0:
            logger.info(
                f"Injecting Gaussian noise (level={self.noise_level}) into local data."
            )
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    std = float(df[col].std() or 0.0)
                    if std <= 0:
                        continue
                    noise = np.random.normal(0, std * self.noise_level, size=len(df))
                    df[col] = df[col].astype(float) + noise

        self.raw_data = df[["close", "open", "high", "low", "volume", "total_turnover"]].copy()

        df_sorted = self.raw_data.sort_index(level=["instrument", "datetime"])
        label_s = (
            df_sorted.groupby(level="instrument", group_keys=False)["close"]
            .apply(lambda x: x.shift(-1) / x - 1)
        )
        self.label_data = (
            label_s.to_frame(name="label")
            .reorder_levels(["datetime", "instrument"])
            .sort_index()
        )

    def run_robustness_test(self):
        """Local data runs should not fall back to RiceQuant network robustness."""
        if not hasattr(self, "ic"):
            self.run()
        self.rre = None
        logger.info(
            "Skipping RiceQuant robustness test for LocalDataEval; preserving local main metrics."
        )

    def get_market_regime(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lookback_days: int = 45,
    ) -> str:
        target_end = end_date if end_date else self.test_end_date
        target_start = (
            start_date
            if start_date
            else (pd.to_datetime(target_end) - pd.Timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        )

        panel = pd.concat(
            [
                self._load_profile_frame(
                    profile,
                    prefix_instrument=self.market_mode in {"mixed", "batch"} and len(self.market_profiles) > 1,
                )
                for profile in self.market_profiles
            ]
        )
        panel = panel.loc[
            (panel.index.get_level_values("datetime") >= pd.Timestamp(target_start))
            & (panel.index.get_level_values("datetime") <= pd.Timestamp(target_end))
        ]
        if panel.empty:
            return (
                f"=== LOCAL MARKET ANALYSIS ({','.join(self.market_profiles)}) ===\n"
                f"Period: {target_start} to {target_end}\n"
                "Local market data unavailable.\n"
            )

        close = panel["close"].unstack().mean(axis=1).dropna()
        volume = panel["volume"].unstack().mean(axis=1).dropna()
        returns = close.pct_change().dropna()

        ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else close.mean()
        ma5 = close.rolling(5).mean().iloc[-1] if len(close) >= 5 else close.mean()
        last_close = close.iloc[-1]
        trend = "Bullish (Above MA20)" if last_close > ma20 else "Bearish (Below MA20)"
        momentum = "Strong" if ((last_close > ma20 and ma5 > ma20) or (last_close <= ma20 and ma5 < ma20)) else "Weakening"
        real_vol = (
            float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
            if not returns.empty
            else 0.0
        )
        vol_state = (
            "High Volatility"
            if real_vol > 0.25
            else ("Low Volatility" if real_vol < 0.15 else "Normal Volatility")
        )
        skew = float(returns.skew()) if not returns.empty else 0.0
        kurt = float(returns.kurtosis()) if not returns.empty else 0.0
        period_return = float(close.iloc[-1] / close.iloc[0] - 1.0) if len(close) > 1 else 0.0
        max_drawdown = float((close / close.cummax() - 1).min()) if not close.empty else 0.0
        vol_ratio = float(volume.tail(5).mean() / volume.mean()) if not volume.empty and float(volume.mean()) != 0 else 1.0
        vol_activity = "Expanding" if vol_ratio > 1.2 else ("Shrinking" if vol_ratio < 0.8 else "Stable")

        return (
            f"=== LOCAL MARKET ANALYSIS ({','.join(self.market_profiles)}) ===\n"
            f"Period: {target_start} to {target_end}\n"
            f"- Trend: {trend} | Momentum: {momentum}\n"
            f"- Risk: {vol_state} (Ann. Vol: {real_vol:.2%})\n"
            f"- Return Distribution: Skew={skew:.2f}, Kurt={kurt:.2f}\n"
            f"- Volume Activity: {vol_activity} (Ratio vs Period Avg: {vol_ratio:.2f})\n"
            f"- Performance: Cumulative Return: {period_return:.2%}, Max Drawdown: {max_drawdown:.2%}\n"
        )

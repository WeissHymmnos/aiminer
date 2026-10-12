from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd


class MarketImpactModel(ABC):
    """Abstract base class for transaction cost and market impact models."""

    @abstractmethod
    def compute_drag(
        self,
        weights_df: pd.DataFrame,
        raw_data: pd.DataFrame | None = None,
        label_df: pd.DataFrame | None = None,
    ) -> tuple[pd.Series, pd.DataFrame]:
        """Compute portfolio daily cost drag and per-asset cost rates.

        Returns:
            (daily_cost_drag_series, per_asset_cost_rate_df)
        """
        raise NotImplementedError


class FixedCostImpactModel(MarketImpactModel):
    """Fixed basis-points cost model (e.g., commissions and spread)."""

    def __init__(self, cost_bps: float = 5.0):
        self.cost_bps = float(cost_bps)
        self.cost_rate = self.cost_bps / 10000.0

    def compute_drag(
        self,
        weights_df: pd.DataFrame,
        raw_data: pd.DataFrame | None = None,
        label_df: pd.DataFrame | None = None,
    ) -> tuple[pd.Series, pd.DataFrame]:
        if weights_df.empty:
            empty_s = pd.Series(dtype=float, index=weights_df.index)
            empty_df = pd.DataFrame(
                index=weights_df.index, columns=weights_df.columns
            )
            return empty_s, empty_df

        delta_w = weights_df.diff().abs()
        delta_w.iloc[0] = 0.0

        daily_turnover = delta_w.sum(axis=1) / 2.0
        daily_drag = daily_turnover * self.cost_rate

        cost_matrix = pd.DataFrame(
            self.cost_rate,
            index=weights_df.index,
            columns=weights_df.columns,
        )
        return daily_drag, cost_matrix


class ParticipationMarketImpactModel(MarketImpactModel):
    """Volume-participation market impact model.

    Implements Almgren-Chriss / Barra style impact:
        Impact_rate = base_rate + gamma * sigma * (Participation)^alpha
    where:
        Participation_i,t = (|Delta w_i,t| * Portfolio_Value) / ADV_i,t
    """

    def __init__(
        self,
        *,
        base_cost_bps: float = 5.0,
        impact_gamma: float = 0.1,
        portfolio_value: float = 1e7,
        adv_window: int = 20,
        exponent: float = 0.5,
        default_daily_vol: float = 0.02,
        max_participation: float = 0.5,
    ):
        self.base_cost_bps = float(base_cost_bps)
        self.base_rate = self.base_cost_bps / 10000.0
        self.impact_gamma = float(impact_gamma)
        self.portfolio_value = float(portfolio_value)
        self.adv_window = max(1, int(adv_window))
        self.exponent = float(exponent)
        self.default_daily_vol = float(default_daily_vol)
        self.max_participation = float(max_participation)

    def _extract_adv(
        self,
        weights_df: pd.DataFrame,
        raw_data: pd.DataFrame | None,
    ) -> pd.DataFrame:
        """Extract or estimate Average Daily Traded Value (ADV) matrix."""
        if raw_data is not None and not raw_data.empty:
            if "total_turnover" in raw_data.columns:
                adv_source = raw_data["total_turnover"]
            elif "volume" in raw_data.columns and "close" in raw_data.columns:
                adv_source = raw_data["volume"] * raw_data["close"]
            else:
                adv_source = None

            if adv_source is not None:
                adv_matrix = adv_source.unstack(level="instrument")
                reindexed = adv_matrix.reindex(
                    index=weights_df.index, columns=weights_df.columns
                )
                adv_rolling = reindexed.rolling(
                    window=self.adv_window, min_periods=1
                ).mean()
                return (
                    adv_rolling.replace(0, np.nan)
                    .ffill()
                    .bfill()
                    .fillna(1e7)
                )

        # Fallback default: assume ADV = 5x portfolio value
        return pd.DataFrame(
            self.portfolio_value * 5.0,
            index=weights_df.index,
            columns=weights_df.columns,
        )

    def _extract_volatility(
        self,
        weights_df: pd.DataFrame,
        raw_data: pd.DataFrame | None,
        label_df: pd.DataFrame | None,
    ) -> pd.DataFrame:
        """Extract or estimate rolling daily asset return volatility."""
        ret_matrix = None
        if raw_data is not None and "close" in raw_data.columns:
            close_mat = raw_data["close"].unstack(level="instrument")
            ret_matrix = close_mat.pct_change()
        elif label_df is not None:
            ret_matrix = label_df

        if ret_matrix is not None and not ret_matrix.empty:
            reindexed = ret_matrix.reindex(
                index=weights_df.index, columns=weights_df.columns
            )
            vol_rolling = reindexed.rolling(
                window=self.adv_window, min_periods=2
            ).std()
            return vol_rolling.fillna(self.default_daily_vol).clip(lower=0.001)

        return pd.DataFrame(
            self.default_daily_vol,
            index=weights_df.index,
            columns=weights_df.columns,
        )

    def compute_drag(
        self,
        weights_df: pd.DataFrame,
        raw_data: pd.DataFrame | None = None,
        label_df: pd.DataFrame | None = None,
    ) -> tuple[pd.Series, pd.DataFrame]:
        if weights_df.empty:
            empty_s = pd.Series(dtype=float, index=weights_df.index)
            empty_df = pd.DataFrame(
                index=weights_df.index, columns=weights_df.columns
            )
            return empty_s, empty_df

        delta_w = weights_df.diff().abs()
        delta_w.iloc[0] = 0.0

        adv_df = self._extract_adv(weights_df, raw_data)
        vol_df = self._extract_volatility(weights_df, raw_data, label_df)

        traded_dollars = delta_w * self.portfolio_value
        participation = (traded_dollars / adv_df).clip(
            lower=0.0, upper=self.max_participation
        )

        impact_rates = self.base_rate + (
            self.impact_gamma * vol_df * np.power(participation, self.exponent)
        )

        # Traded dollar cost = traded_dollars * impact_rate
        # Portfolio drag = (delta_w * impact_rates).sum(axis=1) / 2.0
        # (normalized to long-short portfolio basis)
        daily_drag = (delta_w * impact_rates).sum(axis=1) / 2.0
        return daily_drag, impact_rates


class SquareRootImpactModel(ParticipationMarketImpactModel):
    """Square-root law market impact (Barra / Almgren-Chriss, alpha=0.5)."""

    def __init__(
        self,
        *,
        base_cost_bps: float = 5.0,
        impact_gamma: float = 0.1,
        portfolio_value: float = 1e7,
        adv_window: int = 20,
    ):
        super().__init__(
            base_cost_bps=base_cost_bps,
            impact_gamma=impact_gamma,
            portfolio_value=portfolio_value,
            adv_window=adv_window,
            exponent=0.5,
        )


class LinearParticipationImpactModel(ParticipationMarketImpactModel):
    """Linear permanent market impact model (Kyle's lambda, alpha=1.0)."""

    def __init__(
        self,
        *,
        base_cost_bps: float = 5.0,
        impact_gamma: float = 0.05,
        portfolio_value: float = 1e7,
        adv_window: int = 20,
    ):
        super().__init__(
            base_cost_bps=base_cost_bps,
            impact_gamma=impact_gamma,
            portfolio_value=portfolio_value,
            adv_window=adv_window,
            exponent=1.0,
        )


def build_impact_model(
    model_name: str | None,
    *,
    cost_bps: float = 5.0,
    impact_gamma: float = 0.1,
    portfolio_value: float = 1e7,
    **kwargs: Any,
) -> MarketImpactModel:
    """Factory helper to build market impact models."""
    name = (model_name or "fixed").strip().lower()
    if name in {"fixed", "fixed_cost", "none"}:
        return FixedCostImpactModel(cost_bps=cost_bps)
    if name in {"square_root", "sqrt", "almgren_chriss", "almgren"}:
        return SquareRootImpactModel(
            base_cost_bps=cost_bps,
            impact_gamma=impact_gamma,
            portfolio_value=portfolio_value,
            **kwargs,
        )
    if name in {"linear", "linear_participation", "kyle"}:
        return LinearParticipationImpactModel(
            base_cost_bps=cost_bps,
            impact_gamma=impact_gamma,
            portfolio_value=portfolio_value,
            **kwargs,
        )
    raise ValueError(f"Unsupported market impact model: {model_name}")

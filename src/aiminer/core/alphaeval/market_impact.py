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

    @staticmethod
    def _pivot_to_matrix(
        raw_data: pd.DataFrame | None,
        col_names: list[str],
        weights_df: pd.DataFrame,
    ) -> pd.DataFrame | None:
        """Pivot raw_data to (datetime x instrument) DataFrame."""
        if raw_data is None or raw_data.empty:
            return None
        try:
            if isinstance(raw_data.index, pd.MultiIndex):
                names = raw_data.index.names
                inst_lvl = next(
                    (
                        n
                        for n in names
                        if n in ("instrument", "order_book_id", "symbol")
                    ),
                    names[1] if len(names) > 1 else None,
                )
                dt_lvl = next(
                    (
                        n
                        for n in names
                        if n in ("datetime", "date", "timestamp")
                    ),
                    names[0] if len(names) > 0 else None,
                )
                target_col = next(
                    (c for c in col_names if c in raw_data.columns), None
                )
                if target_col is None:
                    return None
                series = raw_data[target_col]
                if inst_lvl is not None and dt_lvl is not None:
                    if series.index.duplicated().any():
                        series = series.groupby(level=[dt_lvl, inst_lvl]).mean()
                    matrix = series.unstack(level=inst_lvl)
                    return matrix.reindex(
                        index=weights_df.index, columns=weights_df.columns
                    )
            work = raw_data.copy()
            inst_col = next(
                (
                    c
                    for c in work.columns
                    if c in ("instrument", "order_book_id", "symbol")
                ),
                None,
            )
            dt_col = next(
                (
                    c
                    for c in work.columns
                    if c in ("datetime", "date", "timestamp")
                ),
                None,
            )
            target_col = next((c for c in col_names if c in work.columns), None)
            if inst_col and dt_col and target_col:
                work[dt_col] = pd.to_datetime(work[dt_col])
                matrix = (
                    work.groupby([dt_col, inst_col])[target_col]
                    .mean()
                    .unstack(level=inst_col)
                )
                return matrix.reindex(
                    index=weights_df.index, columns=weights_df.columns
                )
        except Exception:
            return None
        return None

    def _extract_adv(
        self,
        weights_df: pd.DataFrame,
        raw_data: pd.DataFrame | None,
    ) -> pd.DataFrame:
        """Extract or estimate Average Daily Traded Value (ADV) matrix."""
        fallback_adv = self.portfolio_value * 5.0
        adv_matrix = None
        if raw_data is not None and not raw_data.empty:
            adv_matrix = self._pivot_to_matrix(
                raw_data, ["total_turnover"], weights_df
            )
            if adv_matrix is None:
                vol_mat = self._pivot_to_matrix(
                    raw_data, ["volume"], weights_df
                )
                px_mat = self._pivot_to_matrix(raw_data, ["close"], weights_df)
                if vol_mat is not None and px_mat is not None:
                    adv_matrix = vol_mat * px_mat

        if adv_matrix is not None and not adv_matrix.empty:
            adv_rolling = adv_matrix.rolling(
                window=self.adv_window, min_periods=1
            ).mean()
            clean = adv_rolling.mask(adv_rolling <= 0, np.nan)
            return clean.ffill().bfill().fillna(fallback_adv)

        return pd.DataFrame(
            fallback_adv,
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
        if raw_data is not None and not raw_data.empty:
            close_mat = self._pivot_to_matrix(raw_data, ["close"], weights_df)
            if close_mat is not None:
                ret_matrix = close_mat.pct_change()

        if ret_matrix is None and label_df is not None:
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

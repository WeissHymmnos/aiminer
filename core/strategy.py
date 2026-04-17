from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import json
import sqlite3

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator


StrategyMode = Literal["cross_sectional", "time_series"]
SignalSource = Literal["expression", "factor_combo"]
Direction = Literal["long_only", "long_short", "long_flat"]
SelectionRule = Literal["top_n", "bottom_n", "top_bottom_n", "threshold"]
RebalanceFreq = Literal["daily", "weekly", "monthly"]


class StrategyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Optional[str] = None
    strategy_mode: StrategyMode
    signal_source: SignalSource = "expression"
    direction: Direction
    selection_rule: SelectionRule
    rebalance_freq: RebalanceFreq = "daily"
    top_n: Optional[int] = Field(default=None, ge=1)
    bottom_n: Optional[int] = Field(default=None, ge=1)
    long_threshold: Optional[float] = None
    short_threshold: Optional[float] = None
    exit_threshold: Optional[float] = None
    max_positions: Optional[int] = Field(default=None, ge=1)
    max_weight_per_position: float = Field(default=0.1, gt=0, le=1.0)
    min_holding_days: int = Field(default=1, ge=1)
    commission_bps: float = Field(default=5.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    market: str = "000300.XSHG"
    start_date: str = "2017-01-01"
    end_date: str = "2020-10-31"
    engine: Literal["pandas", "polars"] = "polars"

    @model_validator(mode="after")
    def validate_semantics(self) -> "StrategyConfig":
        if self.selection_rule == "top_n" and self.top_n is None:
            raise ValueError("top_n is required when selection_rule='top_n'")
        if self.selection_rule == "bottom_n" and self.bottom_n is None:
            raise ValueError("bottom_n is required when selection_rule='bottom_n'")
        if self.selection_rule == "top_bottom_n":
            if self.top_n is None or self.bottom_n is None:
                raise ValueError(
                    "top_n and bottom_n are required when selection_rule='top_bottom_n'"
                )
        if self.selection_rule == "threshold":
            if self.long_threshold is None and self.short_threshold is None:
                raise ValueError(
                    "At least one of long_threshold/short_threshold is required when selection_rule='threshold'"
                )
        if self.strategy_mode == "cross_sectional" and self.direction == "long_flat":
            raise ValueError("cross_sectional strategy does not support long_flat")
        if self.strategy_mode == "time_series" and self.selection_rule in {
            "top_n",
            "bottom_n",
            "top_bottom_n",
        }:
            raise ValueError("time_series strategy only supports threshold rule")
        return self


class StrategyProposalOutput(BaseModel):
    template_name: str
    strategy_mode: StrategyMode
    direction: Direction
    selection_rule: SelectionRule
    rebalance_freq: RebalanceFreq
    thresholds: Dict[str, float] = Field(default_factory=dict)
    counts: Dict[str, int] = Field(default_factory=dict)
    holding_constraints: Dict[str, float | int] = Field(default_factory=dict)
    cost_model: Dict[str, float] = Field(default_factory=dict)
    rationale: str


def strategy_templates() -> dict[str, StrategyConfig]:
    return {
        "cs_top_bottom": StrategyConfig(
            label="Cross-sectional Top/Bottom Long-Short",
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="top_bottom_n",
            rebalance_freq="daily",
            top_n=20,
            bottom_n=20,
            max_positions=40,
            max_weight_per_position=0.05,
            min_holding_days=1,
        ),
        "cs_top_only": StrategyConfig(
            label="Cross-sectional Top-N Long-Only",
            strategy_mode="cross_sectional",
            direction="long_only",
            selection_rule="top_n",
            rebalance_freq="daily",
            top_n=20,
            max_positions=20,
            max_weight_per_position=0.08,
            min_holding_days=1,
        ),
        "cs_threshold": StrategyConfig(
            label="Cross-sectional Threshold Long-Only",
            strategy_mode="cross_sectional",
            direction="long_only",
            selection_rule="threshold",
            rebalance_freq="weekly",
            long_threshold=0.75,
            max_positions=25,
            max_weight_per_position=0.06,
            min_holding_days=3,
        ),
        "ts_long_flat": StrategyConfig(
            label="Time-Series Threshold Long/Flat",
            strategy_mode="time_series",
            direction="long_flat",
            selection_rule="threshold",
            rebalance_freq="daily",
            long_threshold=0.6,
            exit_threshold=0.45,
            max_positions=40,
            max_weight_per_position=0.04,
            min_holding_days=2,
        ),
        "ts_long_short": StrategyConfig(
            label="Time-Series Threshold Long/Short",
            strategy_mode="time_series",
            direction="long_short",
            selection_rule="threshold",
            rebalance_freq="daily",
            long_threshold=0.75,
            short_threshold=0.25,
            exit_threshold=0.5,
            max_positions=50,
            max_weight_per_position=0.03,
            min_holding_days=2,
        ),
    }


@dataclass
class StrategyBacktestResult:
    strategy_id: str
    run_type: str
    expression: str
    strategy_config: Dict[str, Any]
    metrics: Dict[str, Any]
    daily_returns: Dict[str, float]
    positions: Dict[str, Dict[str, float]]
    trade_stats: Dict[str, Any]
    chart_paths: Dict[str, str]
    market: str
    engine: str
    ran_at: str
    label: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "run_type": self.run_type,
            "expression": self.expression,
            "strategy_config": self.strategy_config,
            "metrics": self.metrics,
            "daily_returns": self.daily_returns,
            "positions": self.positions,
            "trade_stats": self.trade_stats,
            "chart_paths": self.chart_paths,
            "market": self.market,
            "engine": self.engine,
            "ran_at": self.ran_at,
            "label": self.label,
        }


def _normalize_positions(row: pd.Series, max_weight: float) -> pd.Series:
    row = row.fillna(0.0)
    if row.empty:
        return row
    gross = row.abs().sum()
    if gross <= 1e-12:
        return row * 0.0
    normalized = row / gross
    normalized = normalized.clip(lower=-max_weight, upper=max_weight)
    gross = normalized.abs().sum()
    if gross <= 1e-12:
        return normalized
    return normalized / gross


def _rebalance_mask(index: pd.Index, freq: RebalanceFreq) -> pd.Series:
    dt_index = pd.to_datetime(index)
    if freq == "daily":
        return pd.Series(True, index=dt_index)
    if freq == "weekly":
        periods = dt_index.to_period("W")
    else:
        periods = dt_index.to_period("M")
    return pd.Series(periods != periods.shift(1), index=dt_index).fillna(True)


class StrategyBacktester:
    def __init__(self, config: StrategyConfig):
        self.config = config

    def run(self, signal_df: pd.DataFrame, label_df: pd.DataFrame) -> Dict[str, Any]:
        signal_df = signal_df.sort_index().sort_index(axis=1)
        label_df = label_df.reindex_like(signal_df).fillna(0.0)

        desired = (
            self._build_cross_sectional_positions(signal_df)
            if self.config.strategy_mode == "cross_sectional"
            else self._build_time_series_positions(signal_df)
        )
        positions, trade_stats = self._apply_rebalance_and_constraints(desired)
        turnover = positions.diff().abs().sum(axis=1).fillna(positions.abs().sum(axis=1))
        gross_returns = (positions * label_df).sum(axis=1)
        cost_rate = (
            self.config.commission_bps + self.config.slippage_bps
        ) / 10000.0
        costs = turnover * cost_rate
        net_returns = gross_returns - costs
        cumulative = (1 + net_returns.fillna(0.0)).cumprod()

        sharpe = 0.0
        if float(net_returns.std()) > 1e-12:
            sharpe = float(net_returns.mean() / net_returns.std() * np.sqrt(252))
        max_dd = (
            float((cumulative / cumulative.cummax() - 1.0).min())
            if not cumulative.empty
            else 0.0
        )
        annualized_return = (
            float(cumulative.iloc[-1] ** (252.0 / max(len(cumulative), 1)) - 1.0)
            if not cumulative.empty
            else 0.0
        )
        holding_lengths = trade_stats.pop("holding_lengths", [])
        metrics = {
            "annualized_return": annualized_return,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "turnover": float(turnover.mean()) if not turnover.empty else 0.0,
            "win_rate": float((net_returns > 0).mean()) if not net_returns.empty else 0.0,
            "average_holding_period": (
                float(np.mean(holding_lengths)) if holding_lengths else 0.0
            ),
            "gross_exposure": (
                float(positions.abs().sum(axis=1).mean()) if not positions.empty else 0.0
            ),
            "net_exposure": (
                float(positions.sum(axis=1).mean()) if not positions.empty else 0.0
            ),
            "cost_drag": float(costs.sum()),
            "gross_return": float(gross_returns.sum()) if not gross_returns.empty else 0.0,
            "net_return": float(net_returns.sum()) if not net_returns.empty else 0.0,
        }

        snapshot = positions.tail(5).replace({np.nan: 0.0})
        positions_dict = {
            str(idx.date() if hasattr(idx, "date") else idx): {
                col: float(val) for col, val in row.items() if abs(float(val)) > 1e-12
            }
            for idx, row in snapshot.iterrows()
        }
        return {
            "metrics": metrics,
            "daily_returns": {
                str(k.date() if hasattr(k, "date") else k): float(v)
                for k, v in net_returns.fillna(0.0).items()
            },
            "positions": positions_dict,
            "trade_stats": {
                **trade_stats,
                "avg_turnover": float(turnover.mean()) if not turnover.empty else 0.0,
                "total_cost": float(costs.sum()),
                "rebalance_days": int((turnover > 0).sum()),
            },
            "raw_positions": positions,
            "raw_returns": net_returns,
        }

    def _build_cross_sectional_positions(self, signal_df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        frames = []
        for _, row in signal_df.iterrows():
            pos = pd.Series(0.0, index=row.index, dtype=float)
            ordered = row.dropna().sort_values()
            if ordered.empty:
                frames.append(pos)
                continue
            if cfg.selection_rule == "top_n":
                selected = ordered.tail(cfg.top_n or 0).index
                pos.loc[selected] = 1.0
            elif cfg.selection_rule == "bottom_n":
                selected = ordered.head(cfg.bottom_n or 0).index
                pos.loc[selected] = -1.0 if cfg.direction == "long_short" else 1.0
            elif cfg.selection_rule == "top_bottom_n":
                long_idx = ordered.tail(cfg.top_n or 0).index
                short_idx = ordered.head(cfg.bottom_n or 0).index
                pos.loc[long_idx] = 1.0
                pos.loc[short_idx] = -1.0
            else:
                if cfg.long_threshold is not None:
                    pos.loc[row >= cfg.long_threshold] = 1.0
                if cfg.short_threshold is not None and cfg.direction == "long_short":
                    pos.loc[row <= cfg.short_threshold] = -1.0
            if cfg.direction == "long_only":
                pos = pos.clip(lower=0.0)
            frames.append(_normalize_positions(pos, cfg.max_weight_per_position))
        result = pd.DataFrame(frames, index=signal_df.index, columns=signal_df.columns)
        return result.fillna(0.0)

    def _build_time_series_positions(self, signal_df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        positions = pd.DataFrame(0.0, index=signal_df.index, columns=signal_df.columns)
        for col in signal_df.columns:
            current = 0.0
            held = 0
            series = signal_df[col].fillna(0.0)
            for idx, value in series.items():
                desired = current
                if cfg.direction == "long_flat":
                    if cfg.long_threshold is not None and value >= cfg.long_threshold:
                        desired = 1.0
                    elif (
                        cfg.exit_threshold is not None and value <= cfg.exit_threshold
                    ) or (
                        cfg.long_threshold is not None and value < cfg.long_threshold
                    ):
                        desired = 0.0
                elif cfg.direction == "long_short":
                    if cfg.long_threshold is not None and value >= cfg.long_threshold:
                        desired = 1.0
                    elif cfg.short_threshold is not None and value <= cfg.short_threshold:
                        desired = -1.0
                    elif (
                        cfg.exit_threshold is not None
                        and abs(value - cfg.exit_threshold) <= 1e-12
                    ):
                        desired = 0.0
                    elif cfg.exit_threshold is not None:
                        if current > 0 and value < cfg.exit_threshold:
                            desired = 0.0
                        if current < 0 and value > cfg.exit_threshold:
                            desired = 0.0
                else:
                    if cfg.long_threshold is not None and value >= cfg.long_threshold:
                        desired = 1.0

                if desired != current and current != 0.0 and held < cfg.min_holding_days:
                    desired = current
                if desired == current and current != 0.0:
                    held += 1
                else:
                    held = 1 if desired != 0.0 else 0
                current = desired
                positions.at[idx, col] = current

        if cfg.max_positions:
            ranked = signal_df.where(positions != 0.0).abs().rank(
                axis=1, ascending=False, method="first"
            )
            positions = positions.where(ranked <= cfg.max_positions, 0.0)
        return positions.apply(
            lambda row: _normalize_positions(row, cfg.max_weight_per_position), axis=1
        ).fillna(0.0)

    def _apply_rebalance_and_constraints(
        self, desired: pd.DataFrame
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        cfg = self.config
        rebalance = _rebalance_mask(desired.index, cfg.rebalance_freq)
        positions = pd.DataFrame(0.0, index=desired.index, columns=desired.columns)
        holding_days = {col: 0 for col in desired.columns}
        holding_lengths: list[int] = []

        prev = pd.Series(0.0, index=desired.columns, dtype=float)
        for dt in desired.index:
            candidate = (
                desired.loc[dt].copy()
                if rebalance.loc[pd.to_datetime(dt)]
                else prev.copy()
            )
            if cfg.max_positions:
                non_zero = candidate[candidate != 0.0]
                if len(non_zero) > cfg.max_positions:
                    keep = (
                        non_zero.abs().sort_values(ascending=False).head(cfg.max_positions).index
                    )
                    candidate.loc[~candidate.index.isin(keep)] = 0.0
            for col in candidate.index:
                if prev[col] != 0.0:
                    holding_days[col] += 1
                if (
                    candidate[col] != prev[col]
                    and prev[col] != 0.0
                    and holding_days[col] < cfg.min_holding_days
                ):
                    candidate[col] = prev[col]
                elif candidate[col] != prev[col] and prev[col] != 0.0:
                    holding_lengths.append(holding_days[col])
                    holding_days[col] = 0
                elif candidate[col] != 0.0 and prev[col] == 0.0:
                    holding_days[col] = 1
            candidate = _normalize_positions(candidate, cfg.max_weight_per_position)
            positions.loc[dt] = candidate
            prev = candidate
        return positions.fillna(0.0), {"holding_lengths": holding_lengths}


def ensure_strategy_table(db_path: str | Path) -> None:
    db_path = str(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS strategy_backtests (
                strategy_id TEXT PRIMARY KEY,
                label TEXT,
                run_type TEXT,
                strategy_mode TEXT,
                signal_source TEXT,
                expression_json TEXT,
                strategy_config_json TEXT,
                metrics_json TEXT,
                daily_returns_json TEXT,
                positions_json TEXT,
                trade_stats_json TEXT,
                chart_paths_json TEXT,
                market TEXT,
                engine TEXT,
                ran_at TEXT,
                run_id TEXT,
                source_factor_id TEXT
            )
            """
        )
        for column, ddl in [
            ("run_id", "ALTER TABLE strategy_backtests ADD COLUMN run_id TEXT"),
            (
                "source_factor_id",
                "ALTER TABLE strategy_backtests ADD COLUMN source_factor_id TEXT",
            ),
        ]:
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_strategy_backtests_ran_at ON strategy_backtests(ran_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_strategy_backtests_run_id ON strategy_backtests(run_id)"
        )
        conn.commit()


def persist_strategy_result(db_path: str | Path, payload: Dict[str, Any]) -> None:
    ensure_strategy_table(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO strategy_backtests (
                strategy_id, label, run_type, strategy_mode, signal_source,
                expression_json, strategy_config_json, metrics_json, daily_returns_json,
                positions_json, trade_stats_json, chart_paths_json,
                market, engine, ran_at, run_id, source_factor_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("strategy_id"),
                payload.get("label"),
                payload.get("run_type"),
                payload.get("strategy_config", {}).get("strategy_mode"),
                payload.get("strategy_config", {}).get("signal_source"),
                json.dumps({"expression": payload.get("expression")}, ensure_ascii=False),
                json.dumps(payload.get("strategy_config", {}), ensure_ascii=False),
                json.dumps(payload.get("metrics", {}), ensure_ascii=False),
                json.dumps(payload.get("daily_returns", {}), ensure_ascii=False),
                json.dumps(payload.get("positions", {}), ensure_ascii=False),
                json.dumps(payload.get("trade_stats", {}), ensure_ascii=False),
                json.dumps(payload.get("chart_paths", {}), ensure_ascii=False),
                payload.get("market"),
                payload.get("engine"),
                payload.get("ran_at"),
                payload.get("run_id"),
                payload.get("source_factor_id"),
            ),
        )
        conn.commit()

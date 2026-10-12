from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rule: str
    severity: ValidationSeverity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class DataValidationReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    is_valid: bool
    source: str
    contract_type: str
    row_count: int
    issues: list[ValidationIssue] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)

    def add_issue(
        self,
        rule: str,
        severity: ValidationSeverity,
        message: str,
        **details: Any,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                rule=rule,
                severity=severity,
                message=message,
                details=details,
            )
        )
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False

    @property
    def error_count(self) -> int:
        return sum(
            1
            for issue in self.issues
            if issue.severity == ValidationSeverity.ERROR
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        )


class DataContractError(ValueError):
    """Raised when data violates a required contract schema."""

    def __init__(
        self, message: str, report: DataValidationReport | None = None
    ):
        super().__init__(message)
        self.report = report


class OHLCVContract(BaseModel):
    model_config = ConfigDict(extra="ignore")

    datetime: datetime
    instrument: str
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    vwap: float | None = None
    total_turnover: float | None = None


class MarketDepthContract(BaseModel):
    model_config = ConfigDict(extra="ignore")

    datetime: datetime
    instrument: str
    bid_price_1: float = Field(gt=0)
    ask_price_1: float = Field(gt=0)
    bid_vol_1: float = Field(ge=0)
    ask_vol_1: float = Field(ge=0)


class TickContract(BaseModel):
    model_config = ConfigDict(extra="ignore")

    datetime: datetime
    instrument: str
    price: float = Field(gt=0)
    volume: float = Field(ge=0)
    turnover: float | None = None


class DataContractValidator:
    """Production validator for OHLCV, market depth, and tick inputs."""

    @staticmethod
    def _coerce_df(df_or_pl: Any) -> pd.DataFrame:
        if hasattr(df_or_pl, "to_pandas"):
            return df_or_pl.to_pandas()
        if isinstance(df_or_pl, pd.DataFrame):
            return df_or_pl
        raise TypeError(f"Expected DataFrame, got {type(df_or_pl)}")

    @classmethod
    def detect_missing_dates(
        cls,
        dates: pd.DatetimeIndex | pd.Series,
        *,
        max_allowed_gap_days: int = 4,
    ) -> list[dict[str, Any]]:
        """Detect gaps in trading dates exceeding normal weekend limits."""
        dt_series = (
            pd.Series(pd.to_datetime(dates)).drop_duplicates().sort_values()
        )
        if len(dt_series) < 2:
            return []

        diffs = dt_series.diff()
        suspicious = diffs[diffs > pd.Timedelta(days=max_allowed_gap_days)]
        gaps = []
        for idx, gap in suspicious.items():
            start_date = (
                dt_series.loc[idx - 1] if (idx - 1) in dt_series.index else None
            )
            end_date = dt_series.loc[idx]
            gaps.append(
                {
                    "gap_days": gap.days,
                    "previous_date": str(start_date) if start_date else None,
                    "resume_date": str(end_date),
                }
            )
        return gaps

    @classmethod
    def detect_forward_survivorship_bias(
        cls,
        df: pd.DataFrame,
        *,
        cutoff_date: str | datetime | None = None,
        listing_dates: dict[str, str | datetime] | None = None,
    ) -> list[dict[str, Any]]:
        """Detect forward leakage beyond cutoff or pre-listing survivorship."""
        violations = []
        frame = df.copy()
        if isinstance(frame.index, pd.MultiIndex):
            dt_idx = frame.index.get_level_values("datetime")
            inst_idx = frame.index.get_level_values("instrument")
        else:
            dt_idx = pd.to_datetime(frame["datetime"])
            inst_idx = frame["instrument"]

        dt_series = pd.Series(pd.to_datetime(dt_idx), index=frame.index)
        inst_series = pd.Series(inst_idx, index=frame.index)

        # Check future leakage beyond cutoff_date
        if cutoff_date is not None:
            cutoff = pd.Timestamp(cutoff_date)
            future_mask = dt_series > cutoff
            future_count = int(future_mask.sum())
            if future_count > 0:
                violations.append(
                    {
                        "type": "future_cutoff_leakage",
                        "cutoff_date": str(cutoff),
                        "future_rows": future_count,
                        "max_date_found": str(dt_series.max()),
                    }
                )

        # Check listing date violations (data before instrument listing)
        if listing_dates:
            for inst, list_dt in listing_dates.items():
                list_ts = pd.Timestamp(list_dt)
                sub_mask = (inst_series == inst) & (dt_series < list_ts)
                sub_count = int(sub_mask.sum())
                if sub_count > 0:
                    violations.append(
                        {
                            "type": "pre_listing_survivorship",
                            "instrument": inst,
                            "listing_date": str(list_ts),
                            "premature_rows": sub_count,
                            "min_date_found": str(
                                dt_series[inst_series == inst].min()
                            ),
                        }
                    )
        return violations

    @classmethod
    def validate_ohlcv(
        cls,
        data: Any,
        *,
        source: str = "ohlcv_data",
        strict: bool = True,
        cutoff_date: str | datetime | None = None,
        listing_dates: dict[str, str | datetime] | None = None,
        check_calendar_gaps: bool = True,
    ) -> DataValidationReport:
        """Validate OHLCV data contract and integrity anomalies."""
        df = cls._coerce_df(data)
        report = DataValidationReport(
            is_valid=True,
            source=source,
            contract_type="OHLCV",
            row_count=len(df),
        )

        if df.empty:
            report.add_issue(
                rule="non_empty",
                severity=ValidationSeverity.ERROR,
                message="Dataset is empty.",
            )
            if strict:
                raise DataContractError(f"{source}: dataset is empty", report)
            return report

        # Flatten multi-index if present for column validation
        work = df.copy()
        if isinstance(work.index, pd.MultiIndex):
            work = work.reset_index()

        required_cols = {"open", "high", "low", "close", "volume"}
        missing_cols = sorted(required_cols - set(work.columns))
        if missing_cols:
            report.add_issue(
                rule="required_columns",
                severity=ValidationSeverity.ERROR,
                message=f"Missing required OHLCV columns: {missing_cols}",
                missing=missing_cols,
            )
            if strict:
                raise DataContractError(
                    f"{source}: missing required columns {missing_cols}",
                    report,
                )
            return report

        # Anomaly 1: Inf / -Inf checks
        numeric_cols = [
            c
            for c in ["open", "high", "low", "close", "volume"]
            if c in work.columns
        ]
        for col in numeric_cols:
            vals = pd.to_numeric(work[col], errors="coerce")
            inf_mask = np.isinf(vals)
            inf_count = int(inf_mask.sum())
            if inf_count > 0:
                report.add_issue(
                    rule="no_infinite_values",
                    severity=ValidationSeverity.ERROR,
                    message=f"Column '{col}' has {inf_count} infinite values.",
                    column=col,
                    count=inf_count,
                )

            nan_count = int(vals.isna().sum())
            if nan_count > 0:
                report.add_issue(
                    rule="no_nan_values",
                    severity=ValidationSeverity.ERROR,
                    message=f"Column '{col}' has {nan_count} NaN values.",
                    column=col,
                    count=nan_count,
                )

        # Anomaly 2: Price positivity and invariants
        price_df = work[["open", "high", "low", "close"]].apply(
            pd.to_numeric, errors="coerce"
        )
        non_positive = (price_df <= 0).any(axis=1)
        if non_positive.any():
            report.add_issue(
                rule="positive_prices",
                severity=ValidationSeverity.ERROR,
                message=f"{int(non_positive.sum())} rows have price <= 0.",
                count=int(non_positive.sum()),
            )

        bad_hl = price_df["high"] < price_df["low"]
        if bad_hl.any():
            report.add_issue(
                rule="high_gte_low",
                severity=ValidationSeverity.ERROR,
                message=f"{int(bad_hl.sum())} rows violate high >= low.",
                count=int(bad_hl.sum()),
            )

        bad_open_close = (
            (price_df["open"] > price_df["high"])
            | (price_df["open"] < price_df["low"])
            | (price_df["close"] > price_df["high"])
            | (price_df["close"] < price_df["low"])
        )
        if bad_open_close.any():
            report.add_issue(
                rule="ohlc_bounding",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"{int(bad_open_close.sum())} rows have open/close outside "
                    "[low, high]."
                ),
                count=int(bad_open_close.sum()),
            )

        # Anomaly 3: Volume checks
        vol = pd.to_numeric(work["volume"], errors="coerce")
        neg_vol = vol < 0
        if neg_vol.any():
            report.add_issue(
                rule="non_negative_volume",
                severity=ValidationSeverity.ERROR,
                message=f"{int(neg_vol.sum())} rows have negative volume.",
                count=int(neg_vol.sum()),
            )

        # Anomaly 4: Datetime / Calendar checks
        if "datetime" in work.columns:
            dt = pd.to_datetime(work["datetime"], errors="coerce")
            nat_count = int(dt.isna().sum())
            if nat_count > 0:
                report.add_issue(
                    rule="valid_timestamps",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"{nat_count} rows have invalid timestamps."
                    ),
                    count=nat_count,
                )

            if "instrument" in work.columns:
                dupes = work.duplicated(subset=["datetime", "instrument"]).sum()
                if dupes > 0:
                    report.add_issue(
                        rule="unique_keys",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"{int(dupes)} duplicate pairs found."
                        ),
                        count=int(dupes),
                    )

            if check_calendar_gaps:
                gaps = cls.detect_missing_dates(dt.dropna())
                if gaps:
                    report.add_issue(
                        rule="calendar_continuity",
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"{len(gaps)} calendar gap(s) detected."
                        ),
                        gaps=gaps[:5],
                    )

        # Anomaly 5: Survivorship / Forward Leakage
        bias_issues = cls.detect_forward_survivorship_bias(
            work if "instrument" in work.columns else df,
            cutoff_date=cutoff_date,
            listing_dates=listing_dates,
        )
        for issue in bias_issues:
            report.add_issue(
                rule=issue["type"],
                severity=ValidationSeverity.ERROR,
                message=f"Forward bias anomaly detected: {issue}",
                **issue,
            )

        report.summary = {
            "rows": len(df),
            "errors": report.error_count,
            "warnings": report.warning_count,
        }

        if strict and not report.is_valid:
            error_msgs = "; ".join(
                iss.message
                for iss in report.issues
                if iss.severity == ValidationSeverity.ERROR
            )
            raise DataContractError(
                f"Data contract validation failed for {source}: {error_msgs}",
                report,
            )

        return report

    @classmethod
    def validate_market_depth(
        cls,
        data: Any,
        *,
        depth_levels: int = 5,
        source: str = "market_depth",
        strict: bool = True,
    ) -> DataValidationReport:
        """Validate Level 2 / orderbook market depth data."""
        df = cls._coerce_df(data)
        report = DataValidationReport(
            is_valid=True,
            source=source,
            contract_type="MarketDepth",
            row_count=len(df),
        )

        if df.empty:
            report.add_issue(
                rule="non_empty",
                severity=ValidationSeverity.ERROR,
                message="Dataset is empty.",
            )
            if strict:
                raise DataContractError(f"{source}: dataset is empty", report)
            return report

        work = df.copy()
        if isinstance(work.index, pd.MultiIndex):
            work = work.reset_index()

        # Check level 1 presence
        req = ["bid_price_1", "ask_price_1", "bid_vol_1", "ask_vol_1"]
        missing = [c for c in req if c not in work.columns]
        if missing:
            report.add_issue(
                rule="required_depth_cols",
                severity=ValidationSeverity.ERROR,
                message=f"Missing depth columns: {missing}",
            )
            if strict:
                raise DataContractError(
                    f"{source}: missing required depth columns {missing}",
                    report,
                )
            return report

        # Crossed book check: ask_price_1 must strictly exceed bid_price_1
        ask1 = pd.to_numeric(work["ask_price_1"], errors="coerce")
        bid1 = pd.to_numeric(work["bid_price_1"], errors="coerce")
        crossed = ask1 <= bid1
        if crossed.any():
            report.add_issue(
                rule="crossed_book",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"{int(crossed.sum())} rows have crossed book."
                ),
                count=int(crossed.sum()),
            )

        # Monotonicity check across ladder
        for lvl in range(1, depth_levels):
            curr_bid = f"bid_price_{lvl}"
            next_bid = f"bid_price_{lvl + 1}"
            if curr_bid in work.columns and next_bid in work.columns:
                b_curr = pd.to_numeric(work[curr_bid], errors="coerce")
                b_next = pd.to_numeric(work[next_bid], errors="coerce")
                bad_bid_ladder = b_curr <= b_next
                if bad_bid_ladder.any():
                    report.add_issue(
                        rule="monotonic_bid_ladder",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"{int(bad_bid_ladder.sum())} rows violate "
                            f"bid ladder ({curr_bid} <= {next_bid})."
                        ),
                    )

            curr_ask = f"ask_price_{lvl}"
            next_ask = f"ask_price_{lvl + 1}"
            if curr_ask in work.columns and next_ask in work.columns:
                a_curr = pd.to_numeric(work[curr_ask], errors="coerce")
                a_next = pd.to_numeric(work[next_ask], errors="coerce")
                bad_ask_ladder = a_curr >= a_next
                if bad_ask_ladder.any():
                    report.add_issue(
                        rule="monotonic_ask_ladder",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"{int(bad_ask_ladder.sum())} rows violate "
                            f"ask ladder ({curr_ask} >= {next_ask})."
                        ),
                    )

        # Depth size positivity
        vol_cols = [
            c
            for c in work.columns
            if "vol" in c or "volume" in c or "size" in c
        ]
        for vc in vol_cols:
            s_vol = pd.to_numeric(work[vc], errors="coerce")
            neg = s_vol < 0
            if neg.any():
                report.add_issue(
                    rule="non_negative_depth_volume",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Column {vc} has {int(neg.sum())} negative volume."
                    ),
                )

        report.summary = {
            "rows": len(df),
            "errors": report.error_count,
            "warnings": report.warning_count,
        }

        if strict and not report.is_valid:
            error_msgs = "; ".join(
                iss.message
                for iss in report.issues
                if iss.severity == ValidationSeverity.ERROR
            )
            raise DataContractError(
                f"Market depth validation failed for {source}: {error_msgs}",
                report,
            )

        return report

    @classmethod
    def validate_tick_data(
        cls,
        data: Any,
        *,
        source: str = "tick_data",
        strict: bool = True,
    ) -> DataValidationReport:
        """Validate tick data feed for monotonicity and price sanity."""
        df = cls._coerce_df(data)
        report = DataValidationReport(
            is_valid=True,
            source=source,
            contract_type="Tick",
            row_count=len(df),
        )

        if df.empty:
            report.add_issue(
                rule="non_empty",
                severity=ValidationSeverity.ERROR,
                message="Tick dataset is empty.",
            )
            if strict:
                raise DataContractError(f"{source}: dataset is empty", report)
            return report

        work = df.copy()
        if isinstance(work.index, pd.MultiIndex):
            work = work.reset_index()

        required = {"datetime", "instrument", "price", "volume"}
        missing = sorted(required - set(work.columns))
        if missing:
            report.add_issue(
                rule="required_tick_cols",
                severity=ValidationSeverity.ERROR,
                message=f"Missing tick columns: {missing}",
            )
            if strict:
                raise DataContractError(
                    f"{source}: missing tick columns {missing}", report
                )
            return report

        px = pd.to_numeric(work["price"], errors="coerce")
        bad_px = (px <= 0) | np.isinf(px) | px.isna()
        if bad_px.any():
            report.add_issue(
                rule="valid_tick_prices",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"{int(bad_px.sum())} tick rows have invalid price."
                ),
            )

        vol = pd.to_numeric(work["volume"], errors="coerce")
        bad_vol = (vol < 0) | np.isinf(vol) | vol.isna()
        if bad_vol.any():
            report.add_issue(
                rule="valid_tick_volume",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"{int(bad_vol.sum())} tick rows have invalid volume."
                ),
            )

        # Monotonic timestamps per instrument
        dt = pd.to_datetime(work["datetime"], errors="coerce")
        work["_parsed_dt"] = dt
        for inst, group in work.groupby("instrument"):
            ts_diff = group["_parsed_dt"].diff()
            if (ts_diff < pd.Timedelta(0)).any():
                report.add_issue(
                    rule="monotonic_tick_timestamps",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Tick timestamps for {inst} are not monotonic."
                    ),
                    instrument=inst,
                )

        report.summary = {
            "rows": len(df),
            "errors": report.error_count,
            "warnings": report.warning_count,
        }

        if strict and not report.is_valid:
            error_msgs = "; ".join(
                iss.message
                for iss in report.issues
                if iss.severity == ValidationSeverity.ERROR
            )
            raise DataContractError(
                f"Tick data validation failed for {source}: {error_msgs}",
                report,
            )

        return report

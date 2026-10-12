from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aiminer.core.data_contract import (
    DataContractError,
    DataContractValidator,
    DataValidationReport,
    MarketDepthContract,
    OHLCVContract,
    TickContract,
    ValidationSeverity,
)


def _make_valid_ohlcv() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.DataFrame(
        {
            "datetime": dates,
            "instrument": ["AAPL"] * 5,
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [105.0, 106.0, 107.0, 108.0, 109.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [102.0, 103.0, 104.0, 105.0, 106.0],
            "volume": [1000.0, 1500.0, 1200.0, 1800.0, 1600.0],
        }
    )


def test_valid_ohlcv_passes():
    df = _make_valid_ohlcv()
    report = DataContractValidator.validate_ohlcv(
        df, strict=True, check_calendar_gaps=False
    )
    assert report.is_valid is True
    assert report.error_count == 0
    assert report.row_count == 5


def test_empty_dataframe_rejected():
    df = pd.DataFrame()
    with pytest.raises(DataContractError, match="dataset is empty"):
        DataContractValidator.validate_ohlcv(df, strict=True)

    report = DataContractValidator.validate_ohlcv(df, strict=False)
    assert report.is_valid is False
    assert report.error_count > 0


def test_missing_required_columns():
    df = pd.DataFrame({"open": [10.0], "close": [11.0]})
    with pytest.raises(DataContractError, match="missing required columns"):
        DataContractValidator.validate_ohlcv(df, strict=True)


def test_infinite_and_nan_detected():
    df = _make_valid_ohlcv()
    df.loc[0, "close"] = np.inf
    df.loc[1, "open"] = np.nan

    with pytest.raises(DataContractError) as exc_info:
        DataContractValidator.validate_ohlcv(
            df, strict=True, check_calendar_gaps=False
        )
    assert "infinite values" in str(exc_info.value) or "NaN" in str(
        exc_info.value
    )

    report = DataContractValidator.validate_ohlcv(
        df, strict=False, check_calendar_gaps=False
    )
    assert report.is_valid is False
    rules = [iss.rule for iss in report.issues]
    assert "no_infinite_values" in rules
    assert "no_nan_values" in rules


def test_price_invariants_high_lower_than_low():
    df = _make_valid_ohlcv()
    df.loc[2, "high"] = 90.0  # low is 101.0
    with pytest.raises(DataContractError, match="high >= low"):
        DataContractValidator.validate_ohlcv(
            df, strict=True, check_calendar_gaps=False
        )


def test_price_invariants_close_outside_high_low():
    df = _make_valid_ohlcv()
    df.loc[0, "close"] = 120.0  # high is 105.0
    with pytest.raises(DataContractError, match="open/close outside"):
        DataContractValidator.validate_ohlcv(
            df, strict=True, check_calendar_gaps=False
        )


def test_negative_volume():
    df = _make_valid_ohlcv()
    df.loc[1, "volume"] = -50.0
    with pytest.raises(DataContractError, match="negative volume"):
        DataContractValidator.validate_ohlcv(
            df, strict=True, check_calendar_gaps=False
        )


def test_duplicate_keys():
    df = _make_valid_ohlcv()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    with pytest.raises(DataContractError, match="duplicate"):
        DataContractValidator.validate_ohlcv(
            df, strict=True, check_calendar_gaps=False
        )


def test_forward_survivorship_cutoff_leakage():
    df = _make_valid_ohlcv()
    cutoff = "2024-01-03"
    with pytest.raises(DataContractError, match="future_cutoff_leakage"):
        DataContractValidator.validate_ohlcv(
            df, cutoff_date=cutoff, strict=True, check_calendar_gaps=False
        )


def test_forward_survivorship_pre_listing():
    df = _make_valid_ohlcv()
    listing_dates = {"AAPL": "2024-01-03"}
    with pytest.raises(DataContractError, match="pre_listing_survivorship"):
        DataContractValidator.validate_ohlcv(
            df,
            listing_dates=listing_dates,
            strict=True,
            check_calendar_gaps=False,
        )


def test_calendar_gap_detection():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-15"])
    gaps = DataContractValidator.detect_missing_dates(
        dates, max_allowed_gap_days=4
    )
    assert len(gaps) == 1
    assert gaps[0]["gap_days"] == 13


def test_market_depth_valid_and_crossed_book():
    depth_df = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="min"),
            "instrument": ["AAPL"] * 3,
            "bid_price_1": [100.0, 100.1, 100.2],
            "ask_price_1": [100.1, 100.2, 100.3],
            "bid_price_2": [99.9, 100.0, 100.1],
            "ask_price_2": [100.2, 100.3, 100.4],
            "bid_vol_1": [10, 20, 30],
            "ask_vol_1": [15, 25, 35],
        }
    )
    report = DataContractValidator.validate_market_depth(depth_df, strict=True)
    assert report.is_valid is True

    # Crossed book: ask_price_1 <= bid_price_1
    bad_depth = depth_df.copy()
    bad_depth.loc[0, "ask_price_1"] = 99.5
    with pytest.raises(DataContractError, match="crossed book"):
        DataContractValidator.validate_market_depth(bad_depth, strict=True)


def test_market_depth_monotonic_ladder_violation():
    depth_df = pd.DataFrame(
        {
            "bid_price_1": [100.0],
            "ask_price_1": [101.0],
            "bid_price_2": [100.5],  # bad: bid_2 > bid_1
            "ask_price_2": [102.0],
            "bid_vol_1": [10],
            "ask_vol_1": [10],
        }
    )
    with pytest.raises(DataContractError, match="bid ladder"):
        DataContractValidator.validate_market_depth(depth_df, strict=True)


def test_tick_data_valid_and_non_monotonic_timestamps():
    ticks = pd.DataFrame(
        {
            "datetime": [
                "2024-01-01 09:30:00",
                "2024-01-01 09:30:01",
                "2024-01-01 09:30:02",
            ],
            "instrument": ["AAPL", "AAPL", "AAPL"],
            "price": [100.0, 100.1, 100.05],
            "volume": [100, 200, 150],
        }
    )
    report = DataContractValidator.validate_tick_data(ticks, strict=True)
    assert report.is_valid is True

    bad_ticks = ticks.copy()
    bad_ticks.loc[1, "datetime"] = "2024-01-01 09:29:59"
    with pytest.raises(DataContractError, match="not monotonic"):
        DataContractValidator.validate_tick_data(bad_ticks, strict=True)


def test_pydantic_contracts_instantiation():
    ohlcv = OHLCVContract(
        datetime="2024-01-01T09:30:00",
        instrument="AAPL",
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1000.0,
    )
    assert ohlcv.instrument == "AAPL"

    depth = MarketDepthContract(
        datetime="2024-01-01T09:30:00",
        instrument="AAPL",
        bid_price_1=100.0,
        ask_price_1=100.5,
        bid_vol_1=50,
        ask_vol_1=60,
    )
    assert depth.bid_price_1 == 100.0

    tick = TickContract(
        datetime="2024-01-01T09:30:00",
        instrument="AAPL",
        price=101.5,
        volume=25.0,
    )
    assert tick.price == 101.5


def test_forward_survivorship_intraday_on_cutoff_date_allowed():
    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                ["2024-01-01 15:00:00", "2024-01-02 15:00:00"]
            ),
            "instrument": ["AAPL", "AAPL"],
            "open": [10.0, 10.0],
            "high": [11.0, 11.0],
            "low": [9.0, 9.0],
            "close": [10.5, 10.5],
            "volume": [100.0, 100.0],
        }
    )
    rep = DataContractValidator.validate_ohlcv(
        df, cutoff_date="2024-01-02", strict=True, check_calendar_gaps=False
    )
    assert rep.is_valid is True
    assert rep.error_count == 0


def test_forward_survivorship_timezone_aware():
    df = pd.DataFrame(
        {
            "datetime": (
                pd.to_datetime(["2024-01-01", "2024-01-02"])
                .tz_localize("UTC")
            ),
            "instrument": ["AAPL", "AAPL"],
            "open": [10.0, 10.0],
            "high": [11.0, 11.0],
            "low": [9.0, 9.0],
            "close": [10.5, 10.5],
            "volume": [100.0, 100.0],
        }
    )
    rep = DataContractValidator.validate_ohlcv(
        df, cutoff_date="2024-01-05", strict=True, check_calendar_gaps=False
    )
    assert rep.is_valid is True


def test_missing_dates_with_non_consecutive_indices():
    s = pd.Series(
        ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-15"],
        index=[10, 20, 30, 40],
    )
    gaps = DataContractValidator.detect_missing_dates(s)
    assert len(gaps) == 1
    assert gaps[0]["gap_days"] == 13
    assert gaps[0]["previous_date"] == "2024-01-02 00:00:00"
    assert gaps[0]["resume_date"] == "2024-01-15 00:00:00"


def test_market_depth_negative_and_nan_prices_rejected():
    depth_neg = pd.DataFrame(
        {
            "bid_price_1": [-100.0],
            "ask_price_1": [-90.0],
            "bid_vol_1": [10],
            "ask_vol_1": [10],
        }
    )
    with pytest.raises(DataContractError, match="invalid bid_price_1"):
        DataContractValidator.validate_market_depth(depth_neg, strict=True)

    depth_nan = pd.DataFrame(
        {
            "bid_price_1": [np.nan],
            "ask_price_1": [100.0],
            "bid_vol_1": [10],
            "ask_vol_1": [10],
        }
    )
    with pytest.raises(DataContractError, match="invalid bid_price_1"):
        DataContractValidator.validate_market_depth(depth_nan, strict=True)


def test_tick_data_nat_timestamps_rejected():
    bad_ticks = pd.DataFrame(
        {
            "datetime": ["2024-01-01", "not_a_date"],
            "instrument": ["A", "A"],
            "price": [10.0, 10.5],
            "volume": [100, 100],
        }
    )
    with pytest.raises(DataContractError, match="invalid timestamps"):
        DataContractValidator.validate_tick_data(bad_ticks, strict=True)


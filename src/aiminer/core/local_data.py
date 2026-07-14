from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import pandas as pd


DATA_FILE_SUFFIXES = (".csv", ".parquet", ".pq")
PRICE_COLUMNS = ("open", "high", "low", "close")

_COLUMN_ALIASES = {
    "date": "datetime",
    "time": "datetime",
    "timestamp": "datetime",
    "symbol": "instrument",
    "ticker": "instrument",
    "asset": "instrument",
    "order_book_id": "instrument",
    "code": "instrument",
    "turnover": "total_turnover",
    "amount": "total_turnover",
    "value": "total_turnover",
    "money": "total_turnover",
}

_INSTRUMENT_COLUMN_NAMES = {
    name for name, canonical in _COLUMN_ALIASES.items() if canonical == "instrument"
} | {"instrument"}


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported local data file format: {path}")


def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for col in df.columns:
        key = str(col).strip()
        lower = key.lower()
        rename_map[col] = _COLUMN_ALIASES.get(lower, lower)
    return df.rename(columns=rename_map)


def ohlcv_quality_report(df: pd.DataFrame) -> dict[str, int]:
    """Return row-level OHLCV sanity counts for local market data."""
    if df.empty:
        return {
            "rows": 0,
            "invalid_rows": 0,
            "missing_ohlc": 0,
            "non_positive_ohlc": 0,
            "bad_high_low": 0,
            "negative_volume": 0,
        }

    price = df[list(PRICE_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    missing_ohlc = price.isna().any(axis=1)
    non_positive_ohlc = price.le(0).any(axis=1)
    bad_high_low = price["high"].lt(price[["open", "low", "close"]].max(axis=1)) | price[
        "low"
    ].gt(price[["open", "high", "close"]].min(axis=1))
    if "volume" in df.columns:
        volume = pd.to_numeric(df["volume"], errors="coerce")
        negative_volume = volume.lt(0) | volume.isna()
    else:
        negative_volume = pd.Series(True, index=df.index)

    invalid_rows = missing_ohlc | non_positive_ohlc | bad_high_low | negative_volume
    return {
        "rows": int(len(df)),
        "invalid_rows": int(invalid_rows.sum()),
        "missing_ohlc": int(missing_ohlc.sum()),
        "non_positive_ohlc": int(non_positive_ohlc.sum()),
        "bad_high_low": int(bad_high_low.sum()),
        "negative_volume": int(negative_volume.sum()),
    }


def validate_ohlcv_quality(df: pd.DataFrame, *, source: str = "local data") -> None:
    report = ohlcv_quality_report(df)
    if report["invalid_rows"] == 0:
        return
    raise ValueError(
        f"{source} has {report['invalid_rows']} invalid OHLCV row(s): "
        f"missing_ohlc={report['missing_ohlc']}, "
        f"non_positive_ohlc={report['non_positive_ohlc']}, "
        f"bad_high_low={report['bad_high_low']}, "
        f"negative_volume={report['negative_volume']}"
    )


def _ensure_schema(
    df: pd.DataFrame,
    *,
    market_profile: str,
    instrument_override: str | None = None,
    instrument_prefix: str | None = None,
) -> pd.DataFrame:
    df = _canonicalize_columns(df.copy())

    if instrument_override is not None:
        df["instrument"] = instrument_override

    if "datetime" not in df.columns:
        raise ValueError("Local data must contain a datetime/date/timestamp column.")
    if "instrument" not in df.columns:
        raise ValueError("Local data must contain an instrument/ticker/symbol column.")

    required_price_cols = {"open", "high", "low", "close", "volume"}
    missing = sorted(required_price_cols - set(df.columns))
    if missing:
        raise ValueError(
            f"Local data is missing required OHLCV columns: {', '.join(missing)}"
        )

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df[df["datetime"].notna()].copy()
    df["instrument"] = df["instrument"].astype(str).str.strip()
    df = df[df["instrument"] != ""].copy()

    if instrument_prefix:
        df["instrument"] = instrument_prefix + df["instrument"]

    if "market" not in df.columns:
        df["market"] = market_profile
    else:
        df["market"] = df["market"].astype(str).fillna(market_profile)

    df["asset_class"] = "futures" if market_profile == "futures" else "stock"

    if "vwap" not in df.columns:
        if "total_turnover" in df.columns:
            df["vwap"] = df["total_turnover"] / df["volume"].replace(0, pd.NA)
        else:
            df["vwap"] = df["close"]
    if "total_turnover" not in df.columns:
        df["total_turnover"] = df["vwap"].fillna(df["close"]) * df["volume"].fillna(0.0)

    for col in ("open", "high", "low", "close", "volume", "vwap", "total_turnover"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    validate_ohlcv_quality(df, source=f"local data ({market_profile})")

    keep = [
        "datetime",
        "instrument",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "vwap",
        "total_turnover",
        "market",
        "asset_class",
    ]
    for col in keep:
        if col not in df.columns:
            df[col] = pd.NA
    return df[keep]


def _iter_data_files(path: Path) -> Iterable[Path]:
    for child in sorted(path.iterdir()):
        if child.is_file() and child.suffix.lower() in DATA_FILE_SUFFIXES:
            yield child


def _has_instrument_column(path: Path) -> bool:
    table = _read_table(path)
    columns = {str(col).strip().lower() for col in table.columns}
    return bool(columns & _INSTRUMENT_COLUMN_NAMES)


def infer_layout(path: Path) -> str:
    if path.is_file():
        return "panel"
    files = list(_iter_data_files(path))
    if not files:
        raise FileNotFoundError(f"No CSV/Parquet files found under {path}")
    if len(files) == 1:
        return "panel" if _has_instrument_column(files[0]) else "instrument_files"

    has_instrument = [_has_instrument_column(file_path) for file_path in files]
    if all(has_instrument):
        return "panel"
    if not any(has_instrument):
        return "instrument_files"
    raise ValueError(
        "Ambiguous local data directory: panel files include an instrument column, "
        "instrument_files omit it and use filenames as instruments. Do not mix both "
        "semantics in one auto-detected directory."
    )


def resolve_local_profile_path(base_path: str | os.PathLike[str], market_profile: str) -> Path:
    root = Path(base_path).expanduser()
    if root.is_dir():
        profile_dir = root / market_profile
        if profile_dir.exists():
            return profile_dir
    return root


def load_local_ohlcv(
    path: str | os.PathLike[str],
    *,
    market_profile: str,
    layout: str = "auto",
    start_date: str | None = None,
    end_date: str | None = None,
    instrument_prefix: str | None = None,
) -> pd.DataFrame:
    source = Path(path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"Local data path does not exist: {source}")

    effective_layout = infer_layout(source) if layout == "auto" else layout
    if effective_layout not in {"panel", "instrument_files"}:
        raise ValueError(
            f"Unsupported local data layout '{effective_layout}'. Expected auto, panel, or instrument_files."
        )

    frames: list[pd.DataFrame] = []
    if effective_layout == "panel":
        if source.is_dir():
            files = list(_iter_data_files(source))
            if not files:
                raise FileNotFoundError(f"No local data files found in {source}")
            for file_path in files:
                try:
                    frames.append(
                        _ensure_schema(
                            _read_table(file_path),
                            market_profile=market_profile,
                            instrument_prefix=instrument_prefix,
                        )
                    )
                except ValueError as exc:
                    raise ValueError(
                        "panel layout treats every file in a directory as a panel shard "
                        f"and requires an instrument column; {file_path.name}: {exc}"
                    ) from exc
        else:
            frames.append(
                _ensure_schema(
                    _read_table(source),
                    market_profile=market_profile,
                    instrument_prefix=instrument_prefix,
                )
            )
    else:
        if not source.is_dir():
            raise ValueError("instrument_files layout requires a directory input.")
        files = list(_iter_data_files(source))
        if not files:
            raise FileNotFoundError(f"No instrument files found in {source}")
        for file_path in files:
            table = _read_table(file_path)
            frames.append(
                _ensure_schema(
                    table,
                    market_profile=market_profile,
                    instrument_override=file_path.stem,
                    instrument_prefix=instrument_prefix,
                )
            )

    df = pd.concat(frames, ignore_index=True)
    if start_date:
        df = df[df["datetime"] >= pd.Timestamp(start_date)]
    if end_date:
        df = df[df["datetime"] <= pd.Timestamp(end_date)]

    if df.empty:
        raise ValueError(
            f"Local dataset at {source} contains no rows after date filtering."
        )

    df = (
        df.sort_values(["datetime", "instrument"])
        .drop_duplicates(subset=["datetime", "instrument"], keep="last")
        .set_index(["datetime", "instrument"])
        .sort_index()
    )
    return df

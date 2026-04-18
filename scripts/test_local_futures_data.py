from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.local_data import load_local_ohlcv


CONTRACT_REQUIRED_COLUMNS = {
    "datetime",
    "instrument",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "total_turnover",
    "open_interest",
    "market",
    "asset_class",
    "underlying_symbol",
    "exchange",
}

DOMINANT_REQUIRED_COLUMNS = CONTRACT_REQUIRED_COLUMNS | {"dominant_contract"}
DEFAULT_UNDERLYINGS = ("IF", "IH", "IC", "IM")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read_parquet(path: Path) -> pd.DataFrame:
    _assert(path.exists(), f"Missing file: {path}")
    df = pd.read_parquet(path)
    _assert(not df.empty, f"Empty parquet file: {path}")
    return df


def validate_contract_file(path: Path) -> dict[str, object]:
    df = _read_parquet(path)
    missing = sorted(CONTRACT_REQUIRED_COLUMNS - set(df.columns))
    _assert(not missing, f"{path} missing columns: {', '.join(missing)}")
    dt = pd.to_datetime(df["datetime"], errors="coerce")
    _assert(dt.notna().all(), f"{path} has invalid datetime values")
    _assert(dt.is_monotonic_increasing, f"{path} datetime is not ascending")
    _assert(df["datetime"].nunique() == len(df), f"{path} has duplicate datetime rows")
    _assert(df["instrument"].astype(str).nunique() == 1, f"{path} contains multiple instruments")
    return {
        "path": str(path),
        "rows": len(df),
        "instrument": str(df["instrument"].iloc[0]),
        "start": str(dt.min()),
        "end": str(dt.max()),
    }


def validate_dominant_file(path: Path, underlying: str) -> dict[str, object]:
    df = _read_parquet(path)
    missing = sorted(DOMINANT_REQUIRED_COLUMNS - set(df.columns))
    _assert(not missing, f"{path} missing columns: {', '.join(missing)}")
    dt = pd.to_datetime(df["datetime"], errors="coerce")
    _assert(dt.notna().all(), f"{path} has invalid datetime values")
    _assert(dt.is_monotonic_increasing, f"{path} datetime is not ascending")
    _assert(df["datetime"].nunique() == len(df), f"{path} has duplicate datetime rows")
    _assert(df["instrument"].astype(str).nunique() == 1, f"{path} contains multiple instruments")
    _assert(str(df["instrument"].iloc[0]) == underlying, f"{path} instrument is not {underlying}")
    _assert(df["dominant_contract"].astype(str).str.startswith(underlying).all(), f"{path} has wrong dominant contract prefix")
    return {
        "path": str(path),
        "rows": len(df),
        "instrument": underlying,
        "start": str(dt.min()),
        "end": str(dt.max()),
    }


def validate_local_loader(contracts_dir: Path) -> dict[str, object]:
    df = load_local_ohlcv(
        contracts_dir,
        market_profile="futures",
        layout="instrument_files",
    )
    _assert(df.index.names == ["datetime", "instrument"], "load_local_ohlcv index names mismatch")
    _assert(len(df) > 0, "load_local_ohlcv returned empty dataframe")
    for column in ("open", "high", "low", "close", "volume", "vwap", "total_turnover", "market", "asset_class"):
        _assert(column in df.columns, f"load_local_ohlcv missing column: {column}")
    return {
        "rows": len(df),
        "instruments": int(df.index.get_level_values("instrument").nunique()),
        "start": str(df.index.get_level_values("datetime").min()),
        "end": str(df.index.get_level_values("datetime").max()),
    }


def run_suite(root: Path, *, check_1m: bool) -> dict[str, object]:
    contracts_1d = root / "contracts" / "1d"
    dominant_1d = root / "dominant" / "1d"
    _assert(contracts_1d.exists(), f"Missing directory: {contracts_1d}")
    _assert(dominant_1d.exists(), f"Missing directory: {dominant_1d}")

    summaries: dict[str, object] = {}
    contract_files_1d = sorted(contracts_1d.glob("*.parquet"))
    _assert(contract_files_1d, f"No parquet files found in {contracts_1d}")
    summaries["contracts_1d_count"] = len(contract_files_1d)
    summaries["contracts_1d_sample"] = validate_contract_file(contract_files_1d[0])

    dominant_summaries = {}
    for underlying in DEFAULT_UNDERLYINGS:
        path = dominant_1d / f"{underlying}.parquet"
        dominant_summaries[underlying] = validate_dominant_file(path, underlying)
    summaries["dominant_1d"] = dominant_summaries
    summaries["local_loader_1d"] = validate_local_loader(contracts_1d)

    if check_1m:
        contracts_1m = root / "contracts" / "1m"
        dominant_1m = root / "dominant" / "1m"
        _assert(contracts_1m.exists(), f"Missing directory: {contracts_1m}")
        _assert(dominant_1m.exists(), f"Missing directory: {dominant_1m}")
        contract_files_1m = sorted(contracts_1m.glob("*.parquet"))
        _assert(contract_files_1m, f"No parquet files found in {contracts_1m}")
        summaries["contracts_1m_count"] = len(contract_files_1m)
        summaries["contracts_1m_sample"] = validate_contract_file(contract_files_1m[0])
        dominant_1m_summaries = {}
        for underlying in DEFAULT_UNDERLYINGS:
            path = dominant_1m / f"{underlying}.parquet"
            dominant_1m_summaries[underlying] = validate_dominant_file(path, underlying)
        summaries["dominant_1m"] = dominant_1m_summaries

    manifest = root / "manifests" / "download_manifest.json"
    _assert(manifest.exists(), f"Missing manifest: {manifest}")
    summaries["manifest"] = str(manifest)
    return summaries


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate downloaded local futures parquet data.")
    parser.add_argument("--root", default="data/local_futures")
    parser.add_argument("--skip-1m", action="store_true", help="Only validate 1d contracts and dominant files.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    root = Path(args.root).expanduser()
    try:
        summary = run_suite(root, check_1m=not args.skip_1m)
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[PASS] local futures dataset validation succeeded")
    print(f"root: {root}")
    print(f"contracts/1d files: {summary['contracts_1d_count']}")
    if "contracts_1m_count" in summary:
        print(f"contracts/1m files: {summary['contracts_1m_count']}")

    sample_1d = summary["contracts_1d_sample"]
    print(
        "sample 1d contract:",
        sample_1d["instrument"],
        sample_1d["start"],
        "->",
        sample_1d["end"],
        f"rows={sample_1d['rows']}",
    )
    loader = summary["local_loader_1d"]
    print(
        "local loader 1d:",
        f"rows={loader['rows']}",
        f"instruments={loader['instruments']}",
        loader["start"],
        "->",
        loader["end"],
    )
    print(f"manifest: {summary['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

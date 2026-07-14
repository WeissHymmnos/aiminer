from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aiminer.core.local_data import load_local_ohlcv
from aiminer.core.local_data import ohlcv_quality_report, validate_ohlcv_quality


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
    validate_ohlcv_quality(df, source=str(path))
    quality = ohlcv_quality_report(df)
    return {
        "path": str(path),
        "rows": len(df),
        "instrument": str(df["instrument"].iloc[0]),
        "start": str(dt.min()),
        "end": str(dt.max()),
        "quality": quality,
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
    validate_ohlcv_quality(df, source=str(path))
    quality = ohlcv_quality_report(df)
    return {
        "path": str(path),
        "rows": len(df),
        "instrument": underlying,
        "start": str(dt.min()),
        "end": str(dt.max()),
        "quality": quality,
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
    quality = ohlcv_quality_report(df.reset_index())
    _assert(quality["invalid_rows"] == 0, f"load_local_ohlcv returned invalid OHLCV rows: {quality}")
    return {
        "rows": len(df),
        "instruments": int(df.index.get_level_values("instrument").nunique()),
        "start": str(df.index.get_level_values("datetime").min()),
        "end": str(df.index.get_level_values("datetime").max()),
        "quality": quality,
    }


def _validate_all_contract_files(paths: list[Path]) -> list[dict[str, object]]:
    return [validate_contract_file(path) for path in paths]


def _load_manifest(root: Path) -> dict[str, object]:
    manifest = root / "manifests" / "download_manifest.json"
    if not manifest.exists():
        return {}
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _dominant_underlyings_for_frequency(
    root: Path,
    *,
    manifest_payload: dict[str, object],
    frequency: str,
) -> tuple[list[str], dict[str, str]]:
    runs = [run for run in (manifest_payload.get("runs") or []) if isinstance(run, dict)]
    requested: list[str] = []
    for run in reversed(runs):
        results = [
            item
            for item in (run.get("dominant_results") or [])
            if item.get("frequency") == frequency
        ]
        if results:
            requested = [str(item.get("underlying")).upper() for item in results]
            break
    if not requested:
        last_request = manifest_payload.get("last_request")
        if isinstance(last_request, dict):
            requested = [str(item).upper() for item in (last_request.get("underlyings") or [])]
    requested = requested or list(DEFAULT_UNDERLYINGS)

    statuses: dict[str, str] = {}
    for run in reversed(runs):
        for item in run.get("dominant_results") or []:
            if item.get("frequency") != frequency:
                continue
            underlying = str(item.get("underlying")).upper()
            statuses.setdefault(underlying, str(item.get("status")))
    dominant_dir = root / "dominant" / frequency
    underlyings: list[str] = []
    skipped: dict[str, str] = {}
    for underlying in requested:
        path = dominant_dir / f"{underlying}.parquet"
        status = statuses.get(underlying)
        if status == "empty" and not path.exists():
            skipped[underlying] = "empty"
            continue
        if status is None and not path.exists():
            skipped[underlying] = "missing_without_manifest_status"
            continue
        underlyings.append(underlying)
    return underlyings, skipped


def run_suite(root: Path, *, check_1m: bool) -> dict[str, object]:
    contracts_1d = root / "contracts" / "1d"
    dominant_1d = root / "dominant" / "1d"
    _assert(contracts_1d.exists(), f"Missing directory: {contracts_1d}")
    _assert(dominant_1d.exists(), f"Missing directory: {dominant_1d}")
    manifest_payload = _load_manifest(root)

    summaries: dict[str, object] = {}
    contract_files_1d = sorted(contracts_1d.glob("*.parquet"))
    _assert(contract_files_1d, f"No parquet files found in {contracts_1d}")
    summaries["contracts_1d_count"] = len(contract_files_1d)
    summaries["contracts_1d_files"] = _validate_all_contract_files(contract_files_1d)
    summaries["contracts_1d_sample"] = summaries["contracts_1d_files"][0]

    dominant_summaries = {}
    dominant_underlyings_1d, skipped_1d = _dominant_underlyings_for_frequency(
        root, manifest_payload=manifest_payload, frequency="1d"
    )
    _assert(dominant_underlyings_1d, f"No dominant 1d files expected/found in {dominant_1d}")
    for underlying in dominant_underlyings_1d:
        path = dominant_1d / f"{underlying}.parquet"
        dominant_summaries[underlying] = validate_dominant_file(path, underlying)
    summaries["dominant_1d"] = dominant_summaries
    summaries["dominant_1d_skipped"] = skipped_1d
    summaries["local_loader_1d"] = validate_local_loader(contracts_1d)

    if check_1m:
        contracts_1m = root / "contracts" / "1m"
        dominant_1m = root / "dominant" / "1m"
        _assert(contracts_1m.exists(), f"Missing directory: {contracts_1m}")
        _assert(dominant_1m.exists(), f"Missing directory: {dominant_1m}")
        contract_files_1m = sorted(contracts_1m.glob("*.parquet"))
        _assert(contract_files_1m, f"No parquet files found in {contracts_1m}")
        summaries["contracts_1m_count"] = len(contract_files_1m)
        summaries["contracts_1m_files"] = _validate_all_contract_files(contract_files_1m)
        summaries["contracts_1m_sample"] = summaries["contracts_1m_files"][0]
        dominant_1m_summaries = {}
        dominant_underlyings_1m, skipped_1m = _dominant_underlyings_for_frequency(
            root, manifest_payload=manifest_payload, frequency="1m"
        )
        _assert(dominant_underlyings_1m, f"No dominant 1m files expected/found in {dominant_1m}")
        for underlying in dominant_underlyings_1m:
            path = dominant_1m / f"{underlying}.parquet"
            dominant_1m_summaries[underlying] = validate_dominant_file(path, underlying)
        summaries["dominant_1m"] = dominant_1m_summaries
        summaries["dominant_1m_skipped"] = skipped_1m

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

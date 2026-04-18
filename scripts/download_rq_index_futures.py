from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import rqdatac as rq
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.alphaeval.rq_eval import init_rq_auth
from scripts.test_local_futures_data import run_suite


DEFAULT_UNDERLYINGS = ("IF", "IH", "IC", "IM")
DEFAULT_FIELDS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "total_turnover",
    "open_interest",
]


@dataclass(frozen=True)
class ContractMeta:
    order_book_id: str
    underlying_symbol: str
    exchange: str
    listed_date: pd.Timestamp | None
    de_listed_date: pd.Timestamp | None


def _parse_csv_arg(value: str | None, *, default: Iterable[str]) -> list[str]:
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _coerce_timestamp(value: Any) -> pd.Timestamp | None:
    if value is None or value == "":
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts)


def _date_column_name(df: pd.DataFrame) -> str:
    for candidate in ("datetime", "date", "trading_date"):
        if candidate in df.columns:
            return candidate
    first = df.columns[0]
    return str(first)


def _normalize_price_frame(
    raw: pd.DataFrame | pd.Series,
    *,
    instrument: str,
    underlying_symbol: str,
    exchange: str,
) -> pd.DataFrame:
    if raw is None:
        return pd.DataFrame()
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    if raw.empty:
        return pd.DataFrame()

    df = raw.copy()
    if isinstance(df.index, pd.MultiIndex):
        index_names = [name or f"level_{i}" for i, name in enumerate(df.index.names)]
        df.index.names = index_names
        df = df.reset_index()
    else:
        df = df.reset_index()

    date_col = _date_column_name(df)
    rename_map = {date_col: "datetime"}
    if "order_book_id" in df.columns:
        rename_map["order_book_id"] = "instrument"
    df = df.rename(columns=rename_map)

    if "instrument" not in df.columns:
        df["instrument"] = instrument

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df[df["datetime"].notna()].copy()
    df["instrument"] = instrument
    df["market"] = "futures"
    df["asset_class"] = "futures"
    df["underlying_symbol"] = underlying_symbol
    df["exchange"] = exchange

    if "total_turnover" not in df.columns:
        df["total_turnover"] = pd.NA
    if "open_interest" not in df.columns:
        df["open_interest"] = pd.NA

    keep = [
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
    ]
    for col in keep:
        if col not in df.columns:
            df[col] = pd.NA
    return df[keep].sort_values("datetime").drop_duplicates(subset=["datetime"], keep="last")


def discover_contracts(
    *,
    underlyings: list[str],
    start: str,
    end: str,
) -> list[ContractMeta]:
    instruments = rq.all_instruments(type="Future", market="cn")
    if instruments is None or instruments.empty:
        return []

    df = instruments.copy()
    if "underlying_symbol" not in df.columns:
        raise ValueError("rq.all_instruments(type='Future') missing underlying_symbol column.")
    if "order_book_id" not in df.columns:
        raise ValueError("rq.all_instruments(type='Future') missing order_book_id column.")

    df["underlying_symbol"] = df["underlying_symbol"].astype(str).str.upper()
    df = df[df["underlying_symbol"].isin([item.upper() for item in underlyings])].copy()

    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if "listed_date" in df.columns:
        df["listed_date"] = pd.to_datetime(df["listed_date"], errors="coerce")
    else:
        df["listed_date"] = pd.NaT
    if "de_listed_date" in df.columns:
        df["de_listed_date"] = pd.to_datetime(df["de_listed_date"], errors="coerce")
    else:
        df["de_listed_date"] = pd.NaT

    df = df[(df["de_listed_date"].isna()) | (df["de_listed_date"] >= start_ts)].copy()
    df = df[(df["listed_date"].isna()) | (df["listed_date"] <= end_ts)].copy()

    exchange_col = "exchange"
    if exchange_col not in df.columns:
        df[exchange_col] = ""

    df = df.sort_values(["underlying_symbol", "listed_date", "order_book_id"])
    return [
        ContractMeta(
            order_book_id=str(row.order_book_id),
            underlying_symbol=str(row.underlying_symbol),
            exchange=str(getattr(row, exchange_col, "") or ""),
            listed_date=_coerce_timestamp(getattr(row, "listed_date", None)),
            de_listed_date=_coerce_timestamp(getattr(row, "de_listed_date", None)),
        )
        for row in df.itertuples(index=False)
    ]


def contract_file_path(output_root: Path, frequency: str, instrument: str) -> Path:
    return output_root / "contracts" / frequency / f"{instrument}.parquet"


def dominant_file_path(output_root: Path, frequency: str, underlying: str) -> Path:
    return output_root / "dominant" / frequency / f"{underlying}.parquet"


def manifest_file_path(output_root: Path) -> Path:
    return output_root / "manifests" / "download_manifest.json"


def _existing_max_datetime(path: Path) -> pd.Timestamp | None:
    if not path.exists():
        return None
    df = pd.read_parquet(path, columns=["datetime"])
    if df.empty:
        return None
    dt = pd.to_datetime(df["datetime"], errors="coerce").dropna()
    if dt.empty:
        return None
    return pd.Timestamp(dt.max())


def _next_start_after(last_dt: pd.Timestamp | None, frequency: str) -> pd.Timestamp | None:
    if last_dt is None:
        return None
    if frequency == "1d":
        return last_dt.normalize() + pd.Timedelta(days=1)
    return last_dt + pd.Timedelta(minutes=1)


def _effective_contract_window(
    meta: ContractMeta,
    *,
    requested_start: pd.Timestamp,
    requested_end: pd.Timestamp,
    existing_max_dt: pd.Timestamp | None,
    frequency: str,
) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    start = requested_start
    if meta.listed_date is not None:
        start = max(start, meta.listed_date.normalize())
    if existing_max_dt is not None:
        next_start = _next_start_after(existing_max_dt, frequency)
        if next_start is not None:
            start = max(start, next_start)

    end = requested_end
    if meta.de_listed_date is not None:
        end = min(end, meta.de_listed_date)

    if start > end:
        return None
    return start, end


def _merge_and_write_parquet(path: Path, new_df: pd.DataFrame) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = pd.read_parquet(path)
        merged = pd.concat([existing, new_df], ignore_index=True)
    else:
        merged = new_df.copy()

    merged["datetime"] = pd.to_datetime(merged["datetime"], errors="coerce")
    merged = (
        merged[merged["datetime"].notna()]
        .sort_values("datetime")
        .drop_duplicates(subset=["datetime"], keep="last")
    )
    merged.to_parquet(path, index=False)
    return len(merged)


def download_contract_data(
    meta: ContractMeta,
    *,
    output_root: Path,
    frequency: str,
    start: str,
    end: str,
    dry_run: bool = False,
    full_refresh: bool = False,
) -> dict[str, Any]:
    path = contract_file_path(output_root, frequency, meta.order_book_id)
    requested_start = pd.Timestamp(start)
    requested_end = pd.Timestamp(end)
    existing_max_dt = None if full_refresh else _existing_max_datetime(path)
    window = _effective_contract_window(
        meta,
        requested_start=requested_start,
        requested_end=requested_end,
        existing_max_dt=existing_max_dt,
        frequency=frequency,
    )
    if window is None:
        return {
            "instrument": meta.order_book_id,
            "frequency": frequency,
            "path": str(path),
            "status": "up_to_date",
            "rows_written": 0,
        }

    fetch_start, fetch_end = window
    if dry_run:
        return {
            "instrument": meta.order_book_id,
            "frequency": frequency,
            "path": str(path),
            "status": "dry_run",
            "rows_written": 0,
            "fetch_start": fetch_start.isoformat(),
            "fetch_end": fetch_end.isoformat(),
        }

    raw = rq.get_price(
        meta.order_book_id,
        start_date=fetch_start,
        end_date=fetch_end,
        frequency=frequency,
        fields=DEFAULT_FIELDS,
        market="cn",
        expect_df=True,
    )
    frame = _normalize_price_frame(
        raw,
        instrument=meta.order_book_id,
        underlying_symbol=meta.underlying_symbol,
        exchange=meta.exchange,
    )
    if frame.empty:
        return {
            "instrument": meta.order_book_id,
            "frequency": frequency,
            "path": str(path),
            "status": "empty",
            "rows_written": 0,
        }

    if full_refresh and path.exists():
        path.unlink()
    row_count = _merge_and_write_parquet(path, frame)
    return {
        "instrument": meta.order_book_id,
        "frequency": frequency,
        "path": str(path),
        "status": "written",
        "rows_written": row_count,
    }


def _dominant_mapping_frame(underlying: str, *, start: str, end: str, rule: int, rank: int) -> pd.DataFrame:
    raw = rq.get_dominant_future(
        underlying,
        start_date=start,
        end_date=end,
        rule=rule,
        rank=rank,
        market="cn",
    )
    if raw is None:
        return pd.DataFrame(columns=["date", "dominant_contract"])

    if isinstance(raw, pd.Series):
        mapping = raw.rename("dominant_contract").reset_index()
    else:
        mapping = raw.copy().reset_index()
        if "dominant_contract" not in mapping.columns:
            if underlying in mapping.columns:
                mapping = mapping.rename(columns={underlying: "dominant_contract"})
            else:
                value_col = [col for col in mapping.columns if col not in {"date", "datetime", "trading_date"}]
                if len(value_col) != 1:
                    raise ValueError(f"Unable to infer dominant contract column for {underlying}.")
                mapping = mapping.rename(columns={value_col[0]: "dominant_contract"})

    date_col = _date_column_name(mapping)
    mapping = mapping.rename(columns={date_col: "date"})
    mapping["date"] = pd.to_datetime(mapping["date"], errors="coerce").dt.normalize()
    mapping["dominant_contract"] = mapping["dominant_contract"].astype(str).str.strip()
    mapping = mapping[(mapping["date"].notna()) & (mapping["dominant_contract"] != "")]
    return mapping[["date", "dominant_contract"]].drop_duplicates(subset=["date"], keep="last")


def build_dominant_data(
    *,
    output_root: Path,
    underlying: str,
    frequency: str,
    start: str,
    end: str,
    rule: int,
    rank: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    path = dominant_file_path(output_root, frequency, underlying)
    mapping = _dominant_mapping_frame(underlying, start=start, end=end, rule=rule, rank=rank)
    if mapping.empty:
        return {
            "underlying": underlying,
            "frequency": frequency,
            "path": str(path),
            "status": "empty",
            "rows_written": 0,
        }

    if dry_run:
        return {
            "underlying": underlying,
            "frequency": frequency,
            "path": str(path),
            "status": "dry_run",
            "rows_written": 0,
            "contracts": sorted(mapping["dominant_contract"].unique().tolist()),
        }

    frames: list[pd.DataFrame] = []
    for contract in sorted(mapping["dominant_contract"].unique().tolist()):
        contract_path = contract_file_path(output_root, frequency, contract)
        if not contract_path.exists():
            raise FileNotFoundError(
                f"Missing contract file for dominant build: {contract_path}. Download contracts first."
            )
        contract_df = pd.read_parquet(contract_path)
        if contract_df.empty:
            continue
        contract_df["datetime"] = pd.to_datetime(contract_df["datetime"], errors="coerce")
        contract_df = contract_df[contract_df["datetime"].notna()].copy()
        contract_df["date"] = contract_df["datetime"].dt.normalize()
        contract_df["dominant_contract"] = contract
        frames.append(contract_df)

    if not frames:
        return {
            "underlying": underlying,
            "frequency": frequency,
            "path": str(path),
            "status": "empty",
            "rows_written": 0,
        }

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.merge(mapping, on=["date", "dominant_contract"], how="inner")
    merged["instrument"] = underlying
    keep = [
        "datetime",
        "instrument",
        "dominant_contract",
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
    ]
    merged = (
        merged[keep]
        .sort_values("datetime")
        .drop_duplicates(subset=["datetime"], keep="last")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(path, index=False)
    return {
        "underlying": underlying,
        "frequency": frequency,
        "path": str(path),
        "status": "written",
        "rows_written": len(merged),
    }


def load_manifest(output_root: Path) -> dict[str, Any]:
    path = manifest_file_path(output_root)
    if not path.exists():
        return {"runs": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"runs": []}


def save_manifest(output_root: Path, payload: dict[str, Any]) -> None:
    path = manifest_file_path(output_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def update_manifest(
    output_root: Path,
    *,
    contract_results: list[dict[str, Any]],
    dominant_results: list[dict[str, Any]],
    frequencies: list[str],
    underlyings: list[str],
    start: str,
    end: str,
) -> dict[str, Any]:
    payload = load_manifest(output_root)
    payload["last_run_at"] = datetime.utcnow().isoformat(timespec="seconds")
    payload["last_request"] = {
        "frequencies": frequencies,
        "underlyings": underlyings,
        "start": start,
        "end": end,
    }
    payload["runs"] = [
        *payload.get("runs", [])[-9:],
        {
            "ran_at": payload["last_run_at"],
            "contract_results": contract_results,
            "dominant_results": dominant_results,
        },
    ]
    payload["frequency_status"] = {}
    for frequency in frequencies:
        payload["frequency_status"][frequency] = {
            "contracts_written": sum(
                1 for item in contract_results if item.get("frequency") == frequency and item.get("status") == "written"
            ),
            "dominant_written": sum(
                1 for item in dominant_results if item.get("frequency") == frequency and item.get("status") == "written"
            ),
        }
    save_manifest(output_root, payload)
    return payload


def run_download(
    *,
    output_root: Path,
    start: str,
    end: str,
    frequencies: list[str],
    underlyings: list[str],
    contracts_only: bool = False,
    dominant_only: bool = False,
    dominant_rule: int = 0,
    dominant_rank: int = 1,
    full_refresh: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    if contracts_only and dominant_only:
        raise ValueError("contracts_only and dominant_only cannot both be true.")

    init_rq_auth()
    contracts = discover_contracts(underlyings=underlyings, start=start, end=end)
    contract_results: list[dict[str, Any]] = []
    dominant_results: list[dict[str, Any]] = []

    if not dominant_only:
        for frequency in frequencies:
            for meta in contracts:
                logger.info(f"Downloading {meta.order_book_id} ({frequency})")
                contract_results.append(
                    download_contract_data(
                        meta,
                        output_root=output_root,
                        frequency=frequency,
                        start=start,
                        end=end,
                        dry_run=dry_run,
                        full_refresh=full_refresh,
                    )
                )

    if not contracts_only:
        for frequency in frequencies:
            for underlying in underlyings:
                logger.info(f"Building dominant series {underlying} ({frequency})")
                dominant_results.append(
                    build_dominant_data(
                        output_root=output_root,
                        underlying=underlying,
                        frequency=frequency,
                        start=start,
                        end=end,
                        rule=dominant_rule,
                        rank=dominant_rank,
                        dry_run=dry_run,
                    )
                )

    manifest = None
    if not dry_run:
        manifest = update_manifest(
            output_root,
            contract_results=contract_results,
            dominant_results=dominant_results,
            frequencies=frequencies,
            underlyings=underlyings,
            start=start,
            end=end,
        )

    return {
        "contracts": contracts,
        "contract_results": contract_results,
        "dominant_results": dominant_results,
        "manifest": manifest,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download China index futures data from RiceQuant.")
    parser.add_argument("--output", default="data/local_futures")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m-%d"))
    parser.add_argument("--frequencies", default="1d,1m")
    parser.add_argument("--underlyings", default=",".join(DEFAULT_UNDERLYINGS))
    parser.add_argument("--contracts-only", action="store_true")
    parser.add_argument("--dominant-only", action="store_true")
    parser.add_argument("--dominant-rule", type=int, default=0)
    parser.add_argument("--dominant-rank", type=int, default=1)
    parser.add_argument("--full-refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--validate-skip-1m", action="store_true")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    payload = run_download(
        output_root=Path(args.output).expanduser(),
        start=args.start,
        end=args.end,
        frequencies=_parse_csv_arg(args.frequencies, default=["1d", "1m"]),
        underlyings=[item.upper() for item in _parse_csv_arg(args.underlyings, default=DEFAULT_UNDERLYINGS)],
        contracts_only=args.contracts_only,
        dominant_only=args.dominant_only,
        dominant_rule=args.dominant_rule,
        dominant_rank=args.dominant_rank,
        full_refresh=args.full_refresh,
        dry_run=args.dry_run,
    )
    logger.info(
        "Download finished: {} contract tasks, {} dominant tasks",
        len(payload["contract_results"]),
        len(payload["dominant_results"]),
    )
    if not args.dry_run and not args.skip_validate:
        logger.info("Running post-download validation for {}", args.output)
        summary = run_suite(
            Path(args.output).expanduser(),
            check_1m=not args.validate_skip_1m,
        )
        logger.info(
            "Validation passed: contracts/1d={}, contracts/1m={}",
            summary["contracts_1d_count"],
            summary.get("contracts_1m_count", 0),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

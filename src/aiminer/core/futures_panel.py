"""Build a tradable China-futures panel with session tags and roll marks.

Preferred sources, in order:
1. A cached dominant parquet written by a previous launch
2. ``mapping.zip`` + ``daily_*.zip`` under ``~/Documents/finance/data/raw`` (full book)
3. Dominant 1d parquets (``~/Documents/finance/research/llm/data/local_futures`` or repo)
4. ``~/Documents/finance/data/samples`` (user-stated path; currently has no futures bars)

``load_local_ohlcv`` drops ``dominant_contract``, so this loader keeps it.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Iterable
import zipfile

import pandas as pd

_CONTRACT_RE = re.compile(r"^([A-Za-z]+)")

# Day-session close used for the daily bar. Night session, when it exists,
# is attributed to the next trading date (exchange convention).
_CFFEX_EQUITY = {"IF", "IH", "IC", "IM"}
_CFFEX_BOND = {"T", "TF", "TS", "TL"}
_NIGHT_SESSION = {
    "AU",
    "AG",
    "CU",
    "AL",
    "ZN",
    "PB",
    "NI",
    "SN",
    "RB",
    "HC",
    "SS",
    "BU",
    "RU",
    "FU",
    "SP",
    "AO",
    "BR",
    "AD",
    "I",
    "J",
    "JM",
    "A",
    "M",
    "Y",
    "P",
    "PP",
    "L",
    "V",
    "EG",
    "EB",
    "PG",
    "C",
    "CS",
    "TA",
    "MA",
    "FG",
    "SA",
    "SR",
    "CF",
    "OI",
    "RM",
    "PF",
    "SH",
    "UR",
    "SF",
    "SM",
    "SC",
    "LU",
    "NR",
    "BC",
}


def session_close_time(product: str) -> str:
    key = str(product).upper()
    if key in _CFFEX_BOND:
        return "15:15"
    if key in _CFFEX_EQUITY:
        return "15:00"
    return "15:00"


def has_night_session(product: str) -> bool:
    return str(product).upper() in _NIGHT_SESSION


def default_data_candidates() -> list[Path]:
    home = Path.home()
    repo_data = Path(__file__).resolve().parents[3] / "data"
    return [
        home / "Documents" / "finance" / "data" / "samples",
        home / "Documents" / "finance" / "data" / "raw",
        home
        / "Documents"
        / "finance"
        / "research"
        / "llm"
        / "data"
        / "local_futures"
        / "dominant"
        / "1d",
        repo_data / "local_futures" / "dominant" / "1d",
        repo_data / "cache",
    ]


def _find_daily_zip(root: Path) -> Path | None:
    if (
        root.is_file()
        and root.suffix.lower() == ".zip"
        and "daily" in root.name.lower()
    ):
        return root
    if not root.is_dir():
        return None
    matches = sorted(root.glob("daily_*.zip"))
    return matches[0] if matches else None


def _find_mapping_zip(root: Path) -> Path | None:
    if root.is_file() and root.name.lower() == "mapping.zip":
        return root
    if not root.is_dir():
        return None
    candidate = root / "mapping.zip"
    return candidate if candidate.exists() else None


def _parse_mapping_symbol(mapping_symbol: str) -> tuple[str, str, str]:
    text = str(mapping_symbol).strip().upper()
    if "." in text:
        contract, exch = text.rsplit(".", 1)
    else:
        contract, exch = text, ""
    match = _CONTRACT_RE.match(contract)
    product = match.group(1) if match else contract
    return exch, product, contract


def _parse_trade_date(value: object) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        return value.normalize()
    text = str(value).strip()
    if text.isdigit() and len(text) == 8:
        return pd.Timestamp(text)
    return pd.Timestamp(text).normalize()


def _attach_session_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "product" in out.columns:
        products = out["product"].astype(str)
    elif "underlying_symbol" in out.columns:
        products = out["underlying_symbol"].astype(str)
    else:
        products = (
            out["instrument"]
            .astype(str)
            .str.extract(r"^([A-Za-z]+)", expand=False)
        )
    out["session_close"] = products.map(session_close_time)
    out["has_night_session"] = products.map(has_night_session)
    if "product" not in out.columns:
        out["product"] = products
    return out


def _mark_rolls(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["instrument", "datetime"]).copy()
    prev = out.groupby("instrument")["dominant_contract"].shift(1)
    out["is_roll"] = prev.notna() & prev.ne(out["dominant_contract"])
    return out


def _finalize_panel(df: pd.DataFrame) -> pd.DataFrame:
    required = {
        "datetime",
        "instrument",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Futures panel missing columns: {sorted(missing)}")
    out = df.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    out = out[out["datetime"].notna()].copy()
    out["instrument"] = out["instrument"].astype(str).str.strip().str.upper()
    if "dominant_contract" not in out.columns:
        out["dominant_contract"] = out["instrument"]
    out["dominant_contract"] = out["dominant_contract"].astype(str).str.strip()
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if "total_turnover" not in out.columns:
        if "turnover" in out.columns:
            out["total_turnover"] = pd.to_numeric(
                out["turnover"], errors="coerce"
            )
        else:
            out["total_turnover"] = out["close"] * out["volume"].fillna(0.0)
    else:
        out["total_turnover"] = pd.to_numeric(
            out["total_turnover"], errors="coerce"
        )
    out = out.dropna(subset=["open", "close"])
    out = out[out["close"] > 0]
    out = out[out["open"] > 0]
    out = _attach_session_columns(out)
    out = _mark_rolls(out)
    out = (
        out.sort_values(["datetime", "instrument"])
        .drop_duplicates(subset=["datetime", "instrument"], keep="last")
        .reset_index(drop=True)
    )
    return out


def load_dominant_parquets(path: Path) -> pd.DataFrame:
    files = sorted(path.glob("*.parquet")) if path.is_dir() else [path]
    files = [f for f in files if f.suffix.lower() in {".parquet", ".pq"}]
    if not files:
        raise FileNotFoundError(f"No parquet futures files under {path}")
    frames = [pd.read_parquet(f) for f in files]
    return _finalize_panel(pd.concat(frames, ignore_index=True))


def _read_mapping_zip(mapping_zip: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(mapping_zip) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            with zf.open(name) as handle:
                raw = pd.read_csv(handle)
            if raw.empty or "mapping_symbol" not in raw.columns:
                continue
            date_col = (
                "trade_date" if "trade_date" in raw.columns else raw.columns[1]
            )
            product_col = (
                "symbol" if "symbol" in raw.columns else raw.columns[0]
            )
            parsed = raw[[product_col, date_col, "mapping_symbol"]].copy()
            parsed.columns = ["product_symbol", "trade_date", "mapping_symbol"]
            parsed["datetime"] = parsed["trade_date"].map(_parse_trade_date)
            exch, product, contract = zip(
                *parsed["mapping_symbol"].map(_parse_mapping_symbol)
            )
            parsed["exchange"] = list(exch)
            parsed["instrument"] = list(product)
            parsed["dominant_contract"] = list(contract)
            frames.append(
                parsed[
                    [
                        "datetime",
                        "instrument",
                        "exchange",
                        "dominant_contract",
                        "mapping_symbol",
                    ]
                ]
            )
    if not frames:
        raise ValueError(f"No usable mapping CSVs in {mapping_zip}")
    mapping = pd.concat(frames, ignore_index=True)
    mapping = mapping.dropna(
        subset=["datetime", "instrument", "dominant_contract"]
    )
    return mapping.drop_duplicates(
        subset=["datetime", "instrument"], keep="last"
    )


def _read_contract_from_zip(
    zf: zipfile.ZipFile,
    member: str,
) -> pd.DataFrame:
    with zf.open(member) as handle:
        raw = pd.read_csv(handle)
    if raw.empty:
        return pd.DataFrame()
    rename = {}
    for col in raw.columns:
        key = str(col).strip().lower()
        if key in {"trading_date", "date", "trade_date"}:
            rename[col] = "datetime"
        elif key == "turnover":
            rename[col] = "total_turnover"
        elif key == "order_book_id":
            rename[col] = "contract"
    raw = raw.rename(columns=rename)
    if "datetime" not in raw.columns:
        return pd.DataFrame()
    raw["datetime"] = raw["datetime"].map(_parse_trade_date)
    keep = [
        c
        for c in (
            "datetime",
            "instrument",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "total_turnover",
            "settlement",
            "pre_settlement",
            "open_interest",
        )
        if c in raw.columns
    ]
    out = raw[keep].copy()
    out["source_contract"] = Path(member).stem.upper()
    return out


def load_from_daily_zips(
    daily_zip: Path,
    mapping_zip: Path,
    *,
    min_names_hint: int = 8,
) -> pd.DataFrame:
    """Join dominant-contract mapping onto per-contract daily bars."""
    mapping = _read_mapping_zip(mapping_zip)
    needed: dict[tuple[str, str, str], None] = {}
    for row in mapping.itertuples(index=False):
        needed[
            (str(row.exchange), str(row.instrument), str(row.dominant_contract))
        ] = None

    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(daily_zip) as zf:
        members = {
            name: name
            for name in zf.namelist()
            if name.lower().endswith(".csv")
        }
        for exch, product, contract in needed:
            # CFX/IF/IF1501.csv
            candidates = [
                f"{exch}/{product}/{contract}.csv",
                f"{exch}/{product}/{contract.lower()}.csv",
            ]
            member = None
            for cand in candidates:
                if cand in members:
                    member = cand
                    break
            if member is None:
                suffix = f"/{contract}.csv"
                member = next((n for n in members if n.endswith(suffix)), None)
            if member is None:
                continue
            chunk = _read_contract_from_zip(zf, member)
            if chunk.empty:
                continue
            frames.append(chunk)

    if not frames:
        raise FileNotFoundError(
            f"Daily zip {daily_zip} contained no contracts referenced by {mapping_zip}"
        )

    prices = pd.concat(frames, ignore_index=True)
    prices["join_contract"] = prices["source_contract"].astype(str).str.upper()
    mapping = mapping.copy()
    mapping["join_contract"] = (
        mapping["dominant_contract"].astype(str).str.upper()
    )
    merged = mapping.merge(
        prices,
        left_on=["datetime", "join_contract"],
        right_on=["datetime", "join_contract"],
        how="inner",
        suffixes=("", "_px"),
    )
    if merged.empty:
        raise ValueError("Mapping/price join produced an empty futures panel")
    if merged["instrument"].nunique() < min_names_hint:
        raise ValueError(
            f"Joined futures panel has only {merged['instrument'].nunique()} names"
        )
    return _finalize_panel(merged)


def resolve_panel_source(
    explicit: str | os.PathLike[str] | None = None,
) -> dict[str, Path | str]:
    """Locate the best available futures book. Does not load bars."""
    search: list[Path] = []
    if explicit:
        search.append(Path(explicit).expanduser())
    search.extend(default_data_candidates())

    for root in search:
        if not root.exists():
            continue
        cache = (
            root / "cn_futures_dominant_1d.parquet" if root.is_dir() else None
        )
        if cache is not None and cache.exists():
            return {"kind": "cache", "path": cache, "root": root}
        if root.is_file() and root.suffix.lower() in {".parquet", ".pq"}:
            return {"kind": "parquet", "path": root, "root": root.parent}
        daily = _find_daily_zip(root)
        mapping = _find_mapping_zip(root)
        if daily is not None and mapping is not None:
            return {
                "kind": "daily_zip",
                "path": daily,
                "mapping": mapping,
                "root": root,
            }
        if root.is_dir() and any(root.glob("*.parquet")):
            sample = next(root.glob("*.parquet"))
            probe = pd.read_parquet(sample, columns=None)
            if {"open", "close"}.issubset({c.lower() for c in probe.columns}):
                return {"kind": "parquet_dir", "path": root, "root": root}
    capital_d = Path.home() / "Documents" / "finance" / "data" / "samples"
    raise FileNotFoundError(
        "No usable China futures bars found. "
        f"{capital_d} has an empty futures_1m/ and stock samples only; "
        "looked for daily_*.zip+mapping.zip and dominant 1d parquets."
    )


def default_contract_dirs() -> list[Path]:
    home = Path.home()
    repo_data = Path(__file__).resolve().parents[3] / "data"
    return [
        home
        / "Documents"
        / "finance"
        / "research"
        / "llm"
        / "data"
        / "local_futures"
        / "contracts"
        / "1d",
        repo_data / "local_futures" / "contracts" / "1d",
    ]


def load_contract_panel(
    explicit: str | os.PathLike[str] | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    min_days: int = 60,
    min_median_volume: float = 5000.0,
    cache_path: str | os.PathLike[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Load individual futures contracts as instruments (no dominant splice).

    Each contract is its own tradable name, so a roll/splice gap cannot appear
    as P&L. Thin contracts are dropped.
    """
    search: list[Path] = []
    if explicit:
        search.append(Path(explicit).expanduser())
    search.extend(default_contract_dirs())
    found: Path | None = None
    for root in search:
        if root.is_dir() and any(root.glob("*.parquet")):
            found = root
            break
    if found is None:
        raise FileNotFoundError("No per-contract daily futures parquets found")

    repo_cache = Path(__file__).resolve().parents[3] / "data" / "cache"
    dest = (
        Path(cache_path).expanduser()
        if cache_path
        else repo_cache / ("cn_futures_contracts_1d.parquet")
    )
    if dest.exists():
        panel = _finalize_panel(pd.read_parquet(dest))
        meta = {"kind": "contract_cache", "path": str(dest)}
    else:
        frames: list[pd.DataFrame] = []
        for path in sorted(found.glob("*.parquet")):
            raw = pd.read_parquet(path)
            if raw.empty:
                continue
            raw = raw.copy()
            raw["instrument"] = path.stem.upper()
            if "underlying_symbol" in raw.columns:
                raw["product"] = (
                    raw["underlying_symbol"].astype(str).str.upper()
                )
            else:
                match = _CONTRACT_RE.match(path.stem.upper())
                raw["product"] = match.group(1) if match else path.stem.upper()
            raw["dominant_contract"] = raw["instrument"]
            frames.append(raw)
        if not frames:
            raise FileNotFoundError(f"No contract frames under {found}")
        panel = _finalize_panel(pd.concat(frames, ignore_index=True))
        # liquidity screen on the full history, then persist
        stats = panel.groupby("instrument").agg(
            n=("datetime", "size"), vol=("volume", "median")
        )
        keep = stats[
            (stats["n"] >= min_days) & (stats["vol"] >= min_median_volume)
        ].index
        panel = panel[panel["instrument"].isin(keep)].copy()
        dest.parent.mkdir(parents=True, exist_ok=True)
        panel.to_parquet(dest, index=False)
        meta = {
            "kind": "contract_dir",
            "path": str(found),
            "cached_as": str(dest),
        }

    if start_date:
        panel = panel[panel["datetime"] >= pd.Timestamp(start_date)]
    if end_date:
        panel = panel[panel["datetime"] <= pd.Timestamp(end_date)]
    if panel.empty:
        raise ValueError("Contract panel is empty after filters")
    meta.update(
        {
            "n_rows": str(len(panel)),
            "n_instruments": str(panel["instrument"].nunique()),
            "start": str(panel["datetime"].min().date()),
            "end": str(panel["datetime"].max().date()),
            "universe": "contracts",
        }
    )
    return panel.reset_index(drop=True), meta


def load_all_zip_contracts_panel(
    daily_zip: Path | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    min_days: int = 60,
    min_median_volume: float = 5000.0,
    cache_path: str | os.PathLike[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Every CSV in the daily zip is one tradable contract (no dominant splice)."""
    if daily_zip is None:
        daily_zip = (
            Path.home()
            / "Documents"
            / "finance"
            / "data"
            / "raw"
            / "daily_20000101_20260331.zip"
        )
    daily_zip = Path(daily_zip).expanduser()
    if not daily_zip.exists():
        raise FileNotFoundError(daily_zip)

    repo_cache = Path(__file__).resolve().parents[3] / "data" / "cache"
    dest = (
        Path(cache_path).expanduser()
        if cache_path
        else repo_cache / ("cn_futures_all_contracts_1d.parquet")
    )
    if dest.exists():
        panel = _finalize_panel(pd.read_parquet(dest))
        meta = {"kind": "all_contract_cache", "path": str(dest)}
    else:
        frames: list[pd.DataFrame] = []
        with zipfile.ZipFile(daily_zip) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".csv"):
                    continue
                chunk = _read_contract_from_zip(zf, name)
                if chunk.empty:
                    continue
                contract = Path(name).stem.upper()
                chunk["instrument"] = contract
                match = _CONTRACT_RE.match(contract)
                chunk["product"] = match.group(1) if match else contract
                chunk["dominant_contract"] = contract
                frames.append(chunk)
        if not frames:
            raise ValueError(f"No contracts in {daily_zip}")
        panel = _finalize_panel(pd.concat(frames, ignore_index=True))
        stats = panel.groupby("instrument").agg(
            n=("datetime", "size"), vol=("volume", "median")
        )
        keep = stats[
            (stats["n"] >= min_days) & (stats["vol"] >= min_median_volume)
        ].index
        panel = panel[panel["instrument"].isin(keep)].copy()
        dest.parent.mkdir(parents=True, exist_ok=True)
        panel.to_parquet(dest, index=False)
        meta = {
            "kind": "all_contract_zip",
            "path": str(daily_zip),
            "cached_as": str(dest),
        }

    if start_date:
        panel = panel[panel["datetime"] >= pd.Timestamp(start_date)]
    if end_date:
        panel = panel[panel["datetime"] <= pd.Timestamp(end_date)]
    if panel.empty:
        raise ValueError("All-contract panel empty after filters")
    meta.update(
        {
            "n_rows": str(len(panel)),
            "n_instruments": str(panel["instrument"].nunique()),
            "start": str(panel["datetime"].min().date()),
            "end": str(panel["datetime"].max().date()),
            "universe": "all_contracts",
        }
    )
    return panel.reset_index(drop=True), meta


def load_futures_panel(
    explicit: str | os.PathLike[str] | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    cache_path: str | os.PathLike[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Load a dominant-contract futures panel and optional on-disk cache."""
    source = resolve_panel_source(explicit)
    kind = str(source["kind"])
    meta = {
        "kind": kind,
        "path": str(source["path"]),
        "root": str(source.get("root", source["path"])),
    }
    if kind == "daily_zip":
        meta["mapping"] = str(source["mapping"])

    repo_cache = Path(__file__).resolve().parents[3] / "data" / "cache"
    dest = (
        Path(cache_path).expanduser()
        if cache_path
        else repo_cache / ("cn_futures_dominant_1d.parquet")
    )

    if kind == "cache":
        panel = _finalize_panel(pd.read_parquet(source["path"]))
    elif kind == "parquet":
        panel = load_dominant_parquets(source["path"])
    elif kind == "parquet_dir":
        panel = load_dominant_parquets(source["path"])
    else:
        if dest.exists():
            panel = _finalize_panel(pd.read_parquet(dest))
            meta["kind"] = "cache"
            meta["path"] = str(dest)
        else:
            panel = load_from_daily_zips(source["path"], source["mapping"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            panel.to_parquet(dest, index=False)
            meta["cached_as"] = str(dest)

    if start_date:
        panel = panel[panel["datetime"] >= pd.Timestamp(start_date)]
    if end_date:
        panel = panel[panel["datetime"] <= pd.Timestamp(end_date)]
    if panel.empty:
        raise ValueError("Futures panel is empty after date filtering")
    meta["n_rows"] = str(len(panel))
    meta["n_instruments"] = str(panel["instrument"].nunique())
    meta["start"] = str(panel["datetime"].min().date())
    meta["end"] = str(panel["datetime"].max().date())
    return panel.reset_index(drop=True), meta


def panel_to_wide(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Unstack long panel fields to date × instrument frames."""
    indexed = panel.set_index(["datetime", "instrument"]).sort_index()
    fields = {}
    for col in (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "total_turnover",
        "dominant_contract",
        "is_roll",
        "session_close",
        "has_night_session",
    ):
        if col in indexed.columns:
            fields[col] = indexed[col].unstack("instrument")
    return fields


def default_intraday_dirs() -> list[Path]:
    home = Path.home()
    repo_data = Path(__file__).resolve().parents[3] / "data"
    return [
        home
        / "Documents"
        / "finance"
        / "research"
        / "llm"
        / "data"
        / "local_futures"
        / "dominant"
        / "1m",
        repo_data / "local_futures" / "dominant" / "1m",
        home / "Documents" / "finance" / "data" / "samples" / "futures_1m",
    ]


def resample_ohlcv(panel: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample a 1m (or finer) dominant panel to a coarser bar."""
    if panel.empty:
        return panel
    frames: list[pd.DataFrame] = []
    for inst, grp in panel.groupby("instrument", sort=False):
        g = grp.sort_values("datetime").set_index("datetime")
        agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "total_turnover": "sum",
            "dominant_contract": "last",
        }
        use = {k: v for k, v in agg.items() if k in g.columns}
        out = (
            g.resample(rule, label="right", closed="right")
            .agg(use)
            .dropna(subset=["open", "close"])
        )
        out["instrument"] = inst
        frames.append(out.reset_index())
    if not frames:
        return panel.iloc[0:0].copy()
    return _finalize_panel(pd.concat(frames, ignore_index=True))


def load_intraday_panel(
    explicit: str | os.PathLike[str] | None = None,
    *,
    rule: str = "5min",
    start_date: str | None = None,
    end_date: str | None = None,
    cache_path: str | os.PathLike[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Load 1-minute dominant bars and resample to ``rule``."""
    search: list[Path] = []
    if explicit:
        search.append(Path(explicit).expanduser())
    search.extend(default_intraday_dirs())
    found: Path | None = None
    for root in search:
        if root.is_dir() and any(root.glob("*.parquet")):
            found = root
            break
        if root.is_file() and root.suffix.lower() in {".parquet", ".pq"}:
            found = root
            break
    if found is None:
        raise FileNotFoundError(
            "No 1-minute futures bars found under "
            + ", ".join(str(p) for p in search)
        )

    repo_cache = Path(__file__).resolve().parents[3] / "data" / "cache"
    dest = (
        Path(cache_path).expanduser()
        if cache_path
        else repo_cache / (f"cn_futures_dominant_{rule}.parquet")
    )
    if dest.exists():
        panel = _finalize_panel(pd.read_parquet(dest))
        meta = {"kind": "intraday_cache", "path": str(dest), "rule": rule}
    else:
        raw = load_dominant_parquets(found)
        panel = resample_ohlcv(raw, rule)
        dest.parent.mkdir(parents=True, exist_ok=True)
        panel.to_parquet(dest, index=False)
        meta = {
            "kind": "intraday_resample",
            "path": str(found),
            "rule": rule,
            "cached_as": str(dest),
        }

    if start_date:
        panel = panel[panel["datetime"] >= pd.Timestamp(start_date)]
    if end_date:
        # keep the full last day
        panel = panel[
            panel["datetime"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1)
        ]
    if panel.empty:
        raise ValueError("Intraday futures panel is empty after date filtering")
    meta["n_rows"] = str(len(panel))
    meta["n_instruments"] = str(panel["instrument"].nunique())
    meta["start"] = str(pd.Timestamp(panel["datetime"].min()).date())
    meta["end"] = str(pd.Timestamp(panel["datetime"].max()).date())
    return panel.reset_index(drop=True), meta

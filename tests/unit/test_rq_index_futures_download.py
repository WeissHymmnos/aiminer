import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("rqdatac", reason="RiceQuant downloader imports the optional rqdatac client")

from core.local_data import load_local_ohlcv
from scripts import download_rq_index_futures as downloader


pytestmark = pytest.mark.external


class FakeRQ:
    def __init__(self):
        self.calls = []

    def all_instruments(self, type=None, market=None):
        return pd.DataFrame(
            [
                {
                    "order_book_id": "IF2406",
                    "underlying_symbol": "IF",
                    "exchange": "CFFEX",
                    "listed_date": "2024-01-01",
                    "de_listed_date": "2024-06-21",
                },
                {
                    "order_book_id": "IH2406",
                    "underlying_symbol": "IH",
                    "exchange": "CFFEX",
                    "listed_date": "2024-01-01",
                    "de_listed_date": "2024-06-21",
                },
                {
                    "order_book_id": "CU2406",
                    "underlying_symbol": "CU",
                    "exchange": "SHFE",
                    "listed_date": "2024-01-01",
                    "de_listed_date": "2024-06-21",
                },
            ]
        )

    def get_price(self, order_book_ids, start_date=None, end_date=None, frequency="1d", fields=None, market=None, expect_df=True):
        self.calls.append(
            {
                "order_book_ids": order_book_ids,
                "start_date": pd.Timestamp(start_date),
                "end_date": pd.Timestamp(end_date),
                "frequency": frequency,
            }
        )
        start = pd.Timestamp(start_date)
        if start >= pd.Timestamp("2024-01-03"):
            dates = pd.to_datetime(["2024-01-03"])
            values = [102.0]
        else:
            dates = pd.to_datetime(["2024-01-01", "2024-01-02"])
            values = [100.0, 101.0]
        return pd.DataFrame(
            {
                "open": values,
                "high": [v + 1 for v in values],
                "low": [v - 1 for v in values],
                "close": values,
                "volume": [10 * (i + 1) for i in range(len(values))],
                "total_turnover": [1000 * (i + 1) for i in range(len(values))],
                "open_interest": [100 + i for i in range(len(values))],
            },
            index=dates,
        )

    def get_dominant_future(self, underlying_symbol, start_date=None, end_date=None, rule=0, rank=1, market="cn"):
        return pd.Series(
            ["IF2406", "IF2407"],
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
            name=underlying_symbol,
        )


class TestRQIndexFuturesDownload(unittest.TestCase):
    def test_discover_contracts_filters_requested_underlyings(self):
        fake = FakeRQ()
        with patch.object(downloader, "rq", fake):
            contracts = downloader.discover_contracts(
                underlyings=["IF", "IH"],
                start="2024-01-01",
                end="2024-12-31",
            )
        self.assertEqual([item.order_book_id for item in contracts], ["IF2406", "IH2406"])

    def test_download_contract_data_supports_incremental_append(self):
        fake = FakeRQ()
        meta = downloader.ContractMeta(
            order_book_id="IF2406",
            underlying_symbol="IF",
            exchange="CFFEX",
            listed_date=pd.Timestamp("2024-01-01"),
            de_listed_date=pd.Timestamp("2024-06-21"),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with patch.object(downloader, "rq", fake):
                first = downloader.download_contract_data(
                    meta,
                    output_root=root,
                    frequency="1d",
                    start="2024-01-01",
                    end="2024-01-03",
                )
                second = downloader.download_contract_data(
                    meta,
                    output_root=root,
                    frequency="1d",
                    start="2024-01-01",
                    end="2024-01-03",
                )

            self.assertEqual(first["status"], "written")
            self.assertEqual(second["status"], "written")
            self.assertEqual(fake.calls[1]["start_date"], pd.Timestamp("2024-01-03"))
            path = downloader.contract_file_path(root, "1d", "IF2406")
            df = pd.read_parquet(path)
            self.assertEqual(df["datetime"].nunique(), 3)

    def test_build_dominant_data_and_local_loader_compatibility(self):
        fake = FakeRQ()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            contract_dir = root / "contracts" / "1d"
            contract_dir.mkdir(parents=True, exist_ok=True)

            pd.DataFrame(
                {
                    "datetime": pd.to_datetime(["2024-01-01"]),
                    "instrument": ["IF2406"],
                    "open": [100.0],
                    "high": [101.0],
                    "low": [99.0],
                    "close": [100.5],
                    "volume": [1000],
                    "total_turnover": [100000.0],
                    "open_interest": [5000],
                    "market": ["futures"],
                    "asset_class": ["futures"],
                    "underlying_symbol": ["IF"],
                    "exchange": ["CFFEX"],
                }
            ).to_parquet(contract_dir / "IF2406.parquet", index=False)
            pd.DataFrame(
                {
                    "datetime": pd.to_datetime(["2024-01-02"]),
                    "instrument": ["IF2407"],
                    "open": [110.0],
                    "high": [111.0],
                    "low": [109.0],
                    "close": [110.5],
                    "volume": [1200],
                    "total_turnover": [120000.0],
                    "open_interest": [5200],
                    "market": ["futures"],
                    "asset_class": ["futures"],
                    "underlying_symbol": ["IF"],
                    "exchange": ["CFFEX"],
                }
            ).to_parquet(contract_dir / "IF2407.parquet", index=False)

            with patch.object(downloader, "rq", fake):
                result = downloader.build_dominant_data(
                    output_root=root,
                    underlying="IF",
                    frequency="1d",
                    start="2024-01-01",
                    end="2024-01-02",
                    rule=0,
                    rank=1,
                )

            self.assertEqual(result["status"], "written")
            dominant_path = downloader.dominant_file_path(root, "1d", "IF")
            dominant = pd.read_parquet(dominant_path)
            self.assertEqual(dominant["dominant_contract"].tolist(), ["IF2406", "IF2407"])
            self.assertEqual(dominant["instrument"].unique().tolist(), ["IF"])

            local_df = load_local_ohlcv(contract_dir / "IF2406.parquet", market_profile="futures")
            self.assertEqual(local_df.index.names, ["datetime", "instrument"])
            self.assertIn("total_turnover", local_df.columns)


if __name__ == "__main__":
    unittest.main()

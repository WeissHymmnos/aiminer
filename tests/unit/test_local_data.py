import tempfile
import unittest
from pathlib import Path

import pandas as pd
import pytest

from core.local_data import load_local_ohlcv


class TestLocalDataLoader(unittest.TestCase):
    def test_load_panel_csv_with_vwap_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "panel.csv"
            pd.DataFrame(
                {
                    "datetime": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"],
                    "instrument": ["A", "B", "A", "B"],
                    "open": [1, 2, 1.1, 2.1],
                    "high": [1.2, 2.2, 1.3, 2.3],
                    "low": [0.9, 1.9, 1.0, 2.0],
                    "close": [1.1, 2.1, 1.2, 2.2],
                    "volume": [100, 200, 110, 210],
                }
            ).to_csv(path, index=False)
            df = load_local_ohlcv(path, market_profile="cn_stock")
            self.assertIn("vwap", df.columns)
            self.assertIn("total_turnover", df.columns)
            self.assertEqual(df.index.names, ["datetime", "instrument"])

    def test_load_instrument_files_parquet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for instrument in ("A", "B"):
                pd.DataFrame(
                    {
                        "date": ["2024-01-01", "2024-01-02"],
                        "open": [1, 1.1],
                        "high": [1.2, 1.3],
                        "low": [0.9, 1.0],
                        "close": [1.1, 1.2],
                        "volume": [100, 110],
                    }
                ).to_parquet(root / f"{instrument}.parquet", index=False)
            df = load_local_ohlcv(root, market_profile="us_stock", layout="instrument_files")
            instruments = sorted(df.index.get_level_values("instrument").unique().tolist())
            self.assertEqual(instruments, ["A", "B"])

    def test_panel_directory_concatenates_all_panel_shards(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for shard, instrument in (("part1", "A"), ("part2", "B")):
                pd.DataFrame(
                    {
                        "datetime": ["2024-01-01"],
                        "instrument": [instrument],
                        "open": [1.0],
                        "high": [1.1],
                        "low": [0.9],
                        "close": [1.0],
                        "volume": [100],
                    }
                ).to_csv(root / f"{shard}.csv", index=False)

            df = load_local_ohlcv(root, market_profile="cn_stock", layout="panel")
            instruments = sorted(df.index.get_level_values("instrument").unique().tolist())

            self.assertEqual(instruments, ["A", "B"])

    def test_auto_detects_multi_file_panel_when_files_have_instruments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for shard, instrument in (("jan", "A"), ("feb", "A")):
                pd.DataFrame(
                    {
                        "date": [f"2024-0{1 if shard == 'jan' else 2}-01"],
                        "symbol": [instrument],
                        "open": [1.0],
                        "high": [1.1],
                        "low": [0.9],
                        "close": [1.0],
                        "volume": [100],
                    }
                ).to_csv(root / f"{shard}.csv", index=False)

            df = load_local_ohlcv(root, market_profile="cn_stock")

            self.assertEqual(len(df), 2)
            self.assertEqual(
                sorted(df.index.get_level_values("instrument").unique().tolist()),
                ["A"],
            )

    def test_rejects_non_positive_ohlc_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad_panel.csv"
            pd.DataFrame(
                {
                    "datetime": ["2024-01-01"],
                    "instrument": ["A"],
                    "open": [1.0],
                    "high": [1.1],
                    "low": [0.9],
                    "close": [0.0],
                    "volume": [100],
                }
            ).to_csv(path, index=False)

            with pytest.raises(ValueError, match="non_positive_ohlc=1"):
                load_local_ohlcv(path, market_profile="futures")

    def test_rejects_inconsistent_high_low_bounds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad_bounds.csv"
            pd.DataFrame(
                {
                    "datetime": ["2024-01-01"],
                    "instrument": ["A"],
                    "open": [1.0],
                    "high": [0.95],
                    "low": [0.9],
                    "close": [1.05],
                    "volume": [100],
                }
            ).to_csv(path, index=False)

            with pytest.raises(ValueError, match="bad_high_low=1"):
                load_local_ohlcv(path, market_profile="futures")

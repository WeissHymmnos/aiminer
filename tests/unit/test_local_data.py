import tempfile
import unittest
from pathlib import Path

import pandas as pd

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

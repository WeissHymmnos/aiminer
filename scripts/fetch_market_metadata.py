import akshare as ak
import os
from datetime import datetime


def generate_market_metadata():
    output_dir = "data/rag_docs/market_meta"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "current_market_metadata.md")

    print("Fetching market data via AKShare to generate metadata...")

    try:
        # Get A-share stock info
        stock_info = ak.stock_info_a_code_name()
        total_stocks = len(stock_info)
        sample_stocks = stock_info.head(5).to_dict("records")

        # Get a sample daily data for a stock (e.g. Ping An Bank 000001)
        sample_hist = ak.stock_zh_a_hist(
            symbol="000001",
            period="daily",
            start_date="20230101",
            end_date="20230110",
            adjust="qfq",
        )
        columns = sample_hist.columns.tolist()

        # Get Futures info
        futures_info = ak.futures_symbol_mark()
        total_futures = len(futures_info)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Market Data Metadata\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Overview\n")
            f.write(
                "This document provides metadata about the financial market data available for factor mining.\n"
            )
            f.write(f"- **Total A-Share Equities:** {total_stocks}\n")
            f.write(f"- **Total Futures Contracts (Active):** {total_futures}\n\n")

            f.write("## A-Share Daily Bar Data Structure\n")
            f.write(
                "The standard daily history data for A-shares (forward adjusted `qfq`) contains the following columns:\n"
            )
            for col in columns:
                f.write(f"- `{col}`\n")

            f.write("\n### Sample Stock Tickers\n")
            for stock in sample_stocks:
                f.write(f"- {stock['code']}: {stock['name']}\n")

            f.write("\n## How to align with Qlib Format\n")
            f.write(
                "When writing Qlib factor code, map these AKShare/standard columns as follows:\n"
            )
            f.write("- `开盘` -> `$open`\n")
            f.write("- `收盘` -> `$close`\n")
            f.write("- `最高` -> `$high`\n")
            f.write("- `最低` -> `$low`\n")
            f.write("- `成交量` -> `$volume`\n")
            f.write("- `成交额` / `成交量` -> `$vwap` (approximate)\n\n")

            f.write("## Notes on Strategy Design\n")
            f.write(
                "- All factor values must handle `NaN` gracefully (e.g., using Qlib's robust operations).\n"
            )
            f.write("- Prices are adjusted for splits and dividends.\n")
            f.write(
                "- Futures data usually includes Open Interest (`持仓量`) which can be used as a strong predictor.\n"
            )

        print(f"Market metadata successfully written to {file_path}")

    except Exception as e:
        print(f"Failed to generate market metadata: {e}")


if __name__ == "__main__":
    generate_market_metadata()

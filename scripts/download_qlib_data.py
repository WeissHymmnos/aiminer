import os
import sys
import subprocess


def download_qlib_data(region="cn"):
    """Download Qlib data using wget and the official data source."""
    target_dir = os.path.expanduser(
        "~/.qlib/qlib_data/cn_data" if region == "cn" else "~/.qlib/qlib_data/us_data"
    )

    print(f"Downloading {region.upper()} market data to {target_dir}...")

    os.makedirs(target_dir, exist_ok=True)

    # Use the correct download URL for Qlib data
    if region == "cn":
        data_url = "https://github.com/chenditc/investment_data/releases/download/2024-07-31/qlib_bin.tar.gz"
    else:
        data_url = "https://github.com/chenditc/investment_data/releases/download/2024-07-31/qlib_us_bin.tar.gz"

    tar_file = os.path.join(target_dir, "qlib_bin.tar.gz")

    try:
        print(f"Downloading from {data_url}...")
        subprocess.run(["wget", "-O", tar_file, data_url], check=True)

        print(f"Extracting to {target_dir}...")
        subprocess.run(
            ["tar", "-xzf", tar_file, "-C", target_dir, "--strip-components=1"],
            check=True,
        )

        os.remove(tar_file)
        print(f"Successfully downloaded {region.upper()} data to {target_dir}")

    except subprocess.CalledProcessError as e:
        print(f"Error downloading data: {e}")
        print("\nManual download instructions:")
        print(f"1. Download: {data_url}")
        print(f"2. Extract to: {target_dir}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    region = sys.argv[1] if len(sys.argv) > 1 else "cn"
    download_qlib_data(region)

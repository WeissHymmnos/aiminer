import os
import sys

def download_qlib_data(region='cn'):
    """Download Qlib data using the scripts.get_data module."""
    target_dir = os.path.expanduser("~/.qlib/qlib_data/cn_data" if region == 'cn' else "~/.qlib/qlib_data/us_data")
    
    print(f"Downloading {region.upper()} market data to {target_dir}...")
    
    try:
        from qlib.contrib.data.handler import GetData
        
        GetData().qlib_data(
            target_dir=target_dir,
            region=region,
            interval="1d",
            delete_old=False
        )
        
        print(f"Successfully downloaded {region.upper()} data to {target_dir}")
        
    except ImportError:
        print("Error: qlib.contrib.data.handler.GetData not available")
        print("\nTry downloading data manually:")
        print(f"1. Visit: https://github.com/microsoft/qlib/tree/main/scripts")
        print(f"2. Download get_data.py")
        print(f"3. Run: python get_data.py qlib_data --target_dir {target_dir} --region {region}")
    except Exception as e:
        print(f"Error downloading data: {e}")
        print("\nAlternative: Download pre-built data from:")
        print(f"https://github.com/microsoft/qlib/releases")

if __name__ == "__main__":
    region = sys.argv[1] if len(sys.argv) > 1 else 'cn'
    download_qlib_data(region)

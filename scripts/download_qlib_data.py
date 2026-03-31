import qlib
import os

def download_qlib_data(region='cn'):
    """Download Qlib data for the specified region."""
    provider_uri = "~/.qlib/qlib_data/cn_data" if region == 'cn' else "~/.qlib/qlib_data/us_data"
    provider_uri = os.path.expanduser(provider_uri)
    
    print(f"Downloading {region.upper()} market data to {provider_uri}...")
    
    try:
        from qlib.data.data import BaseProvider
        qlib.init(provider_uri=provider_uri, region=region)
        print(f"Successfully initialized Qlib with {region.upper()} data")
    except Exception as e:
        print(f"Error: {e}")
        print("\nTo download Qlib data manually, run:")
        print(f"python -m qlib.run.get_data qlib_data --target_dir {provider_uri} --region {region}")

if __name__ == "__main__":
    import sys
    region = sys.argv[1] if len(sys.argv) > 1 else 'cn'
    download_qlib_data(region)

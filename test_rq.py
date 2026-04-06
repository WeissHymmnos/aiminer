import os
import rqdatac as rq
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    token = os.getenv("RQ_TOKEN")
    user = os.getenv("RQ_USER")
    password = os.getenv("RQ_PASS")

    print("\n=== RiceQuant Connection Test ===")
    
    if token:
        print(f"Detected RQ_TOKEN (Length: {len(token)})")
        print(f"Token starts with: {token[:10]}...")
        try:
            # 官方推荐的最稳健初始化方式
            rq.init(token=token.strip())
            print("SUCCESS: Connected via Token!")
            print(f"User Info: {rq.user_info()}")
            return
        except Exception as e:
            print(f"FAILED: Token Auth Error: {e}")
    
    if user and password:
        print(f"Detected RQ_USER: {user}")
        try:
            rq.init(username=user.strip(), password=password.strip())
            print("SUCCESS: Connected via Password!")
            print(f"User Info: {rq.user_info()}")
            return
        except Exception as e:
            print(f"FAILED: Password Auth Error: {e}")

    print("\nNo valid credentials worked. Please check your export commands.")

if __name__ == "__main__":
    test_connection()

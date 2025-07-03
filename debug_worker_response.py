#!/usr/bin/env python3
"""
Debug script to see actual worker API response format
"""

import os
import sys
import json

# Load encrypted environment variables FIRST
os.environ['ENV_ENCRYPTION_KEY'] = 'ProofOfLIfe123'
from env_manager import EncryptedEnvManager
env_manager = EncryptedEnvManager()
env_manager.load_encrypted_env('.env.encrypted')

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from antpool_client import AntpoolClient
from account_credentials import get_account_credentials

def debug_worker_response():
    """Debug the actual worker API response"""
    
    # Test with POWDigital3 (first account)
    account_name = "POWDigital3"
    
    try:
        api_key, api_secret, user_id = get_account_credentials(account_name)
        client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
        
        print(f"Testing worker list API for {account_name} (user_id: {user_id})")
        print("=" * 60)
        
        # Test the original get_worker_list method
        response = client.get_worker_list(user_id=user_id, coin='BTC', worker_status=0, page=1, page_size=50)
        
        print("RAW API RESPONSE:")
        print(json.dumps(response, indent=2))
        print("=" * 60)
        
        print("RESPONSE ANALYSIS:")
        print(f"Type: {type(response)}")
        print(f"Keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        
        if isinstance(response, dict):
            if 'rows' in response:
                print(f"Found 'rows' key with {len(response['rows'])} items")
            elif 'result' in response:
                print(f"Found 'result' key: {type(response['result'])}")
                if isinstance(response['result'], dict):
                    print(f"Result keys: {list(response['result'].keys())}")
                    if 'rows' in response['result']:
                        print(f"Found 'result.rows' with {len(response['result']['rows'])} items")
            else:
                print("No 'rows' or 'result' key found")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_worker_response()


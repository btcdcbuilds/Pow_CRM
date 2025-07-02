#!/usr/bin/env python3
"""
Debug script to test sub-account API calls and see actual responses
"""

import os
import sys
sys.path.append('/home/ubuntu/Pow_CRM')

from antpool_auth import AntpoolAuth
from antpool_client import AntpoolClient
import json

# Test accounts
TEST_ACCOUNTS = ['POWDigital3', 'PNGMiningEth', 'PedroEth']

def main():
    print("=== Sub-Account API Debug Test ===")
    
    # Initialize client
    client = AntpoolClient(
        api_key=os.getenv('ANTPOOL_ACCESS_KEY'),
        api_secret=os.getenv('ANTPOOL_SECRET_KEY'),
        user_id=os.getenv('ANTPOOL_USER_ID')
    )
    
    for account in TEST_ACCOUNTS:
        print(f"\n--- Testing Account: {account} ---")
        
        try:
            # Test account balance
            print(f"Calling get_account_balance(user_id='{account}')")
            balance_data = client.get_account_balance(user_id=account, coin='BTC')
            print(f"Balance Response: {json.dumps(balance_data, indent=2)}")
            
            # Test hashrate
            print(f"Calling get_hashrate(user_id='{account}')")
            hashrate_data = client.get_hashrate(user_id=account, coin='BTC')
            print(f"Hashrate Response: {json.dumps(hashrate_data, indent=2)}")
            
        except Exception as e:
            print(f"ERROR for {account}: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    main()


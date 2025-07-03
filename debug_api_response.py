#!/usr/bin/env python3
"""
Debug script to see the actual API response from accountOverview endpoint
"""

import os
import sys
import logging
import json

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load encrypted environment variables FIRST
os.environ['ENV_ENCRYPTION_KEY'] = 'ProofOfLIfe123'

from env_manager import EncryptedEnvManager
env_manager = EncryptedEnvManager()
env_manager.load_encrypted_env('.env.encrypted')

from antpool_client import AntpoolClient
from account_credentials import get_account_credentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Check the actual API response"""
    try:
        # Test with first account
        account_name = "POWDigital3"
        api_key, api_secret, user_id = get_account_credentials(account_name)
        
        logger.info(f"Testing API response with account: {account_name}")
        
        # Create client
        client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
        
        # Test the _make_request method directly to see raw response
        logger.info("=== TESTING ACCOUNT OVERVIEW RAW RESPONSE ===")
        
        # Get auth params
        params = client.auth.get_auth_params(user_id=user_id, coin='BTC')
        
        # Make raw request
        try:
            response = client._make_request('account_overview', params)
            logger.info(f"Raw response type: {type(response)}")
            logger.info(f"Raw response: {response}")
            
            if isinstance(response, dict):
                logger.info(f"Response keys: {list(response.keys())}")
                for key, value in response.items():
                    logger.info(f"  {key}: {value} (type: {type(value)})")
            
        except Exception as e:
            logger.error(f"Exception during raw request: {e}")
            logger.error(f"Exception type: {type(e)}")
        
        # Compare with working endpoint
        logger.info("=== TESTING WORKING ENDPOINT FOR COMPARISON ===")
        
        try:
            params = client.auth.get_auth_params(user_id=user_id, coin='BTC')
            response = client._make_request('account', params)
            logger.info(f"Account response: {response}")
            
        except Exception as e:
            logger.error(f"Account endpoint exception: {e}")
        
        logger.info("=== DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"Debug script failed: {e}")

if __name__ == "__main__":
    main()


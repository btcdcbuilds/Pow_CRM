#!/usr/bin/env python3
"""
Debug script to test Antpool API endpoints and see what's actually available
"""

import os
import sys
import logging
import json

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load encrypted environment variables FIRST
import os
os.environ['ENV_ENCRYPTION_KEY'] = 'ProofOfLIfe123'  # Set the encryption key

from env_manager import EncryptedEnvManager
env_manager = EncryptedEnvManager()
env_manager.load_encrypted_env('.env.encrypted')

from antpool_client import AntpoolClient
from account_credentials import get_account_credentials

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api_endpoint(client, endpoint_name, method_name, *args, **kwargs):
    """Test a specific API endpoint and return detailed results"""
    try:
        logger.info(f"Testing {endpoint_name} endpoint...")
        method = getattr(client, method_name)
        result = method(*args, **kwargs)
        
        if result:
            logger.info(f"✅ {endpoint_name} SUCCESS")
            logger.info(f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            if isinstance(result, dict):
                logger.info(f"Code: {result.get('code', 'No code')}")
                logger.info(f"Message: {result.get('message', 'No message')}")
                if result.get('data'):
                    logger.info(f"Data keys: {list(result['data'].keys()) if isinstance(result['data'], dict) else 'Data not a dict'}")
            return True, result
        else:
            logger.error(f"❌ {endpoint_name} FAILED - No response")
            return False, None
            
    except Exception as e:
        logger.error(f"❌ {endpoint_name} FAILED - Exception: {e}")
        return False, str(e)

def main():
    """Test all API endpoints to see what's working"""
    try:
        # Test with first account
        account_name = "POWDigital3"
        api_key, api_secret, user_id = get_account_credentials(account_name)
        
        logger.info(f"Testing API endpoints with account: {account_name}")
        logger.info(f"User ID: {user_id}")
        
        # Create client
        client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
        
        # Test endpoints that work in Tier 1
        logger.info("=== TESTING WORKING ENDPOINTS ===")
        
        # Test account balance (works in Tier 1)
        success, result = test_api_endpoint(
            client, "Account Balance", "get_account_balance", 
            user_id=user_id, coin='BTC'
        )
        
        # Test hashrate (works in Tier 1)
        success, result = test_api_endpoint(
            client, "Hashrate", "get_hashrate",
            user_id=user_id, coin='BTC'
        )
        
        logger.info("=== TESTING FAILING ENDPOINTS ===")
        
        # Test account overview (fails in Tier 2)
        success, result = test_api_endpoint(
            client, "Account Overview", "get_account_overview",
            user_id=user_id, coin='BTC'
        )
        
        # Test alternative endpoints
        logger.info("=== TESTING ALTERNATIVE ENDPOINTS ===")
        
        # Test worker list
        success, result = test_api_endpoint(
            client, "Worker List", "get_worker_list",
            user_id=user_id, coin='BTC', worker_status=0, page=1, page_size=10
        )
        
        # Test workers endpoint
        success, result = test_api_endpoint(
            client, "Workers", "get_workers",
            user_id=user_id, coin='BTC'
        )
        
        logger.info("=== DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"Debug script failed: {e}")

if __name__ == "__main__":
    main()


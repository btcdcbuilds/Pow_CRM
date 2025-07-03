#!/usr/bin/env python3
"""
Debug script to see the raw HTTP response from accountOverview endpoint
"""

import os
import sys
import logging
import json
import requests

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load encrypted environment variables FIRST
os.environ['ENV_ENCRYPTION_KEY'] = 'ProofOfLIfe123'

from env_manager import EncryptedEnvManager
env_manager = EncryptedEnvManager()
env_manager.load_encrypted_env('.env.encrypted')

from antpool_auth import AntpoolAuth, AntpoolConfig
from account_credentials import get_account_credentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_raw_endpoint(auth, endpoint_name, user_id, coin='BTC'):
    """Test endpoint with raw HTTP request"""
    try:
        # Get URL and params
        url = AntpoolConfig.get_endpoint_url(endpoint_name)
        params = auth.get_auth_params(user_id=user_id, coin=coin)
        
        logger.info(f"Testing {endpoint_name} endpoint")
        logger.info(f"URL: {url}")
        logger.info(f"Params: {list(params.keys())}")
        
        # Make raw request
        response = requests.post(url, data=params, timeout=30)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Headers: {dict(response.headers)}")
        logger.info(f"Raw Response Text: {response.text}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                logger.info(f"JSON Response: {json.dumps(json_data, indent=2)}")
                return json_data
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return None
        else:
            logger.error(f"HTTP error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Exception: {e}")
        return None

def main():
    """Check the actual API response"""
    try:
        # Test with first account
        account_name = "POWDigital3"
        api_key, api_secret, user_id = get_account_credentials(account_name)
        
        logger.info(f"Testing raw API response with account: {account_name}")
        
        # Create auth
        auth = AntpoolAuth(api_key, api_secret, user_id)
        
        # Test working endpoint first
        logger.info("=== TESTING WORKING ENDPOINT (account) ===")
        working_response = test_raw_endpoint(auth, 'account', user_id, 'BTC')
        
        # Test failing endpoint
        logger.info("=== TESTING FAILING ENDPOINT (account_overview) ===")
        failing_response = test_raw_endpoint(auth, 'account_overview', user_id, 'BTC')
        
        # Test worker list (which works)
        logger.info("=== TESTING WORKER LIST ENDPOINT ===")
        worker_response = test_raw_endpoint(auth, 'worker_list', user_id, 'BTC')
        
        logger.info("=== DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"Debug script failed: {e}")

if __name__ == "__main__":
    main()


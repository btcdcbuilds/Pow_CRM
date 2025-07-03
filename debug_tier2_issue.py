#!/usr/bin/env python3
"""
Debug script to see what's happening with the worker list call in Tier 2
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

def test_worker_list_call():
    """Test the exact worker list call used in Tier 2"""
    try:
        # Test with first account
        account_name = "POWDigital3"
        api_key, api_secret, user_id = get_account_credentials(account_name)
        
        logger.info(f"Testing worker list call with account: {account_name}")
        
        # Create client
        client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
        
        # Test the exact call from Tier 2
        logger.info("=== TESTING TIER 2 WORKER LIST CALL ===")
        
        try:
            worker_data = client.get_worker_list(user_id=user_id, coin='BTC', worker_status=0, page=1, page_size=50)
            logger.info(f"Worker data type: {type(worker_data)}")
            logger.info(f"Worker data: {worker_data}")
            
            if worker_data:
                logger.info(f"Worker data keys: {list(worker_data.keys()) if isinstance(worker_data, dict) else 'Not a dict'}")
                
                if isinstance(worker_data, dict):
                    logger.info(f"Code: {worker_data.get('code', 'No code field')}")
                    logger.info(f"Message: {worker_data.get('message', 'No message field')}")
                    
                    if worker_data.get('code') == 0:
                        logger.info("✅ API call successful (code == 0)")
                        data = worker_data.get('data', {})
                        logger.info(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Data not a dict'}")
                        
                        # Test the overview data extraction
                        overview_data = {
                            'total_workers': data.get('result', {}).get('totalRecord', 0),
                            'active_workers': len([w for w in data.get('result', {}).get('rows', []) if w.get('hsLast10min', '0') != '0 TH/s']),
                            'coin_type': data.get('coinType', 'BTC'),
                            'user_id': data.get('userId', user_id),
                            'worker_summary': data.get('result', {})
                        }
                        logger.info(f"Extracted overview data: {overview_data}")
                        
                    else:
                        logger.error(f"❌ API call failed with code: {worker_data.get('code')}")
                        logger.error(f"Error message: {worker_data.get('message')}")
                        
            else:
                logger.error("❌ No worker data returned")
                
        except Exception as e:
            logger.error(f"❌ Exception during worker list call: {e}")
            logger.error(f"Exception type: {type(e)}")
        
        logger.info("=== DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"Debug script failed: {e}")

if __name__ == "__main__":
    test_worker_list_call()


#!/usr/bin/env python3
"""
Debug Data Flow - Trace where worker data is lost
"""

import os
import sys
import logging
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load encrypted environment variables FIRST
from env_manager import EncryptedEnvManager
env_manager = EncryptedEnvManager()
env_manager.load_encrypted_env('.env.encrypted')

from antpool_client import AntpoolClient
from account_credentials import get_account_credentials

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_single_account(account_name: str):
    """Debug data flow for a single account"""
    logger.info(f"=== DEBUGGING DATA FLOW FOR {account_name} ===")
    
    try:
        # Get credentials
        api_key, api_secret, user_id = get_account_credentials(account_name)
        logger.info(f"✅ Got credentials for {account_name}, user_id: {user_id}")
        
        # Initialize client
        client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
        logger.info(f"✅ Initialized client for {account_name}")
        
        # Test get_workers method directly (single page)
        logger.info("🔍 Testing get_workers (single page)...")
        single_page_result = client.get_workers(user_id=user_id, coin='BTC', page=1, page_size=50)
        logger.info(f"📊 Single page result type: {type(single_page_result)}")
        logger.info(f"📊 Single page result keys: {single_page_result.keys() if isinstance(single_page_result, dict) else 'Not a dict'}")
        
        if isinstance(single_page_result, dict):
            logger.info(f"📊 Has 'rows' key: {'rows' in single_page_result}")
            if 'rows' in single_page_result:
                rows = single_page_result['rows']
                logger.info(f"📊 Rows type: {type(rows)}")
                logger.info(f"📊 Rows length: {len(rows) if rows else 'None/Empty'}")
                if rows and len(rows) > 0:
                    logger.info(f"📊 First row type: {type(rows[0])}")
                    logger.info(f"📊 First row content: {rows[0]}")
                else:
                    logger.warning("⚠️ Rows is empty or None")
            else:
                logger.warning("⚠️ No 'rows' key in result")
        else:
            logger.error(f"❌ get_workers returned {type(single_page_result)}, not dict")
        
        # Test get_all_workers method
        logger.info("🔍 Testing get_all_workers...")
        all_workers_result = client.get_all_workers(user_id=user_id, coin='BTC')
        logger.info(f"📊 get_all_workers result type: {type(all_workers_result)}")
        logger.info(f"📊 get_all_workers result length: {len(all_workers_result) if all_workers_result else 'None/Empty'}")
        
        if all_workers_result:
            logger.info(f"📊 First worker type: {type(all_workers_result[0])}")
            logger.info(f"📊 First worker content: {all_workers_result[0]}")
            
            # Save raw data to file for inspection
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_workers_{account_name}_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(all_workers_result, f, indent=2, default=str)
            logger.info(f"💾 Saved raw worker data to {filename}")
        else:
            logger.error("❌ get_all_workers returned None or empty")
        
        # Test the data orchestrator logic
        logger.info("🔍 Testing data orchestrator logic...")
        if all_workers_result and isinstance(all_workers_result, list):
            logger.info("✅ Data orchestrator check would PASS")
            logger.info(f"✅ Would process {len(all_workers_result)} workers")
        else:
            logger.error("❌ Data orchestrator check would FAIL")
            logger.error(f"❌ Condition: all_workers_result={bool(all_workers_result)}, isinstance(list)={isinstance(all_workers_result, list)}")
        
    except Exception as e:
        logger.error(f"❌ Error debugging {account_name}: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

def main():
    """Main debug function"""
    # Test with a few accounts
    test_accounts = ['POWDigital3', 'PNGMiningEth', 'PedroEth']
    
    for account_name in test_accounts:
        debug_single_account(account_name)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()


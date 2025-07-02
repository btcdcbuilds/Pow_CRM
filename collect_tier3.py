#!/usr/bin/env python3
"""
Tier 3 Data Collection Script
Collects financial data from all sub-accounts using individual credentials
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# CRITICAL FIX: Import and load encrypted environment FIRST
from env_manager import EncryptedEnvManager

# Load encrypted environment variables
try:
    env_manager = EncryptedEnvManager()
    env_vars = env_manager.load_encrypted_env('.env.encrypted')
    logging.info(f"Successfully loaded {len(env_vars)} environment variables from encrypted file")
except Exception as e:
    logging.error(f"Failed to load encrypted environment: {e}")
    # Fallback to regular environment variables (for local development)
    logging.warning("Falling back to regular environment variables")

from data_orchestrator import DataExtractionOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main execution function"""
    try:
        logger.info("=== Antpool Tier 3 Collection Started ===")
        
        # Get Supabase credentials
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not all([supabase_url, supabase_key]):
            raise ValueError("Supabase credentials are required")
        
        # Initialize orchestrator (no API credentials needed here)
        orchestrator = DataExtractionOrchestrator(supabase_url, supabase_key)
        
        # Process coins
        coins = ['BTC']  # Add more coins as needed
        total_datasets = 0
        total_offline_devices = 0
        total_sub_accounts = 0
        total_api_calls = 0
        
        for coin in coins:
            logger.info(f"Processing Tier 3 data for {coin}...")
            
            try:
                # Note: Tier 3 method needs to be implemented
                logger.warning("Tier 3 collection not yet implemented - focusing on Tier 1 first")
                
            except Exception as e:
                logger.error(f"✗ {coin}: Unexpected error - {e}")
        
        # Summary
        logger.info("=== Tier 3 Collection Complete ===")
        logger.info(f"Coins processed: {len(coins)}")
        logger.info(f"Total datasets: {total_datasets}")
        logger.info(f"Total offline devices: {total_offline_devices}")
        logger.info(f"Total sub-accounts: {total_sub_accounts}")
        logger.info(f"Total API calls: {total_api_calls}")
        logger.info(f"Execution time: {datetime.now(timezone.utc).isoformat()}")
        
    except Exception as e:
        logger.error(f"Fatal error in Tier 3 collection: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


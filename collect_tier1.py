#!/usr/bin/env python3
"""
Antpool Tier 1 Data Collection Script - Dashboard Essentials
Runs every 10 minutes via Render.com cron job

Collects:
- Main pool info (balance, total hashrate, earnings)
- Sub-account summaries
- Offline device detection only

API Usage: ~5-8 calls per run
Schedule: */10 * * * * (every 10 minutes)
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Import our modules
from data_orchestrator import DataExtractionOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main execution function for Tier 1 collection"""
    try:
        logger.info("=== Antpool Tier 1 Collection Started ===")
        start_time = datetime.now(timezone.utc)
        
        # Initialize orchestrator
        orchestrator = DataExtractionOrchestrator(
            api_key=os.getenv('ANTPOOL_ACCESS_KEY'),
            api_secret=os.getenv('ANTPOOL_SECRET_KEY'),
            user_id=os.getenv('ANTPOOL_USER_ID'),
            email=os.getenv('ANTPOOL_EMAIL'),
            supabase_connection=os.getenv('SUPABASE_CONNECTION_STRING')
        )
        
        # Get coins to process
        coins = os.getenv('ANTPOOL_COINS', 'BTC').split(',')
        
        # Process each coin
        total_api_calls = 0
        total_datasets = 0
        total_offline_devices = 0
        total_sub_accounts = 0
        
        for coin in coins:
            coin = coin.strip()
            logger.info(f"Processing Tier 1 data for {coin}...")
            
            try:
                results = orchestrator.collect_tier1_data(coin)
                
                api_calls = results.get('api_calls_made', 0)
                datasets = len(results.get('data_collected', []))
                offline_devices = len(results.get('offline_devices', []))
                sub_accounts = results.get('sub_accounts_processed', 0)
                success = results.get('success', False)
                
                total_api_calls += api_calls
                total_datasets += datasets
                total_offline_devices += offline_devices
                total_sub_accounts += sub_accounts
                
                if success:
                    logger.info(f"✓ {coin}: {datasets} datasets, {offline_devices} offline devices, "
                               f"{sub_accounts} sub-accounts, {api_calls} API calls")
                    
                    # Log offline devices for monitoring
                    for device in results.get('offline_devices', []):
                        logger.warning(f"🚨 OFFLINE: {device['worker_name']} "
                                     f"(last share: {device.get('last_share_time', 'unknown')})")
                else:
                    logger.error(f"✗ {coin}: Collection failed - {results.get('errors', [])}")
                    
            except Exception as e:
                logger.error(f"✗ {coin}: Exception during collection - {e}")
        
        # Calculate execution time
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Final summary
        logger.info(f"=== Tier 1 Collection Complete ===")
        logger.info(f"Coins processed: {len(coins)}")
        logger.info(f"Total datasets: {total_datasets}")
        logger.info(f"Total offline devices: {total_offline_devices}")
        logger.info(f"Total sub-accounts: {total_sub_accounts}")
        logger.info(f"Total API calls: {total_api_calls}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error in Tier 1 collection: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


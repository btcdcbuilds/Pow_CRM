#!/usr/bin/env python3
"""
Antpool Tier 2 Data Collection Script - Complete Worker Data
Runs every hour via Render.com cron job

Collects:
- All workers from main account + sub-accounts (6000+ devices)
- Hourly hashrate and 24-hour hashrate for each worker
- Worker status and efficiency data
- Low hashrate detection and alerting

API Usage: ~50-100 calls per run (batched efficiently)
Schedule: 0 * * * * (every hour at :00)
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
    """Main execution function for Tier 2 collection"""
    try:
        logger.info("=== Antpool Tier 2 Collection Started ===")
        start_time = datetime.now(timezone.utc)
        
        # Initialize orchestrator
        orchestrator = DataExtractionOrchestrator(
            api_key=os.getenv('ANTPOOL_API_KEY'),
            api_secret=os.getenv('ANTPOOL_API_SECRET'),
            user_id=os.getenv('ANTPOOL_USER_ID'),
            email=os.getenv('ANTPOOL_EMAIL'),
            supabase_connection=os.getenv('SUPABASE_CONNECTION_STRING')
        )
        
        # Get coins to process
        coins = os.getenv('ANTPOOL_COINS', 'BTC').split(',')
        
        # Process each coin
        total_api_calls = 0
        total_workers = 0
        total_accounts = 0
        
        for coin in coins:
            coin = coin.strip()
            logger.info(f"Processing Tier 2 data for {coin}...")
            
            try:
                results = orchestrator.collect_tier2_data(coin)
                
                api_calls = results.get('api_calls_made', 0)
                workers = results.get('workers_processed', 0)
                accounts = results.get('accounts_processed', 0)
                success = results.get('success', False)
                
                total_api_calls += api_calls
                total_workers += workers
                total_accounts += accounts
                
                if success:
                    logger.info(f"✓ {coin}: {workers} workers across {accounts} accounts, {api_calls} API calls")
                    
                    # Log any errors for specific accounts
                    for error in results.get('errors', []):
                        logger.warning(f"⚠️ {error}")
                        
                else:
                    logger.error(f"✗ {coin}: Collection failed - {results.get('errors', [])}")
                    
            except Exception as e:
                logger.error(f"✗ {coin}: Exception during collection - {e}")
        
        # Calculate execution time
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Final summary
        logger.info(f"=== Tier 2 Collection Complete ===")
        logger.info(f"Coins processed: {len(coins)}")
        logger.info(f"Total workers processed: {total_workers}")
        logger.info(f"Total accounts processed: {total_accounts}")
        logger.info(f"Total API calls: {total_api_calls}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Average workers per account: {total_workers/total_accounts if total_accounts > 0 else 0:.0f}")
        logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        
        # Performance warning if too many API calls
        if total_api_calls > 150:
            logger.warning(f"⚠️ High API usage: {total_api_calls} calls. Consider optimizing batch sizes.")
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error in Tier 2 collection: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


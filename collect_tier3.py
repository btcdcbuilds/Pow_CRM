#!/usr/bin/env python3
"""
Antpool Tier 3 Data Collection Script - Daily Financial & Historical
Runs daily at 2 AM via Render.com cron job

Collects:
- Daily earnings per worker (when Antpool updates)
- Payment history tracking
- Daily efficiency calculations
- Worker performance summaries

API Usage: ~20-30 calls per run
Schedule: 0 2 * * * (daily at 2 AM)
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
    """Main execution function for Tier 3 collection"""
    try:
        logger.info("=== Antpool Tier 3 Collection Started ===")
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
        total_datasets = 0
        total_payments = 0
        
        for coin in coins:
            coin = coin.strip()
            logger.info(f"Processing Tier 3 data for {coin}...")
            
            try:
                results = orchestrator.collect_tier3_data(coin)
                
                api_calls = results.get('api_calls_made', 0)
                datasets = len(results.get('data_collected', []))
                payments = results.get('payments_processed', 0)
                success = results.get('success', False)
                
                total_api_calls += api_calls
                total_datasets += datasets
                total_payments += payments
                
                if success:
                    logger.info(f"✓ {coin}: {datasets} datasets, {payments} payments processed, {api_calls} API calls")
                else:
                    logger.error(f"✗ {coin}: Collection failed - {results.get('errors', [])}")
                    
            except Exception as e:
                logger.error(f"✗ {coin}: Exception during collection - {e}")
        
        # Calculate execution time
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Final summary
        logger.info(f"=== Tier 3 Collection Complete ===")
        logger.info(f"Coins processed: {len(coins)}")
        logger.info(f"Total datasets: {total_datasets}")
        logger.info(f"Total payments processed: {total_payments}")
        logger.info(f"Total API calls: {total_api_calls}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error in Tier 3 collection: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Tier 3 - Detailed Worker Data Collection
Collects detailed worker data for problematic accounts every 2 hours
API Usage: ~50-100 calls (selective based on Tier 1/2 findings)
Focus: Detailed worker analysis for accounts with issues
"""

import os
import sys
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load encrypted environment variables FIRST
from env_manager import EncryptedEnvManager
env_manager = EncryptedEnvManager()
env_manager.load_encrypted_env('.env.encrypted')

from data_orchestrator import DataExtractionOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main execution function for Tier 3 data collection"""
    try:
        logger.info("Starting Tier 3 - Detailed Worker Data Collection")
        
        # Get Supabase credentials
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Missing Supabase credentials")
        
        # Initialize orchestrator
        orchestrator = DataExtractionOrchestrator(supabase_url, supabase_key)
        
        # Collect Tier 3 data
        results = orchestrator.collect_tier3_data(coin='BTC')
        
        # Report results
        if results['success']:
            logger.info(f"✓ Tier 3 collection successful")
            logger.info(f"✓ Processed: {results['sub_accounts_processed']} accounts")
            logger.info(f"✓ Workers analyzed: {results['workers_analyzed']}")
            logger.info(f"✓ API calls made: {results['api_calls_made']}")
            logger.info(f"✓ Data collected: {len(results['data_collected'])} datasets")
            
            if results['errors']:
                logger.warning(f"⚠ Partial success with {len(results['errors'])} errors")
                for error in results['errors'][:5]:  # Show first 5 errors
                    logger.warning(f"  - {error}")
        else:
            logger.error(f"✗ Tier 3 collection failed")
            logger.error(f"✗ Errors: {results['errors']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"✗ Tier 3 collection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


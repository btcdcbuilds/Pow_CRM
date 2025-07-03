#!/usr/bin/env python3
"""
Tier 2 - Account Overview Data Collection (OPTIMIZED)
Collects complete worker data for all 33 pools every 30 minutes
- Optimized for performance (5-10 minutes instead of 30)
- Clean summary output per pool
- Batch database operations
- Reduced logging noise
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

# Import optimized components
from data_orchestrator import DataExtractionOrchestrator

# Configure logging for clean output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce noise from HTTP and Supabase clients
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('supabase').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def main():
    """Main execution function for optimized Tier 2 data collection"""
    try:
        logger.info("Starting Tier 2 - Account Overview Data Collection (OPTIMIZED)")
        
        # Get Supabase credentials
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Missing Supabase credentials")
        
        # Initialize optimized orchestrator
        orchestrator = DataExtractionOrchestrator(supabase_url, supabase_key)
        
        # Collect Tier 2 data with optimizations
        results = orchestrator.collect_tier2_data(coin='BTC')
        
        # Report clean summary results
        if results['success']:
            logger.info("🎉 TIER 2 COLLECTION SUCCESSFUL!")
            logger.info(f"📊 SUMMARY:")
            logger.info(f"   • Accounts processed: {results['sub_accounts_processed']}")
            logger.info(f"   • Total workers found: {results['total_workers_found']}")
            logger.info(f"   • Workers stored: {results['workers_stored']}")
            logger.info(f"   • API calls made: {results['api_calls_made']}")
            logger.info(f"   • Data collected: {len(results['data_collected'])} datasets")
            
            if results['errors']:
                logger.warning(f"⚠️  PARTIAL SUCCESS: {len(results['errors'])} accounts had errors")
                logger.warning("First few errors:")
                for error in results['errors'][:3]:  # Show first 3 errors only
                    logger.warning(f"   • {error}")
            else:
                logger.info("✅ All accounts processed successfully!")
                
        else:
            logger.error("❌ TIER 2 COLLECTION FAILED")
            logger.error("Errors encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                logger.error(f"   • {error}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Tier 2 collection failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


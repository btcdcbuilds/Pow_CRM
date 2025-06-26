#!/usr/bin/env python3
"""
Antpool Tier 4 Data Cleanup Script - Storage Management
Runs daily at 3 AM via Render.com cron job

Performs:
- Delete 10-minute data older than 3 days
- Delete hourly worker data older than 7 days
- Keep daily summaries forever
- Aggregate efficiency reports
- Database maintenance and optimization

Schedule: 0 3 * * * (daily at 3 AM)
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
    """Main execution function for Tier 4 cleanup"""
    try:
        logger.info("=== Antpool Tier 4 Cleanup Started ===")
        start_time = datetime.now(timezone.utc)
        
        # Initialize orchestrator
        orchestrator = DataExtractionOrchestrator(
            api_key=os.getenv('ANTPOOL_API_KEY'),
            api_secret=os.getenv('ANTPOOL_API_SECRET'),
            user_id=os.getenv('ANTPOOL_USER_ID'),
            email=os.getenv('ANTPOOL_EMAIL'),
            supabase_connection=os.getenv('SUPABASE_CONNECTION_STRING')
        )
        
        # Perform cleanup operations
        try:
            results = orchestrator.collect_tier4_cleanup()
            
            records_deleted = results.get('records_deleted', 0)
            cleanup_operations = len(results.get('data_cleaned', []))
            success = results.get('success', False)
            
            if success:
                logger.info(f"✓ Cleanup completed: {records_deleted} records deleted, {cleanup_operations} operations")
                
                # Log detailed cleanup results
                for operation in results.get('data_cleaned', []):
                    logger.info(f"  - {operation}")
                    
            else:
                logger.error(f"✗ Cleanup failed - {results.get('errors', [])}")
                
        except Exception as e:
            logger.error(f"✗ Exception during cleanup - {e}")
        
        # Calculate execution time
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Final summary
        logger.info(f"=== Tier 4 Cleanup Complete ===")
        logger.info(f"Total records deleted: {results.get('records_deleted', 0)}")
        logger.info(f"Cleanup operations: {len(results.get('data_cleaned', []))}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        
        # Storage optimization message
        logger.info("💾 Storage optimized - old data cleaned up to maintain 3-day retention for frequent data")
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error in Tier 4 cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


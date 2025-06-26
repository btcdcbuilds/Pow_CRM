#!/usr/bin/env python3
"""
Pow_CRM Health Check Script
Validates all system connections and configurations before data collection

This script runs on Render.com startup to ensure everything is properly configured.
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment_variables():
    """Check that all required environment variables are set"""
    logger.info("🔍 Checking environment variables...")
    
    required_vars = [
        'ANTPOOL_API_KEY',
        'ANTPOOL_API_SECRET', 
        'ANTPOOL_USER_ID',
        'SUPABASE_CONNECTION_STRING'
    ]
    
    optional_vars = [
        'ANTPOOL_EMAIL',
        'ANTPOOL_COINS'
    ]
    
    missing_vars = []
    
    # Check required variables
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            logger.info(f"✅ {var} is set")
    
    # Check optional variables
    for var in optional_vars:
        if os.getenv(var):
            logger.info(f"✅ {var} is set (optional)")
        else:
            logger.info(f"ℹ️  {var} not set (optional)")
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def test_antpool_connection():
    """Test connection to Antpool API"""
    logger.info("🔍 Testing Antpool API connection...")
    
    try:
        from antpool_client import AntpoolClient
        
        client = AntpoolClient(
            api_key=os.getenv('ANTPOOL_API_KEY'),
            api_secret=os.getenv('ANTPOOL_API_SECRET'),
            user_id=os.getenv('ANTPOOL_USER_ID')
        )
        
        # Test API connection with rate limit check
        rate_status = client.get_rate_limit_status()
        
        if rate_status and 'requests_remaining' in rate_status:
            remaining = rate_status['requests_remaining']
            logger.info(f"✅ Antpool API connection successful")
            logger.info(f"📊 API requests remaining: {remaining}")
            return True
        else:
            logger.error("❌ Antpool API connection failed - invalid response")
            return False
            
    except Exception as e:
        logger.error(f"❌ Antpool API connection failed: {e}")
        return False

def test_supabase_connection():
    """Test connection to Supabase database"""
    logger.info("🔍 Testing Supabase database connection...")
    
    try:
        from supabase_manager import SupabaseManager
        
        db = SupabaseManager(os.getenv('SUPABASE_CONNECTION_STRING'))
        
        # Test basic query
        result = db.execute_query("SELECT 1 as test")
        
        if result and len(result) > 0 and result[0].get('test') == 1:
            logger.info("✅ Supabase database connection successful")
            
            # Check if tables exist
            tables_result = db.execute_query("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('accounts', 'workers', 'account_balances')
            """)
            
            if tables_result and len(tables_result) >= 3:
                logger.info("✅ Database schema appears to be properly set up")
                return True
            else:
                logger.warning("⚠️ Database schema may be incomplete - please run supabase_schema.sql")
                return True  # Still allow startup, schema can be fixed
        else:
            logger.error("❌ Supabase database connection failed - invalid response")
            return False
            
    except Exception as e:
        logger.error(f"❌ Supabase database connection failed: {e}")
        return False

def test_data_orchestrator():
    """Test data orchestrator initialization"""
    logger.info("🔍 Testing data orchestrator initialization...")
    
    try:
        from data_orchestrator import DataExtractionOrchestrator
        
        orchestrator = DataExtractionOrchestrator(
            api_key=os.getenv('ANTPOOL_API_KEY'),
            api_secret=os.getenv('ANTPOOL_API_SECRET'),
            user_id=os.getenv('ANTPOOL_USER_ID'),
            email=os.getenv('ANTPOOL_EMAIL'),
            supabase_connection=os.getenv('SUPABASE_CONNECTION_STRING')
        )
        
        logger.info("✅ Data orchestrator initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Data orchestrator initialization failed: {e}")
        return False

def check_account_setup():
    """Check if main account exists in database"""
    logger.info("🔍 Checking account setup...")
    
    try:
        from supabase_manager import SupabaseManager
        
        db = SupabaseManager(os.getenv('SUPABASE_CONNECTION_STRING'))
        user_id = os.getenv('ANTPOOL_USER_ID')
        
        # Check if account exists
        result = db.execute_query(
            "SELECT id, account_name FROM accounts WHERE account_name = %s",
            (user_id,)
        )
        
        if result and len(result) > 0:
            logger.info(f"✅ Account found in database: {user_id}")
        else:
            logger.info(f"ℹ️ Account not found (will be created on first data collection): {user_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Account setup check failed: {e}")
        return False

def main():
    """Run all health checks"""
    logger.info("=" * 60)
    logger.info("🚀 Pow_CRM Health Check Starting")
    logger.info("=" * 60)
    
    start_time = datetime.now(timezone.utc)
    
    # Run all checks
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Antpool API Connection", test_antpool_connection),
        ("Supabase Database Connection", test_supabase_connection),
        ("Data Orchestrator", test_data_orchestrator),
        ("Account Setup", check_account_setup)
    ]
    
    passed_checks = 0
    total_checks = len(checks)
    
    for check_name, check_function in checks:
        logger.info(f"\n🔄 Running {check_name} check...")
        try:
            if check_function():
                passed_checks += 1
                logger.info(f"✅ {check_name} check passed")
            else:
                logger.error(f"❌ {check_name} check failed")
        except Exception as e:
            logger.error(f"💥 {check_name} check crashed: {e}")
    
    # Calculate execution time
    execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 Health Check Summary")
    logger.info("=" * 60)
    logger.info(f"Checks passed: {passed_checks}/{total_checks}")
    logger.info(f"Execution time: {execution_time:.2f} seconds")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    if passed_checks == total_checks:
        logger.info("🎉 All health checks passed! System is ready for data collection.")
        logger.info("📅 Cron jobs will begin collecting data according to schedule:")
        logger.info("   • Tier 1 (Dashboard): Every 10 minutes")
        logger.info("   • Tier 2 (Workers): Every hour")
        logger.info("   • Tier 3 (Financial): Daily at 2 AM")
        logger.info("   • Tier 4 (Cleanup): Daily at 3 AM")
        sys.exit(0)
    else:
        failed_checks = total_checks - passed_checks
        logger.error(f"💥 {failed_checks} health check(s) failed!")
        logger.error("🔧 Please fix the issues above before proceeding.")
        logger.error("📖 Check the README.md for troubleshooting guidance.")
        sys.exit(1)

if __name__ == "__main__":
    main()


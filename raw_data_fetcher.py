#!/usr/bin/env python3
"""
Raw Data Fetcher - Industry Standard API Response Collection
Fetches raw API responses and stores them as strings for later parsing
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load encrypted environment variables FIRST
from env_manager import EncryptedEnvManager
env_manager = EncryptedEnvManager()
env_manager.load_encrypted_env('.env.encrypted')

from antpool_client import AntpoolClient
from raw_data_manager import RawDataManager, RawApiResponse
from account_credentials import get_account_credentials, get_all_account_names

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RawDataFetcher:
    """Fetches and stores raw API responses"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize raw data fetcher"""
        self.raw_manager = RawDataManager(supabase_url, supabase_key)
        self.api_calls_made = 0
        self.api_call_limit = 580  # Leave buffer under 600 limit
        logger.info("Raw Data Fetcher initialized")
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within API rate limits"""
        if self.api_calls_made >= self.api_call_limit:
            logger.warning(f"API rate limit reached ({self.api_calls_made}/{self.api_call_limit})")
            return False
        return True
    
    def _get_account_id(self, account_name: str) -> int:
        """Get or create account ID (simplified for demo)"""
        # In production, this would use the actual account management system
        # For now, we'll use a simple hash-based ID
        return hash(account_name) % 1000000
    
    def fetch_worker_data_raw(self, account_name: str, coin: str = 'BTC') -> Optional[int]:
        """
        Fetch raw worker data for a single account
        
        Args:
            account_name: Name of the account
            coin: Coin type (default BTC)
            
        Returns:
            ID of stored raw response or None if failed
        """
        try:
            # Get credentials
            api_key, api_secret, user_id = get_account_credentials(account_name)
            client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
            account_id = self._get_account_id(account_name)
            
            logger.info(f"🔄 Fetching raw worker data for {account_name}...")
            
            # Record start time
            start_time = time.time()
            
            # Make API call and capture raw response
            all_workers = client.get_all_workers(user_id=user_id, coin=coin)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            self.api_calls_made += 1
            
            # Convert response to JSON string
            if all_workers is not None:
                raw_response_str = json.dumps(all_workers, default=str, ensure_ascii=False)
                response_size = len(raw_response_str.encode('utf-8'))
                worker_count = len(all_workers) if isinstance(all_workers, list) else 0
                
                logger.info(f"📊 {account_name}: Fetched {worker_count} workers, "
                           f"{response_size} bytes, {duration_ms}ms")
            else:
                # Store empty response for debugging
                raw_response_str = json.dumps(None)
                response_size = len(raw_response_str.encode('utf-8'))
                worker_count = 0
                
                logger.warning(f"⚠️ {account_name}: No data returned from API")
            
            # Create raw response object
            raw_response = RawApiResponse(
                account_id=account_id,
                account_name=account_name,
                api_endpoint='get_all_workers',
                request_params={'user_id': user_id, 'coin': coin},
                raw_response=raw_response_str,
                response_size=response_size,
                worker_count=worker_count,
                api_call_duration_ms=duration_ms
            )
            
            # Store raw response
            record_id = self.raw_manager.store_raw_response(raw_response)
            
            if record_id:
                logger.info(f"✅ {account_name}: Stored raw response (ID: {record_id})")
                return record_id
            else:
                logger.error(f"❌ {account_name}: Failed to store raw response")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch raw data for {account_name}: {e}")
            return None
    
    def fetch_all_accounts_raw(self, coin: str = 'BTC', max_accounts: int = None) -> Dict[str, Any]:
        """
        Fetch raw worker data for all accounts
        
        Args:
            coin: Coin type (default BTC)
            max_accounts: Maximum number of accounts to process (None for all)
            
        Returns:
            Summary of fetching results
        """
        results = {
            'success': True,
            'accounts_processed': 0,
            'accounts_successful': 0,
            'accounts_failed': 0,
            'total_workers_found': 0,
            'total_api_calls': 0,
            'total_data_size': 0,
            'raw_records_stored': [],
            'errors': []
        }
        
        try:
            logger.info("=== RAW DATA FETCHING STARTED ===")
            start_time = time.time()
            
            account_names = get_all_account_names()
            if max_accounts:
                account_names = account_names[:max_accounts]
            
            logger.info(f"Processing {len(account_names)} accounts for raw data collection...")
            
            for account_name in account_names:
                if not self._check_rate_limit():
                    logger.warning("Rate limit reached, stopping collection")
                    break
                
                try:
                    record_id = self.fetch_worker_data_raw(account_name, coin)
                    
                    if record_id:
                        results['accounts_successful'] += 1
                        results['raw_records_stored'].append({
                            'account_name': account_name,
                            'record_id': record_id
                        })
                        
                        # Get stored record details for summary
                        stored_record = self.raw_manager.get_raw_response_by_id(record_id)
                        if stored_record:
                            results['total_workers_found'] += stored_record.get('worker_count', 0)
                            results['total_data_size'] += stored_record.get('response_size', 0)
                    else:
                        results['accounts_failed'] += 1
                        results['errors'].append(f'{account_name}: Failed to store raw data')
                    
                    results['accounts_processed'] += 1
                    
                    # Brief pause between accounts
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name}: {e}")
                    results['accounts_failed'] += 1
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            results['total_api_calls'] = self.api_calls_made
            execution_time = time.time() - start_time
            
            logger.info("=== RAW DATA FETCHING COMPLETE ===")
            logger.info(f"📊 SUMMARY:")
            logger.info(f"   • Accounts processed: {results['accounts_processed']}")
            logger.info(f"   • Successful: {results['accounts_successful']}")
            logger.info(f"   • Failed: {results['accounts_failed']}")
            logger.info(f"   • Total workers found: {results['total_workers_found']}")
            logger.info(f"   • Total data size: {results['total_data_size']:,} bytes")
            logger.info(f"   • API calls made: {results['total_api_calls']}")
            logger.info(f"   • Execution time: {execution_time:.1f}s")
            
            if results['errors']:
                logger.warning(f"⚠️ {len(results['errors'])} errors occurred")
                for error in results['errors'][:5]:  # Show first 5 errors
                    logger.warning(f"   • {error}")
            
            # Update success status
            results['success'] = results['accounts_successful'] > 0
            
        except Exception as e:
            logger.error(f"Raw data fetching failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results
    
    def fetch_account_overview_raw(self, account_name: str, coin: str = 'BTC') -> Optional[int]:
        """
        Fetch raw account overview data
        
        Args:
            account_name: Name of the account
            coin: Coin type (default BTC)
            
        Returns:
            ID of stored raw response or None if failed
        """
        try:
            # Get credentials
            api_key, api_secret, user_id = get_account_credentials(account_name)
            client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
            account_id = self._get_account_id(account_name)
            
            logger.info(f"🔄 Fetching raw overview data for {account_name}...")
            
            # Record start time
            start_time = time.time()
            
            # Make API call
            overview_data = client.get_account_overview(user_id=user_id, coin=coin)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            self.api_calls_made += 1
            
            # Convert response to JSON string
            raw_response_str = json.dumps(overview_data, default=str, ensure_ascii=False)
            response_size = len(raw_response_str.encode('utf-8'))
            
            # Create raw response object
            raw_response = RawApiResponse(
                account_id=account_id,
                account_name=account_name,
                api_endpoint='get_account_overview',
                request_params={'user_id': user_id, 'coin': coin},
                raw_response=raw_response_str,
                response_size=response_size,
                worker_count=0,  # Overview doesn't contain worker count
                api_call_duration_ms=duration_ms
            )
            
            # Store raw response
            record_id = self.raw_manager.store_raw_response(raw_response)
            
            if record_id:
                logger.info(f"✅ {account_name}: Stored raw overview (ID: {record_id})")
                return record_id
            else:
                logger.error(f"❌ {account_name}: Failed to store raw overview")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch raw overview for {account_name}: {e}")
            return None

def main():
    """Main function for raw data fetching"""
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not all([supabase_url, supabase_key]):
        logger.error("❌ Missing Supabase credentials")
        return
    
    # Initialize fetcher
    fetcher = RawDataFetcher(supabase_url, supabase_key)
    
    # Fetch raw data for all accounts
    results = fetcher.fetch_all_accounts_raw(coin='BTC')
    
    if results['success']:
        logger.info("🎉 RAW DATA FETCHING SUCCESSFUL!")
        
        # Show processing stats
        stats = fetcher.raw_manager.get_processing_stats()
        logger.info(f"📈 PROCESSING STATS:")
        logger.info(f"   • Total raw responses: {stats['total_raw_responses']}")
        logger.info(f"   • Pending processing: {stats['pending_responses']}")
        logger.info(f"   • Total workers: {stats['total_workers']}")
    else:
        logger.error("❌ RAW DATA FETCHING FAILED")
        if results['errors']:
            logger.error("Errors:")
            for error in results['errors']:
                logger.error(f"   • {error}")

if __name__ == "__main__":
    main()


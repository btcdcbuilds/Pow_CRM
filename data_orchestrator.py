"""
Antpool Data Extraction Orchestrator - FIXED VERSION
Implements all 4 tiers with API rate limiting and performance optimizations
- Fixed data parsing to handle worker dictionaries correctly
- Batch database operations for better performance
- Reduced logging output (summary per pool instead of per worker)
- Removed non-existent properties like pages_fetched
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from antpool_client import AntpoolClient
from supabase_manager import SupabaseManager
from account_credentials import get_account_credentials, get_all_account_names

# Configure logging to reduce noise
logging.getLogger('httpx').setLevel(logging.WARNING)  # Reduce HTTP request logs
logging.getLogger('supabase').setLevel(logging.WARNING)  # Reduce Supabase logs

logger = logging.getLogger(__name__)

class DataExtractionOrchestrator:
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize the orchestrator with Supabase connection"""
        self.db = SupabaseManager(supabase_url, supabase_key)
        self.account_cache = {}  # Cache for account IDs
        self.api_calls_made = 0
        self.api_call_limit = 580  # Leave buffer under 600 limit
        logger.info("Data Extraction Orchestrator initialized")
    
    def _get_or_create_account(self, account_name: str, account_type: str = 'sub') -> int:
        """Get or create account in database and return account_id"""
        if account_name in self.account_cache:
            return self.account_cache[account_name]
        
        # Try to get existing account
        account_id = self.db.get_account_id(account_name)
        if account_id:
            pass  # Removed debug logging
        else:
            # Create new account
            account_id = self.db.upsert_account(account_name, account_type)
            logger.info(f"Created new account: {account_name}")
        
        self.account_cache[account_name] = account_id
        return account_id
    
    def _log_api_call(self, endpoint: str, account_id: Optional[int] = None, 
                     status: int = 200, response_time: int = 0, error: str = None):
        """Log API call for rate limiting"""
        try:
            self.db.log_api_call(endpoint, account_id, status, response_time, error)
            self.api_calls_made += 1
        except Exception as e:
            logger.warning(f"Failed to log API call: {e}")
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within API rate limits"""
        if self.api_calls_made >= self.api_call_limit:
            logger.warning(f"API rate limit reached ({self.api_calls_made}/{self.api_call_limit})")
            return False
        return True

    def collect_tier1_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 1: Essential Dashboard Data (Every 15 minutes)
        - Pool statistics and account balances
        - API Usage: ~10-15 calls
        - Focus: Critical operational data
        """
        results = {
            'success': True,
            'data_collected': [],
            'errors': [],
            'api_calls_made': 0,
            'sub_accounts_processed': 0,
            'offline_devices': []
        }
        
        try:
            logger.info("=== Tier 1 Collection Started ===")
            start_time = time.time()
            
            account_names = get_all_account_names()
            logger.info(f"Processing {len(account_names)} sub-accounts for Tier 1...")
            
            for account_name in account_names:
                if not self._check_rate_limit():
                    break
                    
                try:
                    api_key, api_secret, user_id = get_account_credentials(account_name)
                    client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
                    account_id = self._get_or_create_account(account_name, 'sub')
                    
                    # Get account balance
                    call_start = time.time()
                    balance_data = client.get_account_balance(user_id=user_id, coin=coin)
                    call_time = int((time.time() - call_start) * 1000)
                    
                    if balance_data and balance_data.get('code') == 0:
                        data = balance_data['data']
                        self.db.insert_account_balance(account_id, data, coin)
                        results['data_collected'].append(f'{account_name}_balance')
                        self._log_api_call('/api/account.htm', account_id, 200, call_time)
                        
                        # Check for offline workers
                        if data.get('totalWorkers', 0) > 0 and data.get('activeWorkers', 0) == 0:
                            results['offline_devices'].append({
                                'account_name': account_name,
                                'total_workers': data.get('totalWorkers', 0),
                                'active_workers': 0
                            })
                    else:
                        error_msg = balance_data.get('message', 'Unknown error') if balance_data else 'No response'
                        self._log_api_call('/api/account.htm', account_id, 400, call_time, error_msg)
                        results['errors'].append(f'{account_name}: Balance error - {error_msg}')
                    
                    results['api_calls_made'] += 1
                    results['sub_accounts_processed'] += 1
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name} in Tier 1: {e}")
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            execution_time = time.time() - start_time
            logger.info(f"=== Tier 1 Collection Complete ===")
            logger.info(f"Processed: {results['sub_accounts_processed']} accounts")
            logger.info(f"API calls: {results['api_calls_made']}")
            logger.info(f"Data collected: {len(results['data_collected'])} datasets")
            logger.info(f"Offline devices: {len(results['offline_devices'])}")
            logger.info(f"Execution time: {execution_time:.2f}s")
            
            if results['errors']:
                results['success'] = len(results['errors']) < len(account_names) * 0.5
            
        except Exception as e:
            logger.error(f"Tier 1 collection failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results

    def collect_tier2_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 2: Worker Data Collection (Every 30 minutes) - OPTIMIZED
        - Worker list and status for all accounts
        - API Usage: ~175 calls (pagination for large accounts)
        - Focus: Complete worker inventory with batch operations
        """
        results = {
            'success': True,
            'data_collected': [],
            'errors': [],
            'api_calls_made': 0,
            'sub_accounts_processed': 0,
            'total_workers_found': 0,
            'workers_stored': 0
        }
        
        try:
            logger.info("=== Tier 2 Collection Started ===")
            start_time = time.time()
            
            account_names = get_all_account_names()
            logger.info(f"Processing {len(account_names)} sub-accounts for Tier 2...")
            
            for account_name in account_names:
                if not self._check_rate_limit():
                    break
                    
                try:
                    api_key, api_secret, user_id = get_account_credentials(account_name)
                    client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
                    account_id = self._get_or_create_account(account_name, 'sub')
                    
                    # Get ALL workers for this account (with pagination)
                    logger.info(f"🔄 Collecting ALL workers for {account_name}...")
                    
                    call_start = time.time()
                    all_workers = client.get_all_workers(user_id=user_id, coin=coin)
                    call_time = int((time.time() - call_start) * 1000)
                    
                    if all_workers and isinstance(all_workers, list):
                        worker_count = len(all_workers)
                        results['total_workers_found'] += worker_count
                        
                        # Parse and batch insert workers
                        workers_data = []
                        active_workers = 0
                        inactive_workers = 0
                        invalid_workers = 0
                        
                        for worker in all_workers:
                            try:
                                # Ensure worker is a dictionary
                                if not isinstance(worker, dict):
                                    logger.warning(f"Worker data is not a dictionary for {account_name}: {type(worker)}")
                                    invalid_workers += 1
                                    continue
                                
                                # Parse worker data
                                worker_data = self._parse_worker_data(worker)
                                worker_data['account_id'] = account_id
                                workers_data.append(worker_data)
                                
                                # Count worker status
                                if worker_data['worker_status'] == 'online':
                                    active_workers += 1
                                elif worker_data['worker_status'] == 'offline':
                                    inactive_workers += 1
                                else:
                                    invalid_workers += 1
                                    
                            except Exception as e:
                                logger.warning(f"Failed to parse worker for {account_name}: {e}")
                                invalid_workers += 1
                        
                        # Batch insert workers (much faster than individual inserts)
                        if workers_data:
                            stored_count = self.db.batch_insert_workers(workers_data)
                            results['workers_stored'] += stored_count
                            
                            # Calculate pages fetched (estimate based on 50 workers per page)
                            pages_fetched = (worker_count + 49) // 50
                            logger.info(f"✅ {account_name}: {worker_count} workers ({active_workers} active) from {pages_fetched} pages")
                        
                        # Store account overview summary
                        overview_data = {
                            'total_workers': worker_count,
                            'active_workers': active_workers,
                            'inactive_workers': inactive_workers,
                            'invalid_workers': invalid_workers,
                            'user_id': user_id,
                            'worker_summary': f"Total: {worker_count}, Active: {active_workers}, Inactive: {inactive_workers}"
                        }
                        
                        self.db.insert_account_overview(account_id, coin, overview_data)
                        results['data_collected'].append(f'{account_name}_overview')
                        
                        # Log API calls made for this account (estimate based on pages)
                        api_calls_for_account = max(1, (worker_count + 49) // 50)
                        results['api_calls_made'] += api_calls_for_account
                        self._log_api_call('/api/userWorkerList.htm', account_id, 200, call_time)
                        
                    else:
                        logger.warning(f"No worker data returned for {account_name}")
                        results['errors'].append(f'{account_name}: No worker data returned')
                    
                    results['sub_accounts_processed'] += 1
                    
                    # Brief pause between accounts
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name} in Tier 2: {e}")
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            execution_time = time.time() - start_time
            logger.info("=== Tier 2 Collection Complete ===")
            
            if results['workers_stored'] > 0:
                logger.info("🎉 TIER 2 COLLECTION SUCCESSFUL!")
                logger.info("📊 SUMMARY:")
                logger.info(f"   • Accounts processed: {results['sub_accounts_processed']}")
                logger.info(f"   • Total workers found: {results['total_workers_found']}")
                logger.info(f"   • Workers stored: {results['workers_stored']}")
                logger.info(f"   • API calls made: {results['api_calls_made']}")
                logger.info(f"   • Execution time: {execution_time:.1f}s")
                
                if results['errors']:
                    logger.warning(f"⚠ Partial success with {len(results['errors'])} errors")
                else:
                    logger.info("✅ All accounts processed successfully!")
            else:
                logger.error("❌ TIER 2 COLLECTION FAILED - No workers stored")
                results['success'] = False
            
            if results['errors']:
                results['success'] = len(results['errors']) < len(account_names) * 0.5
            
        except Exception as e:
            logger.error(f"Tier 2 collection failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results
    
    def _parse_worker_data(self, worker: Dict[str, Any]) -> Dict[str, Any]:
        """Parse worker data from API response to database format"""
        def parse_hashrate(value):
            """Parse hashrate value like '123.45 TH/s' to integer"""
            if isinstance(value, str):
                # Remove 'TH/s' and convert to integer
                value_str = value.replace(' TH/s', '').replace('TH/s', '').strip()
                if value_str and value_str != '0':
                    try:
                        return int(float(value_str))
                    except (ValueError, TypeError):
                        return 0
            elif isinstance(value, (int, float)):
                return int(value)
            return 0
        
        def parse_reject_rate(value):
            """Parse reject rate like '0.01%' to float"""
            if isinstance(value, str):
                value_str = value.replace('%', '').strip()
                if value_str:
                    try:
                        return float(value_str)
                    except (ValueError, TypeError):
                        return 0.0
            elif isinstance(value, (int, float)):
                return float(value)
            return 0.0
        
        def parse_timestamp(value):
            """Parse timestamp to ISO format"""
            if isinstance(value, str) and value:
                try:
                    # Convert timestamp to ISO format
                    dt = datetime.fromtimestamp(int(value), tz=timezone.utc)
                    return dt.isoformat()
                except (ValueError, TypeError):
                    pass
            elif isinstance(value, (int, float)):
                try:
                    dt = datetime.fromtimestamp(value, tz=timezone.utc)
                    return dt.isoformat()
                except (ValueError, TypeError):
                    pass
            return None
        
        # Map API response to database fields with safe defaults
        return {
            'worker_name': worker.get('workerName', worker.get('worker_name', '')),
            'worker_status': 'online' if worker.get('workerStatus', worker.get('worker_status', 0)) == 1 else 'offline',
            'hashrate_1h': parse_hashrate(worker.get('hashrate1h', worker.get('hashrate_1h', '0'))),
            'hashrate_24h': parse_hashrate(worker.get('hashrate1d', worker.get('hashrate_24h', '0'))),
            'reject_rate': parse_reject_rate(worker.get('rejectRate', worker.get('reject_rate', '0%'))),
            'last_share_time': parse_timestamp(worker.get('lastShareTime', worker.get('last_share_time')))
        }

    def collect_tier3_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 3: Detailed Worker Data (Every 2 hours)
        - Worker list and performance for accounts with issues
        - API Usage: ~50-100 calls (selective based on Tier 1/2 findings)
        - Focus: Detailed worker analysis for problematic accounts
        """
        results = {
            'success': True,
            'data_collected': [],
            'errors': [],
            'api_calls_made': 0,
            'sub_accounts_processed': 0,
            'workers_analyzed': 0
        }
        
        try:
            logger.info("=== Tier 3 Collection Started ===")
            start_time = time.time()
            
            # Get accounts that need detailed analysis (offline workers, low hashrate, etc.)
            problem_accounts = self.db.get_problem_accounts()
            logger.info(f"Analyzing {len(problem_accounts)} problematic accounts for Tier 3...")
            
            for account_name in problem_accounts:
                if not self._check_rate_limit():
                    break
                    
                try:
                    api_key, api_secret, user_id = get_account_credentials(account_name)
                    client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
                    account_id = self._get_or_create_account(account_name, 'sub')
                    
                    # Get worker list with status
                    logger.debug(f"Collecting worker list for {account_name}...")
                    call_start = time.time()
                    worker_data = client.get_worker_list(user_id=user_id, coin_type=coin, 
                                                       worker_status=0, page_size=50)  # All workers
                    call_time = int((time.time() - call_start) * 1000)
                    
                    if worker_data and worker_data.get('code') == 0:
                        workers = worker_data['data']['result']['rows']
                        for worker in workers:
                            self.db.insert_worker_data(account_id, coin, worker, 'detailed')
                            results['workers_analyzed'] += 1
                        
                        results['data_collected'].append(f'{account_name}_workers')
                        self._log_api_call('/api/userWorkerList.htm', account_id, 200, call_time)
                        logger.info(f"Analyzed {len(workers)} workers for {account_name}")
                    else:
                        error_msg = worker_data.get('message', 'Unknown error') if worker_data else 'No response'
                        self._log_api_call('/api/userWorkerList.htm', account_id, 400, call_time, error_msg)
                        results['errors'].append(f'{account_name}: Worker data error - {error_msg}')
                    
                    results['api_calls_made'] += 1
                    results['sub_accounts_processed'] += 1
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name} in Tier 3: {e}")
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            execution_time = time.time() - start_time
            logger.info(f"=== Tier 3 Collection Complete ===")
            logger.info(f"Processed: {results['sub_accounts_processed']} accounts")
            logger.info(f"Workers analyzed: {results['workers_analyzed']}")
            logger.info(f"API calls: {results['api_calls_made']}")
            logger.info(f"Data collected: {len(results['data_collected'])} datasets")
            logger.info(f"Execution time: {execution_time:.2f}s")
            
            if results['errors']:
                results['success'] = len(results['errors']) < len(problem_accounts) * 0.5
            
        except Exception as e:
            logger.error(f"Tier 3 collection failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results

    def collect_tier4_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 4: Payment History & Database Cleanup (Daily)
        - Payment history for all accounts
        - Database maintenance and cleanup
        - API Usage: ~100-200 calls
        - Focus: Financial records and system maintenance
        """
        results = {
            'success': True,
            'data_collected': [],
            'errors': [],
            'api_calls_made': 0,
            'sub_accounts_processed': 0,
            'payments_collected': 0,
            'cleanup_results': {}
        }
        
        try:
            logger.info("=== Tier 4 Collection Started ===")
            start_time = time.time()
            
            account_names = get_all_account_names()
            logger.info(f"Processing payment history for {len(account_names)} sub-accounts...")
            
            for account_name in account_names:
                if not self._check_rate_limit():
                    break
                    
                try:
                    api_key, api_secret, user_id = get_account_credentials(account_name)
                    client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
                    account_id = self._get_or_create_account(account_name, 'sub')
                    
                    # Get payment history
                    logger.debug(f"Collecting payment history for {account_name}...")
                    call_start = time.time()
                    payment_data = client.get_payment_history(user_id=user_id, coin=coin, page_size=50)
                    call_time = int((time.time() - call_start) * 1000)
                    
                    if payment_data and payment_data.get('code') == 0:
                        payments = payment_data['data']['result']['rows']
                        for payment in payments:
                            self.db.insert_payment_history(account_id, coin, payment, 'daily')
                            results['payments_collected'] += 1
                        
                        results['data_collected'].append(f'{account_name}_payments')
                        self._log_api_call('/api/paymentHistory.htm', account_id, 200, call_time)
                        logger.info(f"Collected {len(payments)} payments for {account_name}")
                    else:
                        error_msg = payment_data.get('message', 'Unknown error') if payment_data else 'No response'
                        self._log_api_call('/api/paymentHistory.htm', account_id, 400, call_time, error_msg)
                        results['errors'].append(f'{account_name}: Payment history error - {error_msg}')
                    
                    results['api_calls_made'] += 1
                    results['sub_accounts_processed'] += 1
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name} in Tier 4: {e}")
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            # Perform database cleanup
            logger.info("Performing database cleanup...")
            
            # Get accounts with offline workers or low hashrate from recent data
            cleanup_results = {}
            
            # Cleanup old worker data
            deleted_workers = self.db.cleanup_old_worker_data()
            cleanup_results['deleted_workers'] = deleted_workers
            
            # Cleanup old API logs
            deleted_logs = self.db.cleanup_old_api_logs()
            cleanup_results['deleted_logs'] = deleted_logs
            
            # Cleanup old alerts
            deleted_alerts = self.db.cleanup_old_alerts()
            cleanup_results['deleted_alerts'] = deleted_alerts
            
            results['cleanup_results'] = cleanup_results
            
            execution_time = time.time() - start_time
            logger.info(f"=== Tier 4 Collection Complete ===")
            logger.info(f"Processed: {results['sub_accounts_processed']} accounts")
            logger.info(f"Payments collected: {results['payments_collected']}")
            logger.info(f"API calls: {results['api_calls_made']}")
            logger.info(f"Data collected: {len(results['data_collected'])} datasets")
            logger.info(f"Cleanup results: {cleanup_results}")
            logger.info(f"Execution time: {execution_time:.2f}s")
            
            if results['errors']:
                results['success'] = len(results['errors']) < len(account_names) * 0.5
            
        except Exception as e:
            logger.error(f"Tier 4 collection failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results


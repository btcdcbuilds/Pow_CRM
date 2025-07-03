"""
Antpool Data Extraction Orchestrator - COMPLETE VERSION
Implements all 4 tiers with API rate limiting (600 calls per 10 minutes)
Aligned with actual Antpool API capabilities
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from antpool_client import AntpoolClient
from supabase_manager import SupabaseManager
from account_credentials import get_account_credentials, get_all_account_names

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
            logger.debug(f"Found existing account: {account_name}")
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
        """Check if we're approaching API rate limit"""
        if self.api_calls_made >= self.api_call_limit:
            logger.warning(f"Approaching API rate limit ({self.api_calls_made}/{self.api_call_limit})")
            return False
        return True
    
    def collect_tier1_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 1: Essential Dashboard Data (Every 10 minutes)
        - Account balances and basic hashrates for all 33 accounts
        - API Usage: ~66 calls (33 balance + 33 hashrate)
        - Focus: Financial data and basic performance
        """
        results = {
            'success': True,
            'data_collected': [],
            'errors': [],
            'api_calls_made': 0,
            'offline_devices': [],
            'sub_accounts_processed': 0
        }
        
        try:
            logger.info("=== Tier 1 Collection Started ===")
            start_time = time.time()
            
            # Get all account names
            account_names = get_all_account_names()
            logger.info(f"Processing {len(account_names)} sub-accounts for Tier 1...")
            
            for account_name in account_names:
                if not self._check_rate_limit():
                    break
                    
                try:
                    # Get credentials for this specific account
                    api_key, api_secret, user_id = get_account_credentials(account_name)
                    
                    # Create client with this account's credentials
                    client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
                    
                    # Create/get account in database
                    account_id = self._get_or_create_account(account_name, 'sub')
                    
                    # 1. Get account balance (ESSENTIAL)
                    logger.debug(f"Collecting balance for {account_name}...")
                    call_start = time.time()
                    balance_data = client.get_account_balance(user_id=user_id, coin=coin)
                    call_time = int((time.time() - call_start) * 1000)
                    
                    if balance_data and balance_data.get('code') == 0:
                        self.db.insert_account_balance(account_id, balance_data['data'], coin)
                        results['data_collected'].append(f'{account_name}_balance')
                        self._log_api_call('/api/account.htm', account_id, 200, call_time)
                    else:
                        error_msg = balance_data.get('message', 'Unknown error') if balance_data else 'No response'
                        self._log_api_call('/api/account.htm', account_id, 400, call_time, error_msg)
                        results['errors'].append(f'{account_name}: Balance error - {error_msg}')
                    
                    results['api_calls_made'] += 1
                    
                    # 2. Get hashrate data (ESSENTIAL)
                    if self._check_rate_limit():
                        logger.debug(f"Collecting hashrate for {account_name}...")
                        call_start = time.time()
                        hashrate_data = client.get_hashrate(user_id=user_id, coin=coin)
                        call_time = int((time.time() - call_start) * 1000)
                        
                        if hashrate_data and hashrate_data.get('code') == 0:
                            self.db.insert_hashrate(account_id, coin, hashrate_data['data'])
                            results['data_collected'].append(f'{account_name}_hashrate')
                            self._log_api_call('/api/hashrate.htm', account_id, 200, call_time)
                            
                            # Check for offline workers
                            data = hashrate_data['data']
                            if data.get('activeWorkers', 0) == 0 and data.get('totalWorkers', 0) > 0:
                                results['offline_devices'].append({
                                    'account': account_name,
                                    'total_workers': data.get('totalWorkers', 0),
                                    'active_workers': 0
                                })
                        else:
                            error_msg = hashrate_data.get('message', 'Unknown error') if hashrate_data else 'No response'
                            self._log_api_call('/api/hashrate.htm', account_id, 400, call_time, error_msg)
                            results['errors'].append(f'{account_name}: Hashrate error - {error_msg}')
                        
                        results['api_calls_made'] += 1
                    
                    results['sub_accounts_processed'] += 1
                    
                    # Small delay to avoid overwhelming API
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name}: {e}")
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            execution_time = time.time() - start_time
            logger.info(f"=== Tier 1 Collection Complete ===")
            logger.info(f"Processed: {results['sub_accounts_processed']} accounts")
            logger.info(f"API calls: {results['api_calls_made']}")
            logger.info(f"Data collected: {len(results['data_collected'])} datasets")
            logger.info(f"Offline devices: {len(results['offline_devices'])}")
            logger.info(f"Execution time: {execution_time:.2f}s")
            
            if results['errors']:
                logger.warning(f"Errors encountered: {len(results['errors'])}")
                results['success'] = len(results['errors']) < len(account_names) * 0.5  # Success if <50% errors
            
        except Exception as e:
            logger.error(f"Tier 1 collection failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results
    
    def collect_tier2_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 2: Account Overview Data (Every 30 minutes)
        - Account overview for all accounts (worker counts, status summary)
        - API Usage: ~33 calls (1 per account)
        - Focus: Worker status and operational overview
        """
        results = {
            'success': True,
            'data_collected': [],
            'errors': [],
            'api_calls_made': 0,
            'sub_accounts_processed': 0
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
                    
                    # Get worker list (account overview replacement)
                    logger.debug(f"Collecting worker overview for {account_name}...")
                    call_start = time.time()
                    worker_data = client.get_worker_list(user_id=user_id, coin=coin, worker_status=0, page=1, page_size=50)
                    call_time = int((time.time() - call_start) * 1000)
                    
                    if worker_data and isinstance(worker_data, dict) and 'result' in worker_data:
                        # Worker list returns data directly without code/message fields
                        overview_data = {
                            'total_workers': worker_data.get('result', {}).get('totalRecord', 0),
                            'active_workers': len([w for w in worker_data.get('result', {}).get('rows', []) if w.get('hsLast10min', '0') != '0 TH/s']),
                            'coin_type': worker_data.get('coinType', coin),
                            'user_id': worker_data.get('userId', user_id),
                            'worker_summary': worker_data.get('result', {})
                        }
                        self.db.insert_account_overview(account_id, coin, overview_data)
                        results['data_collected'].append(f'{account_name}_overview')
                        self._log_api_call('/api/userWorkerList.htm', account_id, 200, call_time)
                        logger.info(f"✅ {account_name}: {overview_data['total_workers']} total workers, {overview_data['active_workers']} active")
                    else:
                        error_msg = 'No worker data returned or invalid format'
                        self._log_api_call('/api/userWorkerList.htm', account_id, 400, call_time, error_msg)
                        results['errors'].append(f'{account_name}: Worker overview error - {error_msg}')
                    
                    results['api_calls_made'] += 1
                    results['sub_accounts_processed'] += 1
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name} in Tier 2: {e}")
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            execution_time = time.time() - start_time
            logger.info(f"=== Tier 2 Collection Complete ===")
            logger.info(f"Processed: {results['sub_accounts_processed']} accounts")
            logger.info(f"API calls: {results['api_calls_made']}")
            logger.info(f"Data collected: {len(results['data_collected'])} datasets")
            logger.info(f"Execution time: {execution_time:.2f}s")
            
            if results['errors']:
                results['success'] = len(results['errors']) < len(account_names) * 0.5
            
        except Exception as e:
            logger.error(f"Tier 2 collection failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results
    
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
            problem_accounts = self._identify_problem_accounts()
            logger.info(f"Analyzing {len(problem_accounts)} accounts with potential issues...")
            
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
                        results['errors'].append(f'{account_name}: Worker list error - {error_msg}')
                    
                    results['api_calls_made'] += 1
                    results['sub_accounts_processed'] += 1
                    
                    time.sleep(0.2)  # Longer delay for detailed analysis
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name} in Tier 3: {e}")
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            execution_time = time.time() - start_time
            logger.info(f"=== Tier 3 Collection Complete ===")
            logger.info(f"Processed: {results['sub_accounts_processed']} accounts")
            logger.info(f"Workers analyzed: {results['workers_analyzed']}")
            logger.info(f"API calls: {results['api_calls_made']}")
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
        Tier 4: Payment History & Cleanup (Daily)
        - Payment history for all accounts
        - Data cleanup and maintenance
        - API Usage: ~100-200 calls (33 payment history + cleanup operations)
        - Focus: Financial records and database maintenance
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
            logger.info(f"Processing payment history for {len(account_names)} accounts...")
            
            # Collect payment history
            for account_name in account_names:
                if not self._check_rate_limit():
                    break
                    
                try:
                    api_key, api_secret, user_id = get_account_credentials(account_name)
                    client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
                    account_id = self._get_or_create_account(account_name, 'sub')
                    
                    # Get payout history
                    logger.debug(f"Collecting payout history for {account_name}...")
                    call_start = time.time()
                    payout_data = client.get_payment_history(coin=coin, payment_type='payout', page_size=20)
                    call_time = int((time.time() - call_start) * 1000)
                    
                    if payout_data and payout_data.get('code') == 0:
                        payouts = payout_data['data']['rows']
                        for payout in payouts:
                            self.db.insert_payment_history(account_id, coin, payout, 'payout')
                            results['payments_collected'] += 1
                        
                        results['data_collected'].append(f'{account_name}_payouts')
                        self._log_api_call('/api/paymentHistoryV2.htm', account_id, 200, call_time)
                    else:
                        error_msg = payout_data.get('message', 'Unknown error') if payout_data else 'No response'
                        self._log_api_call('/api/paymentHistoryV2.htm', account_id, 400, call_time, error_msg)
                        results['errors'].append(f'{account_name}: Payout history error - {error_msg}')
                    
                    results['api_calls_made'] += 1
                    
                    # Get earnings history (if API calls remaining)
                    if self._check_rate_limit():
                        call_start = time.time()
                        earnings_data = client.get_payment_history(coin=coin, payment_type='recv', page_size=10)
                        call_time = int((time.time() - call_start) * 1000)
                        
                        if earnings_data and earnings_data.get('code') == 0:
                            earnings = earnings_data['data']['rows']
                            for earning in earnings:
                                self.db.insert_payment_history(account_id, coin, earning, 'earnings')
                                results['payments_collected'] += 1
                            
                            results['data_collected'].append(f'{account_name}_earnings')
                            self._log_api_call('/api/paymentHistoryV2.htm', account_id, 200, call_time)
                        
                        results['api_calls_made'] += 1
                    
                    results['sub_accounts_processed'] += 1
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name} in Tier 4: {e}")
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            # Perform database cleanup
            logger.info("Performing database cleanup...")
            try:
                cleanup_results = self._perform_database_cleanup()
                results['cleanup_results'] = cleanup_results
                logger.info(f"Cleanup completed: {cleanup_results}")
            except Exception as e:
                logger.error(f"Database cleanup failed: {e}")
                results['errors'].append(f"Cleanup error: {str(e)}")
            
            execution_time = time.time() - start_time
            logger.info(f"=== Tier 4 Collection Complete ===")
            logger.info(f"Processed: {results['sub_accounts_processed']} accounts")
            logger.info(f"Payments collected: {results['payments_collected']}")
            logger.info(f"API calls: {results['api_calls_made']}")
            logger.info(f"Execution time: {execution_time:.2f}s")
            
            if results['errors']:
                results['success'] = len(results['errors']) < len(account_names) * 0.5
            
        except Exception as e:
            logger.error(f"Tier 4 collection failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results
    
    def _identify_problem_accounts(self) -> List[str]:
        """Identify accounts that need detailed analysis based on recent data"""
        try:
            # Get accounts with offline workers or low hashrate from recent data
            problem_accounts = self.db.get_problem_accounts()
            return problem_accounts[:15]  # Limit to 15 accounts to stay under API limit
        except Exception as e:
            logger.error(f"Failed to identify problem accounts: {e}")
            # Fallback: return first 10 accounts
            return get_all_account_names()[:10]
    
    def _perform_database_cleanup(self) -> Dict[str, int]:
        """Perform database cleanup operations"""
        cleanup_results = {}
        
        try:
            # Cleanup old worker data
            deleted_workers = self.db.cleanup_old_worker_data()
            cleanup_results['deleted_workers'] = deleted_workers
            
            # Cleanup old API logs
            deleted_logs = self.db.cleanup_old_api_logs()
            cleanup_results['deleted_api_logs'] = deleted_logs
            
            # Cleanup resolved alerts
            deleted_alerts = self.db.cleanup_old_alerts()
            cleanup_results['deleted_alerts'] = deleted_alerts
            
            logger.info(f"Database cleanup completed: {cleanup_results}")
            
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            cleanup_results['error'] = str(e)
        
        return cleanup_results


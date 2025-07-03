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
    
    def _parse_hashrate(self, hashrate_str: str) -> int:
        """Parse hashrate string like '116.34 TH/s' to integer value in H/s"""
        if not hashrate_str or hashrate_str == '0':
            return 0
        
        try:
            # Remove units and convert to float
            value_str = hashrate_str.replace(' TH/s', '').replace(' GH/s', '').replace(' MH/s', '').replace(' H/s', '')
            value = float(value_str)
            
            # Convert to H/s based on unit
            if 'TH/s' in hashrate_str:
                return int(value * 1_000_000_000_000)  # TH to H
            elif 'GH/s' in hashrate_str:
                return int(value * 1_000_000_000)      # GH to H
            elif 'MH/s' in hashrate_str:
                return int(value * 1_000_000)          # MH to H
            else:
                return int(value)                       # Already in H/s
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse hashrate: {hashrate_str}")
            return 0
    
    def _parse_percentage(self, percentage_str: str) -> float:
        """Parse percentage string like '0.03%' to float value"""
        if not percentage_str:
            return 0.0
        
        try:
            return float(percentage_str.replace('%', ''))
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse percentage: {percentage_str}")
            return 0.0
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None
        
        try:
            # Convert milliseconds to seconds
            timestamp_seconds = int(timestamp_str) / 1000
            return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp: {timestamp_str}")
            return None
    
    def _parse_and_store_workers(self, account_id: int, account_name: str, workers_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse worker data and store individual worker records"""
        workers = workers_data.get('workers', [])
        total_workers = len(workers)
        active_workers = 0
        inactive_workers = 0
        workers_stored = 0
        
        logger.info(f"Parsing {total_workers} workers for {account_name}...")
        
        for worker in workers:
            try:
                # Parse worker data
                hashrate_10m = self._parse_hashrate(worker.get('hsLast10min', '0'))
                hashrate_1h = self._parse_hashrate(worker.get('hsLast1h', '0'))
                hashrate_1d = self._parse_hashrate(worker.get('hsLast1d', '0'))
                reject_rate = self._parse_percentage(worker.get('rejectRatio', '0%'))
                last_share_time = self._parse_timestamp(worker.get('shareLastTime'))
                
                # Determine worker status
                worker_status = 'active' if hashrate_10m > 0 else 'inactive'
                if worker_status == 'active':
                    active_workers += 1
                else:
                    inactive_workers += 1
                
                # Prepare worker data for database
                worker_data = {
                    'account_id': account_id,
                    'worker_name': worker.get('workerId', 'unknown'),
                    'worker_status': worker_status,
                    'hashrate_1h': hashrate_1h,
                    'hashrate_24h': hashrate_1d,  # Map 1d to 24h field
                    'last_share_time': last_share_time,
                    'reject_rate': reject_rate,
                    'data_type': 'tier2_complete'
                }
                
                # Store worker in database
                self.db.insert_worker_data(account_id, 'BTC', worker_data, 'tier2_complete')
                workers_stored += 1
                
            except Exception as e:
                logger.error(f"Failed to parse worker {worker.get('workerId', 'unknown')} for {account_name}: {e}")
                continue
        
        # Calculate summary statistics
        summary = {
            'total_workers': total_workers,
            'active_workers': active_workers,
            'inactive_workers': inactive_workers,
            'invalid_workers': 0,  # Could calculate based on high reject rates
            'workers_stored': workers_stored,
            'api_calls_made': workers_data.get('api_calls_made', 0),
            'pages_fetched': (total_workers + 49) // 50  # Calculate pages based on worker count (50 per page)
        }
        
        logger.info(f"✅ Parsed workers for {account_name}: {active_workers} active, {inactive_workers} inactive, {workers_stored} stored")
        return summary
    
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
        Tier 2: Complete Worker Data Collection (Every 30 minutes)
        - Get ALL workers from ALL pages for each account
        - Parse and store individual worker records in workers table
        - Store summary counts in account_overview table
        - API Usage: Variable (depends on worker count - BlackDawn ~27 calls for 1344 workers)
        - Focus: Complete worker inventory and performance data
        """
        results = {
            'success': True,
            'data_collected': [],
            'errors': [],
            'api_calls_made': 0,
            'sub_accounts_processed': 0,
            'total_workers_found': 0,
            'total_workers_stored': 0
        }
        
        try:
            logger.info("=== Tier 2 Collection Started ===")
            start_time = time.time()
            
            account_names = get_all_account_names()
            logger.info(f"Processing {len(account_names)} sub-accounts for Tier 2...")
            
            for account_name in account_names:
                if not self._check_rate_limit():
                    logger.warning(f"Rate limit reached, stopping Tier 2 collection")
                    break
                    
                try:
                    api_key, api_secret, user_id = get_account_credentials(account_name)
                    client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
                    account_id = self._get_or_create_account(account_name, 'sub')
                    
                    # Get ALL workers from ALL pages
                    logger.info(f"🔄 Collecting ALL workers for {account_name}...")
                    call_start = time.time()
                    
                    all_workers_data = client.get_all_workers(user_id=user_id, coin=coin, worker_status=0)
                    call_time = int((time.time() - call_start) * 1000)
                    
                    if all_workers_data and all_workers_data.get('workers'):
                        # Parse and store all individual workers
                        worker_summary = self._parse_and_store_workers(account_id, account_name, all_workers_data)
                        
                        # Store account overview summary
                        overview_data = {
                            'total_workers': worker_summary['total_workers'],
                            'active_workers': worker_summary['active_workers'],
                            'inactive_workers': worker_summary['inactive_workers'],
                            'invalid_workers': worker_summary['invalid_workers'],
                            'user_id': user_id,
                            'worker_summary': {
                                'pages_fetched': worker_summary['pages_fetched'],
                                'api_calls_made': worker_summary['api_calls_made'],
                                'last_updated': datetime.now().isoformat(),
                                'data_source': 'complete_pagination'
                            }
                        }
                        
                        self.db.insert_account_overview(account_id, coin, overview_data)
                        
                        # Update results
                        results['data_collected'].append(f'{account_name}_complete_workers')
                        results['total_workers_found'] += worker_summary['total_workers']
                        results['total_workers_stored'] += worker_summary['workers_stored']
                        results['api_calls_made'] += worker_summary['api_calls_made']
                        
                        # Log API calls
                        for i in range(worker_summary['api_calls_made']):
                            self._log_api_call('/api/userWorkerList.htm', account_id, 200, call_time // worker_summary['api_calls_made'])
                        
                        logger.info(f"✅ {account_name}: {worker_summary['total_workers']} workers ({worker_summary['active_workers']} active) from {worker_summary['pages_fetched']} pages")
                        
                    else:
                        error_msg = 'No worker data returned from get_all_workers'
                        self._log_api_call('/api/userWorkerList.htm', account_id, 400, call_time, error_msg)
                        results['errors'].append(f'{account_name}: {error_msg}')
                        logger.warning(f"❌ {account_name}: {error_msg}")
                    
                    results['sub_accounts_processed'] += 1
                    
                    # Small delay between accounts
                    time.sleep(1.0)
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name} in Tier 2: {e}")
                    results['errors'].append(f'{account_name}: {str(e)}')
            
            execution_time = time.time() - start_time
            logger.info(f"=== Tier 2 Collection Complete ===")
            logger.info(f"Processed: {results['sub_accounts_processed']} accounts")
            logger.info(f"API calls: {results['api_calls_made']}")
            logger.info(f"Workers found: {results['total_workers_found']}")
            logger.info(f"Workers stored: {results['total_workers_stored']}")
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


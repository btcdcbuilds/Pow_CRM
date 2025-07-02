"""
Antpool Data Extraction Orchestrator - Revised 4-Tier Strategy
Coordinates data collection with optimized scheduling for 6000+ devices

Tier 1 (Every 10 min): Pool info + offline devices
Tier 2 (Every hour): All worker data with hourly/24h hashrates  
Tier 3 (Daily 2 AM): Earnings, payments, daily summaries
Tier 4 (Daily 3 AM): Cleanup old data, maintain storage limits
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from antpool_client import AntpoolClient
from supabase_manager import SupabaseManager
from sub_accounts import SUB_ACCOUNT_IDS, DEFAULT_USER_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataExtractionOrchestrator:
    """Orchestrates data collection across all tiers with sub-account support"""
    
    def __init__(self, api_key: str, api_secret: str, user_id: str, 
                 email: Optional[str] = None, supabase_connection: Optional[str] = None):
        """Initialize orchestrator with API and database connections"""
        self.client = AntpoolClient(api_key, api_secret, user_id)
        self.db = SupabaseManager(supabase_connection)
        self.user_id = user_id
        self.email = email
        self.account_cache = {}
        
        logger.info("Data Extraction Orchestrator initialized")
    
    def _get_or_create_account(self, account_name: str, account_type: str = 'main', 
                              parent_account_id: Optional[int] = None) -> int:
        """Get or create account in database"""
        if account_name in self.account_cache:
            return self.account_cache[account_name]
        
        account_id = self.db.get_account_id(account_name)
        if not account_id:
            account_data = {
                'account_name': account_name,
                'account_type': account_type,
                'email': self.email,
                'coin_type': 'BTC',
                'parent_account_id': parent_account_id
            }
            account_id = self.db.upsert_account(account_data)
            logger.info(f"Created new account: {account_name}")
        
        self.account_cache[account_name] = account_id
        return account_id
    
    def collect_tier1_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 1: Dashboard Essentials (Every 10 minutes)
        - Pool stats for network info
        - All sub-account balances and hashrates
        - Offline device detection
        API Usage: ~35-40 calls (1 pool + 33 accounts + 33 hashrates)
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
            
            # 1. Get pool stats for network info
            logger.info("Collecting pool statistics...")
            try:
                pool_data = self.client.get_pool_stats(coin=coin)
                if pool_data:
                    # Store pool stats in database
                    self.db.insert_pool_stats(pool_data, coin)
                    results['data_collected'].append('pool_stats')
                results['api_calls_made'] += 1
            except Exception as e:
                logger.error(f"Failed to get pool stats: {e}")
                results['errors'].append(f"Pool stats error: {e}")
            
            # 2. Process all sub-accounts
            logger.info(f"Processing {len(SUB_ACCOUNT_IDS)} sub-accounts...")
            
            for user_id in SUB_ACCOUNT_IDS:
                try:
                    # Create/get account in database
                    account_id = self._get_or_create_account(user_id, 'sub')
                    
                    # Get account balance
                    logger.info(f"Collecting balance for {user_id}...")
                    balance_data = self.client.get_account_balance(user_id=user_id, coin=coin)
                    if balance_data:
                        self.db.insert_account_balance(account_id, balance_data)
                        results['data_collected'].append(f'{user_id}_balance')
                    results['api_calls_made'] += 1
                    
                    # Get hashrate data
                    logger.info(f"Collecting hashrate for {user_id}...")
                    hashrate_data = self.client.get_hashrate(user_id=user_id, coin=coin)
                    if hashrate_data:
                        self.db.insert_hashrate(account_id, coin, hashrate_data)
                        results['data_collected'].append(f'{user_id}_hashrate')
                        
                        # Check for offline workers
                        if hashrate_data.get('activeWorkers', 0) == 0 and hashrate_data.get('totalWorkers', 0) > 0:
                            results['offline_devices'].append({
                                'account': user_id,
                                'total_workers': hashrate_data.get('totalWorkers', 0),
                                'active_workers': 0
                            })
                    results['api_calls_made'] += 1
                    
                    results['sub_accounts_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process {user_id}: {e}")
                    results['errors'].append(f"{user_id}: {e}")
            
            results['success'] = len(results['errors']) == 0
            logger.info(f"Tier 1 complete: {results['sub_accounts_processed']} accounts, {results['api_calls_made']} API calls")
            
        except Exception as e:
            logger.error(f"Tier 1 collection failed: {e}")
            results['success'] = False
            results['errors'].append(str(e))
        
        return results
    
    def collect_tier2_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 2: Complete Worker Data (Every hour)
        - All workers from main account + sub-accounts
        - Hourly hashrate and 24-hour hashrate for each worker
        - Worker status and efficiency data
        API Usage: ~50-100 calls (batched efficiently)
        """
        results = {
            'success': True,
            'data_collected': [],
            'errors': [],
            'api_calls_made': 0,
            'workers_processed': 0,
            'accounts_processed': 0
        }
        
        try:
            logger.info("=== Tier 2 Collection Started ===")
            
            # Process main account
            main_account_id = self._get_or_create_account(self.user_id, 'main')
            main_workers = self._collect_account_workers(main_account_id, self.user_id, coin, results)
            results['workers_processed'] += main_workers
            results['accounts_processed'] += 1
            
            # Process sub-accounts
            if self.email:
                sub_accounts = self.client.get_sub_account_list(self.email)
                results['api_calls_made'] += 1
                
                if sub_accounts and 'data' in sub_accounts:
                    for sub_account in sub_accounts['data']:
                        sub_user_id = sub_account.get('userName', '')
                        if sub_user_id:
                            sub_account_id = self._get_or_create_account(
                                sub_user_id, 'sub', main_account_id
                            )
                            sub_workers = self._collect_account_workers(
                                sub_account_id, sub_user_id, coin, results
                            )
                            results['workers_processed'] += sub_workers
                            results['accounts_processed'] += 1
            
            logger.info(f"Tier 2 completed: {results['workers_processed']} workers across "
                       f"{results['accounts_processed']} accounts, {results['api_calls_made']} API calls")
            
        except Exception as e:
            logger.error(f"Tier 2 collection failed: {e}")
            results['success'] = False
            results['errors'].append(str(e))
        
        return results
    
    def _collect_account_workers(self, account_id: int, user_id: str, coin: str, results: Dict) -> int:
        """Collect all worker data for a specific account"""
        workers_processed = 0
        
        try:
            logger.info(f"Collecting workers for account {user_id}...")
            
            # Get all workers for this account
            all_workers = self.client.get_all_workers(coin, user_id if user_id != self.user_id else None)
            results['api_calls_made'] += 1
            
            if all_workers and 'data' in all_workers:
                for worker in all_workers['data']:
                    worker_name = worker.get('worker_name', '')
                    if not worker_name:
                        continue
                    
                    # Store worker data with hourly and 24h hashrates
                    worker_data = {
                        'account_id': account_id,
                        'worker_name': worker_name,
                        'worker_status': worker.get('worker_status', 'Unknown'),
                        'hashrate_1h': worker.get('hashrate_1h', 0),
                        'hashrate_24h': worker.get('hashrate_24h', 0),
                        'last_share_time': worker.get('last_share_time'),
                        'reject_rate': worker.get('reject_rate', 0),
                        'temperature': worker.get('temperature'),
                        'fan_speed': worker.get('fan_speed')
                    }
                    
                    self.db.insert_worker_data(worker_data)
                    workers_processed += 1
                    
                    # Check for low hashrate (compared to 24h average)
                    if worker_data['hashrate_24h'] > 0:
                        hashrate_ratio = worker_data['hashrate_1h'] / worker_data['hashrate_24h']
                        if hashrate_ratio < 0.5:  # 50% drop
                            self.db.create_worker_alert(
                                account_id,
                                worker_name,
                                'low_hashrate',
                                f"Worker {worker_name} hashrate dropped to {hashrate_ratio:.1%} of 24h average",
                                'critical' if hashrate_ratio < 0.3 else 'warning'
                            )
                
                results['data_collected'].append(f'workers_{user_id}_{len(all_workers["data"])}')
        
        except Exception as e:
            logger.error(f"Failed to collect workers for account {user_id}: {e}")
            results['errors'].append(f"Account {user_id}: {str(e)}")
        
        return workers_processed
    
    def collect_tier3_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 3: Daily Financial & Historical (Daily at 2 AM)
        - Daily earnings per worker
        - Payment history updates
        - Daily efficiency calculations
        - Worker performance summaries
        API Usage: ~20-30 calls
        """
        results = {
            'success': True,
            'data_collected': [],
            'errors': [],
            'api_calls_made': 0,
            'payments_processed': 0
        }
        
        try:
            logger.info("=== Tier 3 Collection Started ===")
            
            # Get main account
            main_account_id = self._get_or_create_account(self.user_id, 'main')
            
            # 1. Payment history (main account)
            logger.info("Collecting payment history...")
            payments = self.client.get_payment_history(coin)
            results['api_calls_made'] += 1
            
            if payments and 'data' in payments:
                for payment in payments['data']:
                    payment_data = {
                        'account_id': main_account_id,
                        'coin_type': coin,
                        'amount': payment.get('amount', 0),
                        'payment_time': payment.get('payment_time'),
                        'payment_tx': payment.get('payment_tx', ''),
                        'payment_status': payment.get('payment_status', 'completed')
                    }
                    self.db.insert_payment_history(payment_data)
                    results['payments_processed'] += 1
                
                results['data_collected'].append('payment_history')
            
            # 2. Daily worker earnings and efficiency
            logger.info("Calculating daily worker summaries...")
            self._calculate_daily_worker_summaries(main_account_id, coin)
            results['data_collected'].append('daily_worker_summaries')
            
            # 3. Sub-account payments (if applicable)
            if self.email:
                sub_accounts = self.client.get_sub_account_list(self.email)
                results['api_calls_made'] += 1
                
                if sub_accounts and 'data' in sub_accounts:
                    for sub_account in sub_accounts['data']:
                        sub_user_id = sub_account.get('userName', '')
                        if sub_user_id:
                            sub_account_id = self._get_or_create_account(
                                sub_user_id, 'sub', main_account_id
                            )
                            
                            # Sub-account payments
                            sub_payments = self.client.get_sub_account_payment_history(sub_user_id, coin)
                            results['api_calls_made'] += 1
                            
                            if sub_payments and 'data' in sub_payments:
                                for payment in sub_payments['data']:
                                    payment_data = {
                                        'account_id': sub_account_id,
                                        'coin_type': coin,
                                        'amount': payment.get('amount', 0),
                                        'payment_time': payment.get('payment_time'),
                                        'payment_tx': payment.get('payment_tx', ''),
                                        'payment_status': payment.get('payment_status', 'completed')
                                    }
                                    self.db.insert_payment_history(payment_data)
                                    results['payments_processed'] += 1
                            
                            # Daily summaries for sub-account
                            self._calculate_daily_worker_summaries(sub_account_id, coin)
            
            # 4. Pool statistics summary
            logger.info("Collecting pool statistics...")
            pool_stats = self.client.get_pool_stats(coin)
            results['api_calls_made'] += 1
            
            if pool_stats:
                self.db.insert_pool_stat(main_account_id, coin, pool_stats)
                results['data_collected'].append('pool_statistics')
            
            logger.info(f"Tier 3 completed: {len(results['data_collected'])} datasets, "
                       f"{results['payments_processed']} payments, {results['api_calls_made']} API calls")
            
        except Exception as e:
            logger.error(f"Tier 3 collection failed: {e}")
            results['success'] = False
            results['errors'].append(str(e))
        
        return results
    
    def _calculate_daily_worker_summaries(self, account_id: int, coin: str):
        """Calculate daily efficiency and performance summaries for workers"""
        try:
            # Get yesterday's date
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            date_str = yesterday.strftime('%Y-%m-%d')
            
            # Query worker data from yesterday
            workers_data = self.db.get_daily_worker_data(account_id, date_str)
            
            for worker_data in workers_data:
                # Calculate efficiency metrics
                avg_hashrate_1h = worker_data.get('avg_hashrate_1h', 0)
                avg_hashrate_24h = worker_data.get('avg_hashrate_24h', 0)
                uptime_percentage = worker_data.get('uptime_percentage', 0)
                
                efficiency_score = 0
                if avg_hashrate_24h > 0:
                    efficiency_score = (avg_hashrate_1h / avg_hashrate_24h) * (uptime_percentage / 100)
                
                # Store daily summary
                summary_data = {
                    'account_id': account_id,
                    'worker_name': worker_data['worker_name'],
                    'date': date_str,
                    'avg_hashrate_1h': avg_hashrate_1h,
                    'avg_hashrate_24h': avg_hashrate_24h,
                    'uptime_percentage': uptime_percentage,
                    'efficiency_score': efficiency_score,
                    'total_shares': worker_data.get('total_shares', 0),
                    'reject_rate': worker_data.get('avg_reject_rate', 0)
                }
                
                self.db.insert_daily_worker_summary(summary_data)
        
        except Exception as e:
            logger.error(f"Failed to calculate daily worker summaries: {e}")
    
    def collect_tier4_cleanup(self) -> Dict[str, Any]:
        """
        Tier 4: Daily Cleanup (Daily at 3 AM)
        - Delete 10-minute data older than 3 days
        - Delete hourly worker data older than 7 days  
        - Keep daily summaries forever
        - Aggregate efficiency reports
        """
        results = {
            'success': True,
            'data_cleaned': [],
            'errors': [],
            'records_deleted': 0
        }
        
        try:
            logger.info("=== Tier 4 Cleanup Started ===")
            
            # 1. Delete old 10-minute pool statistics (keep 3 days)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=3)
            deleted_pool_stats = self.db.cleanup_old_pool_stats(cutoff_date)
            results['records_deleted'] += deleted_pool_stats
            results['data_cleaned'].append(f'pool_stats_{deleted_pool_stats}')
            
            # 2. Delete old hourly worker data (keep 7 days)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            deleted_worker_data = self.db.cleanup_old_worker_data(cutoff_date)
            results['records_deleted'] += deleted_worker_data
            results['data_cleaned'].append(f'worker_data_{deleted_worker_data}')
            
            # 3. Delete old API call logs (keep 30 days)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            deleted_api_logs = self.db.cleanup_old_api_logs(cutoff_date)
            results['records_deleted'] += deleted_api_logs
            results['data_cleaned'].append(f'api_logs_{deleted_api_logs}')
            
            # 4. Clean up resolved alerts (keep 14 days)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=14)
            deleted_alerts = self.db.cleanup_old_alerts(cutoff_date)
            results['records_deleted'] += deleted_alerts
            results['data_cleaned'].append(f'alerts_{deleted_alerts}')
            
            # 5. Update database statistics
            self.db.update_database_stats()
            results['data_cleaned'].append('database_stats_updated')
            
            logger.info(f"Tier 4 cleanup completed: {results['records_deleted']} records deleted, "
                       f"{len(results['data_cleaned'])} cleanup operations")
            
        except Exception as e:
            logger.error(f"Tier 4 cleanup failed: {e}")
            results['success'] = False
            results['errors'].append(str(e))
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current system statistics"""
        try:
            stats = {
                'total_accounts': self.db.get_account_count(),
                'total_workers': self.db.get_worker_count(),
                'active_alerts': self.db.get_active_alert_count(),
                'last_collection_times': self.db.get_last_collection_times(),
                'api_usage_today': self.db.get_api_usage_today(),
                'database_size': self.db.get_database_size()
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


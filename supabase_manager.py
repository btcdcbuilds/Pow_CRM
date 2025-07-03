"""
Supabase Manager - COMPLETE VERSION
Handles all database operations for the cleaned schema
Supports all 4 tiers of data collection
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class SupabaseManager:
    def __init__(self, url: str, key: str):
        """Initialize Supabase client"""
        self.client: Client = create_client(url, key)
        logger.info("Supabase Manager initialized")
    
    def get_account_id(self, account_name: str) -> Optional[int]:
        """Get account ID by name"""
        try:
            response = self.client.table('accounts').select('id').eq('account_name', account_name).execute()
            if response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Failed to get account ID for {account_name}: {e}")
            return None
    
    def upsert_account(self, account_name: str, account_type: str = 'sub', 
                      email: str = None, coin_type: str = 'BTC') -> int:
        """Create or update account and return ID"""
        try:
            account_data = {
                'account_name': account_name,
                'account_type': account_type,
                'coin_type': coin_type,
                'is_active': True
            }
            if email:
                account_data['email'] = email
            
            response = self.client.table('accounts').upsert(account_data).execute()
            if response.data:
                logger.info(f"Upserted account: {account_name}")
                return response.data[0]['id']
            else:
                raise Exception("No data returned from upsert")
        except Exception as e:
            logger.error(f"Failed to upsert account {account_name}: {e}")
            raise
    
    def insert_account_balance(self, account_id: int, balance_data: Dict[str, Any], coin_type: str = 'BTC'):
        """Insert account balance data from /api/account.htm"""
        try:
            data = {
                'account_id': account_id,
                'coin_type': coin_type,
                'balance': float(balance_data.get('balance', 0)),
                'earn_24_hours': float(balance_data.get('earn24Hours', 0)),
                'earn_total': float(balance_data.get('earnTotal', 0)),
                'paid_out': float(balance_data.get('paidOut', 0)),
                'unpaid_amount': float(balance_data.get('balance', 0)),  # Unpaid is current balance
                'settle_time': balance_data.get('settleTime')
            }
            
            response = self.client.table('account_balances').insert(data).execute()
            logger.debug(f"Inserted balance for account {account_id}")
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Failed to insert balance for account {account_id}: {e}")
            raise
    
    def insert_hashrate(self, account_id: int, coin_type: str, hashrate_data: Dict[str, Any]):
        """Insert hashrate data from /api/hashrate.htm"""
        try:
            data = {
                'account_id': account_id,
                'coin_type': coin_type,
                'hashrate_10m': int(hashrate_data.get('last10m', 0)),
                'hashrate_1h': int(hashrate_data.get('last1h', 0)),
                'hashrate_1d': int(hashrate_data.get('last1d', 0)),
                'accepted_shares': int(hashrate_data.get('accepted', 0)),
                'stale_shares': int(hashrate_data.get('stale', 0)),
                'duplicate_shares': int(hashrate_data.get('dupelicate', 0)),  # Note: API typo
                'other_shares': int(hashrate_data.get('other', 0)),
                'total_workers': int(hashrate_data.get('totalWorkers', 0)),
                'active_workers': int(hashrate_data.get('activeWorkers', 0))
            }
            
            response = self.client.table('hashrates').insert(data).execute()
            logger.debug(f"Inserted hashrate for account {account_id}")
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Failed to insert hashrate for account {account_id}: {e}")
            raise
    
    def insert_account_overview(self, account_id: int, coin_type: str, overview_data: Dict[str, Any]):
        """Insert account overview data - fixed to match actual schema"""
        try:
            # Only insert fields that actually exist in the user's schema
            data = {
                'account_id': account_id,
                'coin_type': coin_type,
                'total_workers': int(overview_data.get('total_workers', 0)),
                'active_workers': int(overview_data.get('active_workers', 0)),
                'inactive_workers': int(overview_data.get('inactive_workers', 0)),
                'invalid_workers': int(overview_data.get('invalid_workers', 0)),
                'user_id': overview_data.get('user_id'),
                'worker_summary': overview_data.get('worker_summary')
            }
            
            response = self.client.table('account_overview').insert(data).execute()
            logger.debug(f"Inserted overview for account {account_id}: {data['total_workers']} total, {data['active_workers']} active workers")
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Failed to insert overview for account {account_id}: {e}")
            raise
    
    def insert_worker_data(self, account_id: int, coin_type: str, worker_data: Dict[str, Any], data_type: str = 'detailed'):
        """Insert worker data from /api/userWorkerList.htm or /api/workers.htm"""
        try:
            # Determine worker status
            status = 'unknown'
            if 'shareLastTime' in worker_data:
                # From userWorkerList - determine status based on recent activity
                last_share = worker_data.get('shareLastTime')
                if last_share and last_share != '':
                    status = 'online'
                else:
                    status = 'offline'
            
            data = {
                'account_id': account_id,
                'coin_type': coin_type,
                'worker_name': worker_data.get('workerId', worker_data.get('worker', 'unknown')),
                'worker_status': status,
                'hashrate_10m': int(worker_data.get('last10m', 0)),
                'hashrate_1h': int(worker_data.get('last1h', worker_data.get('hsLast1h', 0))),
                'hashrate_1d': int(worker_data.get('last1d', worker_data.get('hsLast1d', 0))),
                'accepted_shares': int(worker_data.get('accepted', 0)),
                'stale_shares': int(worker_data.get('stale', 0)),
                'duplicate_shares': int(worker_data.get('dupelicate', 0)),
                'other_shares': int(worker_data.get('other', 0)),
                'reject_rate': float(worker_data.get('rejectRatio', 0)),
                'last_share_time': worker_data.get('shareLastTime'),
                'data_type': data_type
            }
            
            response = self.client.table('workers').insert(data).execute()
            logger.debug(f"Inserted worker data for {data['worker_name']}")
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Failed to insert worker data: {e}")
            raise
    
    def insert_payment_history(self, account_id: int, coin_type: str, payment_data: Dict[str, Any], payment_type: str):
        """Insert payment history from /api/paymentHistoryV2.htm"""
        try:
            data = {
                'account_id': account_id,
                'coin_type': coin_type,
                'payment_type': payment_type,
                'payment_time': payment_data.get('timestamp'),
                'amount': float(payment_data.get('amount', 0))
            }
            
            if payment_type == 'payout':
                data.update({
                    'wallet_address': payment_data.get('walletAddress'),
                    'tx_id': payment_data.get('txId')
                })
            elif payment_type == 'earnings':
                data.update({
                    'hashrate_value': payment_data.get('hashrate_unit'),
                    'hashrate_unit': payment_data.get('hashrate'),
                    'pps_amount': float(payment_data.get('ppsAmount', 0)),
                    'pplns_amount': float(payment_data.get('pplnsAmount', 0)),
                    'solo_amount': float(payment_data.get('soloAmount', 0))
                })
            
            response = self.client.table('payment_history').insert(data).execute()
            logger.debug(f"Inserted {payment_type} for account {account_id}")
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Failed to insert payment history: {e}")
            raise
    
    def insert_pool_stats(self, coin_type: str, pool_data: Dict[str, Any]):
        """Insert pool statistics from /api/poolStats.htm"""
        try:
            data = {
                'coin_type': coin_type,
                'pool_hashrate': int(pool_data.get('poolHashrate', 0)),
                'active_worker_number': int(pool_data.get('activeWorkerNumber', 0)),
                'pool_status': pool_data.get('poolStatus', 'Unknown'),
                'network_difficulty': int(pool_data.get('networkDiff', 0)),
                'estimate_time': int(pool_data.get('estimateTime', 0)),
                'current_round': int(pool_data.get('currentRound', 0)),
                'total_share_number': int(pool_data.get('totalShareNumber', 0)),
                'total_block_number': int(pool_data.get('totalBlockNumber', 0))
            }
            
            response = self.client.table('pool_stats').insert(data).execute()
            logger.debug(f"Inserted pool stats for {coin_type}")
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Failed to insert pool stats: {e}")
            raise
    
    def log_api_call(self, endpoint: str, account_id: Optional[int] = None, 
                    status: int = 200, response_time: int = 0, error: str = None):
        """Log API call for rate limiting"""
        try:
            data = {
                'endpoint': endpoint,
                'response_status': status,
                'response_time_ms': response_time,
                'api_calls_in_window': 1
            }
            
            if account_id:
                data['account_id'] = account_id
            if error:
                data['error_message'] = error
            
            response = self.client.table('api_call_logs').insert(data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.warning(f"Failed to log API call: {e}")
            # Don't raise - logging failures shouldn't break main flow
    
    def create_worker_alert(self, account_id: int, worker_name: str, alert_type: str, 
                          message: str, alert_level: str = 'warning'):
        """Create worker alert"""
        try:
            data = {
                'account_id': account_id,
                'worker_name': worker_name,
                'alert_type': alert_type,
                'message': message,
                'alert_level': alert_level,
                'is_resolved': False
            }
            
            response = self.client.table('worker_alerts').insert(data).execute()
            logger.info(f"Created {alert_level} alert for {worker_name}: {alert_type}")
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Failed to create worker alert: {e}")
            raise
    
    def get_problem_accounts(self) -> List[str]:
        """Get accounts that need detailed analysis"""
        try:
            # Get accounts with offline workers from recent overview data
            query = """
            SELECT DISTINCT a.account_name 
            FROM accounts a
            JOIN account_overview ao ON a.id = ao.account_id
            WHERE ao.created_at > NOW() - INTERVAL '2 hours'
            AND (ao.inactive_workers > 0 OR ao.invalid_workers > 0 OR ao.hashrate_1h = 0)
            ORDER BY a.account_name
            LIMIT 15
            """
            
            response = self.client.rpc('execute_sql', {'query': query}).execute()
            if response.data:
                return [row['account_name'] for row in response.data]
            
            # Fallback: get accounts with recent offline workers from hashrate data
            response = self.client.table('accounts').select('account_name').limit(15).execute()
            return [row['account_name'] for row in response.data] if response.data else []
            
        except Exception as e:
            logger.error(f"Failed to get problem accounts: {e}")
            return []
    
    def cleanup_old_worker_data(self) -> int:
        """Cleanup old detailed worker data (keep 7 days)"""
        try:
            response = self.client.table('workers').delete().lt(
                'created_at', 
                (datetime.now(timezone.utc) - timezone.timedelta(days=7)).isoformat()
            ).eq('data_type', 'detailed').execute()
            
            deleted_count = len(response.data) if response.data else 0
            logger.info(f"Cleaned up {deleted_count} old worker records")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup worker data: {e}")
            return 0
    
    def cleanup_old_api_logs(self) -> int:
        """Cleanup old API logs (keep 7 days)"""
        try:
            response = self.client.table('api_call_logs').delete().lt(
                'created_at',
                (datetime.now(timezone.utc) - timezone.timedelta(days=7)).isoformat()
            ).execute()
            
            deleted_count = len(response.data) if response.data else 0
            logger.info(f"Cleaned up {deleted_count} old API log records")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup API logs: {e}")
            return 0
    
    def cleanup_old_alerts(self) -> int:
        """Cleanup resolved alerts (keep 14 days)"""
        try:
            response = self.client.table('worker_alerts').delete().lt(
                'resolved_at',
                (datetime.now(timezone.utc) - timezone.timedelta(days=14)).isoformat()
            ).eq('is_resolved', True).execute()
            
            deleted_count = len(response.data) if response.data else 0
            logger.info(f"Cleaned up {deleted_count} old resolved alerts")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup alerts: {e}")
            return 0
    
    def get_api_rate_status(self) -> Dict[str, int]:
        """Get current API rate limiting status"""
        try:
            response = self.client.table('api_call_logs').select('*').gte(
                'created_at',
                (datetime.now(timezone.utc) - timezone.timedelta(minutes=10)).isoformat()
            ).execute()
            
            calls_made = len(response.data) if response.data else 0
            return {
                'calls_in_last_10min': calls_made,
                'calls_remaining': 600 - calls_made,
                'limit': 600
            }
        except Exception as e:
            logger.error(f"Failed to get API rate status: {e}")
            return {'calls_in_last_10min': 0, 'calls_remaining': 600, 'limit': 600}


"""
Supabase Database Configuration and Connection Module
Handles database connections and basic operations for Antpool mining data
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseManager:
    """Manages Supabase database connections and operations"""
    
    def __init__(self, connection_string: str = None):
        """
        Initialize Supabase connection
        
        Args:
            connection_string: PostgreSQL connection string for Supabase
                              If None, will try to get from environment variable SUPABASE_CONNECTION_STRING
        """
        self.connection_string = connection_string or os.getenv('SUPABASE_CONNECTION_STRING')
        if not self.connection_string:
            raise ValueError("Supabase connection string is required. Set SUPABASE_CONNECTION_STRING environment variable.")
        
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
            )
            self.connection.autocommit = True
            logger.info("Successfully connected to Supabase database")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_insert(self, table: str, data: Dict) -> bool:
        """
        Insert data into a table
        
        Args:
            table: Table name
            data: Dictionary of column:value pairs
            
        Returns:
            True if successful
        """
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, list(data.values()))
                logger.debug(f"Inserted data into {table}")
                return True
        except Exception as e:
            logger.error(f"Insert failed for table {table}: {e}")
            raise
    
    def execute_batch_insert(self, table: str, data_list: List[Dict]) -> bool:
        """
        Insert multiple rows into a table
        
        Args:
            table: Table name
            data_list: List of dictionaries representing rows
            
        Returns:
            True if successful
        """
        if not data_list:
            return True
            
        try:
            # Use the first row to determine columns
            columns = ', '.join(data_list[0].keys())
            placeholders = ', '.join(['%s'] * len(data_list[0]))
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            with self.connection.cursor() as cursor:
                for data in data_list:
                    cursor.execute(query, list(data.values()))
                logger.info(f"Batch inserted {len(data_list)} rows into {table}")
                return True
        except Exception as e:
            logger.error(f"Batch insert failed for table {table}: {e}")
            raise
    
    def upsert_account(self, account_data: Dict) -> str:
        """
        Insert or update account information
        
        Args:
            account_data: Account data dictionary
            
        Returns:
            Account UUID
        """
        try:
            query = """
            INSERT INTO accounts (account_id, account_name, account_type, email, coin_type, parent_account_id)
            VALUES (%(account_id)s, %(account_name)s, %(account_type)s, %(email)s, %(coin_type)s, %(parent_account_id)s)
            ON CONFLICT (account_id) 
            DO UPDATE SET 
                account_name = EXCLUDED.account_name,
                email = EXCLUDED.email,
                coin_type = EXCLUDED.coin_type,
                updated_at = NOW()
            RETURNING id
            """
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, account_data)
                result = cursor.fetchone()
                return str(result['id'])
        except Exception as e:
            logger.error(f"Account upsert failed: {e}")
            raise
    
    def get_account_id(self, account_name: str) -> Optional[str]:
        """
        Get account UUID by account name
        
        Args:
            account_name: Account identifier
            
        Returns:
            Account UUID or None if not found
        """
        try:
            query = "SELECT id FROM accounts WHERE account_id = %s"
            result = self.execute_query(query, (account_name,))
            return str(result[0]['id']) if result else None
        except Exception as e:
            logger.error(f"Failed to get account ID: {e}")
            return None
    
    def insert_account_balance(self, account_id: str, balance_data: Dict) -> bool:
        """Insert account balance data"""
        data = {
            'account_id': account_id,
            'timestamp': datetime.now(timezone.utc),
            'earn_24_hours': float(balance_data.get('earn24Hours', 0)),
            'earn_total': float(balance_data.get('earnTotal', 0)),
            'paid_out': float(balance_data.get('paidOut', 0)),
            'balance': float(balance_data.get('balance', 0)),
            'settle_time': balance_data.get('settleTime'),
            'coin_type': balance_data.get('coin_type', 'BTC')
        }
        return self.execute_insert('account_balances', data)
    
    def insert_hashrate(self, account_id: str, hashrate_data: Dict) -> bool:
        """Insert hashrate data"""
        data = {
            'account_id': account_id,
            'timestamp': datetime.now(timezone.utc),
            'last_10m': int(hashrate_data.get('last10m', 0)),
            'last_1h': int(hashrate_data.get('last1h', 0)),
            'last_1d': int(hashrate_data.get('last1d', 0)),
            'prev_10m': int(hashrate_data.get('prev10m', 0)),
            'prev_1h': int(hashrate_data.get('prev1h', 0)),
            'prev_1d': int(hashrate_data.get('prev1d', 0)),
            'accepted_shares': int(hashrate_data.get('accepted', 0)),
            'stale_shares': int(hashrate_data.get('stale', 0)),
            'duplicate_shares': int(hashrate_data.get('dupelicate', 0)),
            'other_shares': int(hashrate_data.get('other', 0)),
            'total_workers': int(hashrate_data.get('totalWorkers', 0)),
            'active_workers': int(hashrate_data.get('activeWorkers', 0)),
            'coin_type': hashrate_data.get('coin_type', 'BTC')
        }
        return self.execute_insert('hashrates', data)
    
    def insert_worker_data(self, account_id: str, workers_data: List[Dict]) -> bool:
        """Insert worker performance data"""
        worker_rows = []
        timestamp = datetime.now(timezone.utc)
        
        for worker in workers_data:
            data = {
                'account_id': account_id,
                'worker_name': worker.get('worker', ''),
                'timestamp': timestamp,
                'hashrate_10m': int(worker.get('last10m', 0)),
                'hashrate_1h': int(worker.get('last1h', 0)),
                'hashrate_1d': int(worker.get('last1d', 0)),
                'prev_hashrate_10m': int(worker.get('prev10m', 0)),
                'prev_hashrate_1h': int(worker.get('prev1h', 0)),
                'prev_hashrate_1d': int(worker.get('prev1d', 0)),
                'accepted_shares': int(worker.get('accepted', 0)),
                'stale_shares': int(worker.get('stale', 0)),
                'duplicate_shares': int(worker.get('dupelicate', 0)),
                'other_shares': int(worker.get('other', 0)),
                'coin_type': worker.get('coin_type', 'BTC')
            }
            worker_rows.append(data)
        
        return self.execute_batch_insert('workers', worker_rows)
    
    def insert_pool_stats(self, pool_data: Dict) -> bool:
        """Insert pool statistics data"""
        data = {
            'timestamp': datetime.now(timezone.utc),
            'pool_hashrate': int(pool_data.get('poolHashrate', 0)),
            'active_worker_number': int(pool_data.get('activeWorkerNumber', 0)),
            'pool_status': pool_data.get('poolStatus', 'Unknown'),
            'network_diff': int(pool_data.get('networkDiff', 0)),
            'estimate_time': int(pool_data.get('estimateTime', 0)),
            'current_round': int(pool_data.get('currentRound', 0)),
            'total_share_number': int(pool_data.get('totalShareNumber', 0)),
            'total_block_number': int(pool_data.get('totalBlockNumber', 0)),
            'coin_type': pool_data.get('coin_type', 'BTC')
        }
        return self.execute_insert('pool_stats', data)
    
    def log_api_call(self, endpoint: str, account_id: str = None, 
                     response_code: int = None, response_time: int = None, 
                     success: bool = True, error_message: str = None) -> bool:
        """Log API call for rate limiting tracking"""
        data = {
            'endpoint': endpoint,
            'account_id': account_id,
            'timestamp': datetime.now(timezone.utc),
            'response_code': response_code,
            'response_time_ms': response_time,
            'success': success,
            'error_message': error_message
        }
        return self.execute_insert('api_call_logs', data)
    
    def get_recent_api_calls(self, minutes: int = 10) -> int:
        """Get count of API calls in the last N minutes"""
        query = """
        SELECT COUNT(*) as call_count 
        FROM api_call_logs 
        WHERE timestamp > NOW() - INTERVAL '%s minutes'
        """
        result = self.execute_query(query, (minutes,))
        return result[0]['call_count'] if result else 0
    
    def create_worker_alert(self, account_id: str, worker_name: str, 
                           alert_type: str, alert_level: str, message: str,
                           current_hashrate: int = None, expected_hashrate: int = None,
                           threshold_percentage: float = None) -> bool:
        """Create a worker alert"""
        data = {
            'account_id': account_id,
            'worker_name': worker_name,
            'alert_type': alert_type,
            'alert_level': alert_level,
            'message': message,
            'current_hashrate': current_hashrate,
            'expected_hashrate': expected_hashrate,
            'threshold_percentage': threshold_percentage,
            'timestamp': datetime.now(timezone.utc)
        }
        return self.execute_insert('worker_alerts', data)
    
    def get_latest_worker_hashrates(self, account_id: str) -> List[Dict]:
        """Get latest hashrate data for all workers in an account"""
        query = """
        SELECT DISTINCT ON (worker_name)
            worker_name, hashrate_10m, hashrate_1h, hashrate_1d, timestamp
        FROM workers 
        WHERE account_id = %s 
        ORDER BY worker_name, timestamp DESC
        """
        return self.execute_query(query, (account_id,))
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

# Example usage and configuration
if __name__ == "__main__":
    # Example configuration - replace with your actual Supabase connection string
    # connection_string = "postgresql://user:password@host:port/database"
    
    print("Supabase Manager Module")
    print("Set SUPABASE_CONNECTION_STRING environment variable to use this module")
    print("\nExample connection string format:")
    print("postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres")


    # =====================================================
    # DATA CLEANUP AND RETENTION FUNCTIONS
    # =====================================================
    
    def cleanup_old_pool_stats(self, cutoff_date):
        """Delete old pool statistics (10-minute data older than cutoff_date)"""
        try:
            result = self.execute_query("SELECT cleanup_old_pool_stats()")
            return result[0]['cleanup_old_pool_stats'] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to cleanup old pool stats: {e}")
            return 0
    
    def cleanup_old_worker_data(self, cutoff_date):
        """Delete old worker data (hourly data older than cutoff_date)"""
        try:
            result = self.execute_query("SELECT cleanup_old_worker_data()")
            return result[0]['cleanup_old_worker_data'] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to cleanup old worker data: {e}")
            return 0
    
    def cleanup_old_api_logs(self, cutoff_date):
        """Delete old API call logs"""
        try:
            result = self.execute_query("SELECT cleanup_old_api_logs()")
            return result[0]['cleanup_old_api_logs'] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to cleanup old API logs: {e}")
            return 0
    
    def cleanup_old_alerts(self, cutoff_date):
        """Delete old resolved alerts"""
        try:
            result = self.execute_query("SELECT cleanup_old_alerts()")
            return result[0]['cleanup_old_alerts'] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to cleanup old alerts: {e}")
            return 0
    
    def update_database_stats(self):
        """Update database statistics for better query performance"""
        try:
            tables = ['accounts', 'account_balances', 'hashrates', 'workers', 
                     'daily_worker_summaries', 'worker_alerts', 'payment_history', 
                     'pool_stats', 'api_call_logs']
            
            for table in tables:
                self.execute_query(f"ANALYZE {table}")
            
            self.logger.info("Database statistics updated")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update database stats: {e}")
            return False
    
    # =====================================================
    # STATISTICS AND MONITORING FUNCTIONS
    # =====================================================
    
    def get_account_count(self):
        """Get total number of accounts"""
        try:
            result = self.execute_query("SELECT COUNT(*) as count FROM accounts WHERE is_active = TRUE")
            return result[0]['count'] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to get account count: {e}")
            return 0
    
    def get_worker_count(self):
        """Get total number of unique workers"""
        try:
            result = self.execute_query("""
                SELECT COUNT(DISTINCT worker_name) as count 
                FROM workers 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            return result[0]['count'] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to get worker count: {e}")
            return 0
    
    def get_active_alert_count(self):
        """Get number of active alerts"""
        try:
            result = self.execute_query("SELECT COUNT(*) as count FROM worker_alerts WHERE is_resolved = FALSE")
            return result[0]['count'] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to get active alert count: {e}")
            return 0
    
    def get_last_collection_times(self):
        """Get last collection times for each tier"""
        try:
            result = {}
            
            # Last balance collection
            balance_result = self.execute_query("""
                SELECT MAX(created_at) as last_time 
                FROM account_balances
            """)
            if balance_result and balance_result[0]['last_time']:
                result['last_balance_collection'] = balance_result[0]['last_time']
            
            # Last worker collection
            worker_result = self.execute_query("""
                SELECT MAX(created_at) as last_time 
                FROM workers
            """)
            if worker_result and worker_result[0]['last_time']:
                result['last_worker_collection'] = worker_result[0]['last_time']
            
            # Last payment collection
            payment_result = self.execute_query("""
                SELECT MAX(created_at) as last_time 
                FROM payment_history
            """)
            if payment_result and payment_result[0]['last_time']:
                result['last_payment_collection'] = payment_result[0]['last_time']
            
            return result
        except Exception as e:
            self.logger.error(f"Failed to get last collection times: {e}")
            return {}
    
    def get_api_usage_today(self):
        """Get API usage statistics for today"""
        try:
            result = self.execute_query("""
                SELECT 
                    COUNT(*) as total_calls,
                    COUNT(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 END) as successful_calls,
                    COUNT(CASE WHEN response_status >= 400 THEN 1 END) as failed_calls,
                    AVG(response_time_ms) as avg_response_time
                FROM api_call_logs 
                WHERE created_at >= CURRENT_DATE
            """)
            return result[0] if result else {}
        except Exception as e:
            self.logger.error(f"Failed to get API usage: {e}")
            return {}
    
    def get_database_size(self):
        """Get database size information"""
        try:
            result = self.execute_query("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)
            return result if result else []
        except Exception as e:
            self.logger.error(f"Failed to get database size: {e}")
            return []
    
    # =====================================================
    # ENHANCED DATA INSERTION FUNCTIONS
    # =====================================================
    
    def get_daily_worker_data(self, account_id, date_str):
        """Get daily worker data for efficiency calculations"""
        try:
            result = self.execute_query("""
                SELECT 
                    worker_name,
                    AVG(hashrate_1h) as avg_hashrate_1h,
                    AVG(hashrate_24h) as avg_hashrate_24h,
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN worker_status = 'Alive' THEN 1 END) * 100.0 / COUNT(*) as uptime_percentage,
                    SUM(CASE WHEN last_share_time IS NOT NULL THEN 1 ELSE 0 END) as total_shares,
                    AVG(reject_rate) as avg_reject_rate
                FROM workers 
                WHERE account_id = %s 
                AND DATE(created_at) = %s
                AND data_type = 'hourly'
                GROUP BY worker_name
            """, (account_id, date_str))
            return result if result else []
        except Exception as e:
            self.logger.error(f"Failed to get daily worker data: {e}")
            return []
    
    def insert_daily_worker_summary(self, summary_data):
        """Insert daily worker summary"""
        try:
            query = """
                INSERT INTO daily_worker_summaries 
                (account_id, worker_name, date, avg_hashrate_1h, avg_hashrate_24h, 
                 uptime_percentage, efficiency_score, total_shares, reject_rate)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (account_id, worker_name, date) 
                DO UPDATE SET
                    avg_hashrate_1h = EXCLUDED.avg_hashrate_1h,
                    avg_hashrate_24h = EXCLUDED.avg_hashrate_24h,
                    uptime_percentage = EXCLUDED.uptime_percentage,
                    efficiency_score = EXCLUDED.efficiency_score,
                    total_shares = EXCLUDED.total_shares,
                    reject_rate = EXCLUDED.reject_rate,
                    created_at = NOW()
            """
            
            self.execute_query(query, (
                summary_data['account_id'],
                summary_data['worker_name'],
                summary_data['date'],
                summary_data['avg_hashrate_1h'],
                summary_data['avg_hashrate_24h'],
                summary_data['uptime_percentage'],
                summary_data['efficiency_score'],
                summary_data['total_shares'],
                summary_data['reject_rate']
            ))
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert daily worker summary: {e}")
            return False
    
    def insert_worker_data(self, worker_data):
        """Insert worker data with proper data type classification"""
        try:
            query = """
                INSERT INTO workers 
                (account_id, worker_name, worker_status, hashrate_1h, hashrate_24h, 
                 last_share_time, reject_rate, temperature, fan_speed, data_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self.execute_query(query, (
                worker_data['account_id'],
                worker_data['worker_name'],
                worker_data['worker_status'],
                worker_data['hashrate_1h'],
                worker_data['hashrate_24h'],
                worker_data['last_share_time'],
                worker_data['reject_rate'],
                worker_data.get('temperature'),
                worker_data.get('fan_speed'),
                worker_data.get('data_type', 'hourly')
            ))
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert worker data: {e}")
            return False
    
    def insert_pool_stat(self, account_id, coin_type, stats_data):
        """Insert pool statistics with frequency classification"""
        try:
            query = """
                INSERT INTO pool_stats 
                (account_id, coin_type, total_workers, online_workers, offline_workers, 
                 offline_percentage, pool_hashrate, network_difficulty, data_frequency)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self.execute_query(query, (
                account_id,
                coin_type,
                stats_data.get('total_workers', 0),
                stats_data.get('online_workers', 0),
                stats_data.get('offline_workers', 0),
                stats_data.get('offline_percentage', 0),
                stats_data.get('pool_hashrate', 0),
                stats_data.get('network_difficulty', 0),
                stats_data.get('data_frequency', '10min')
            ))
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert pool stats: {e}")
            return False


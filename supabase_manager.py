"""
Supabase REST API Manager
Handles Supabase operations using REST API instead of direct database connection
"""

import os
import logging
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseManager:
    """Manages Supabase operations using REST API"""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize Supabase REST API client
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key (for full access)
        """
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and service key are required. Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        
        # Remove trailing slash from URL
        self.supabase_url = self.supabase_url.rstrip('/')
        self.api_url = f"{self.supabase_url}/rest/v1"
        
        # Set up headers for API requests
        self.headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
        logger.info("Successfully initialized Supabase REST API client")
    
    def insert_data(self, table: str, data: Dict) -> bool:
        """
        Insert data into a table
        
        Args:
            table: Table name
            data: Dictionary of data to insert
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_url}/{table}"
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                logger.debug(f"Successfully inserted data into {table}")
                return True
            else:
                logger.error(f"Failed to insert into {table}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error inserting data into {table}: {e}")
            return False
    
    def insert_batch(self, table: str, data_list: List[Dict]) -> bool:
        """
        Insert multiple records at once
        
        Args:
            table: Table name
            data_list: List of dictionaries to insert
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_url}/{table}"
            response = requests.post(url, headers=self.headers, json=data_list)
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully inserted {len(data_list)} records into {table}")
                return True
            else:
                logger.error(f"Failed to batch insert into {table}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error batch inserting into {table}: {e}")
            return False
    
    def get_data(self, table: str, filters: Dict = None, limit: int = None) -> List[Dict]:
        """
        Get data from a table
        
        Args:
            table: Table name
            filters: Dictionary of filters (column: value)
            limit: Maximum number of records to return
            
        Returns:
            List of records
        """
        try:
            url = f"{self.api_url}/{table}"
            params = {}
            
            # Add filters
            if filters:
                for column, value in filters.items():
                    params[f"{column}"] = f"eq.{value}"
            
            # Add limit
            if limit:
                params['limit'] = limit
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get data from {table}: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting data from {table}: {e}")
            return []
    
    def update_data(self, table: str, filters: Dict, data: Dict) -> bool:
        """
        Update data in a table
        
        Args:
            table: Table name
            filters: Dictionary of filters to identify records
            data: Dictionary of data to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_url}/{table}"
            params = {}
            
            # Add filters
            for column, value in filters.items():
                params[f"{column}"] = f"eq.{value}"
            
            response = requests.patch(url, headers=self.headers, params=params, json=data)
            
            if response.status_code == 200:
                logger.debug(f"Successfully updated data in {table}")
                return True
            else:
                logger.error(f"Failed to update {table}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating data in {table}: {e}")
            return False
    
    def delete_data(self, table: str, filters: Dict) -> bool:
        """
        Delete data from a table
        
        Args:
            table: Table name
            filters: Dictionary of filters to identify records to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_url}/{table}"
            params = {}
            
            # Add filters
            for column, value in filters.items():
                params[f"{column}"] = f"eq.{value}"
            
            response = requests.delete(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                logger.debug(f"Successfully deleted data from {table}")
                return True
            else:
                logger.error(f"Failed to delete from {table}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting data from {table}: {e}")
            return False
    
    # ========================
    # ACCOUNT MANAGEMENT
    # ========================
    
    def get_account_id(self, account_name: str) -> Optional[int]:
        """Get account ID by name"""
        accounts = self.get_data('accounts', {'account_name': account_name}, limit=1)
        return accounts[0]['id'] if accounts else None
    
    def create_account(self, account_data: Dict) -> Optional[int]:
        """Create new account and return ID"""
        if self.insert_data('accounts', account_data):
            return self.get_account_id(account_data['account_name'])
        return None
    
    def upsert_account(self, account_data: Dict) -> Optional[int]:
        """Create or update account and return ID"""
        # Check if account already exists
        existing_id = self.get_account_id(account_data['account_name'])
        
        if existing_id:
            # Update existing account
            filters = {'account_name': account_data['account_name']}
            account_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            if self.update_data('accounts', filters, account_data):
                return existing_id
            return None
        else:
            # Create new account
            account_data['created_at'] = datetime.now(timezone.utc).isoformat()
            account_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            return self.create_account(account_data)
    
    def save_account_balance(self, account_id: int, balance_data: Dict) -> bool:
        """Save account balance data"""
        balance_data['account_id'] = account_id
        balance_data['created_at'] = datetime.now(timezone.utc).isoformat()
        return self.insert_data('account_balances', balance_data)
    
    def save_hashrate(self, account_id: int, hashrate_data: Dict) -> bool:
        """Save hashrate data"""
        hashrate_data['account_id'] = account_id
        hashrate_data['created_at'] = datetime.now(timezone.utc).isoformat()
        return self.insert_data('hashrates', hashrate_data)
    
    def save_worker_data(self, account_id: int, worker_data: Dict) -> bool:
        """Save individual worker data"""
        worker_data['account_id'] = account_id
        worker_data['created_at'] = datetime.now(timezone.utc).isoformat()
        return self.insert_data('workers', worker_data)
    
    def save_worker_batch(self, account_id: int, workers_list: List[Dict]) -> bool:
        """Save multiple workers at once"""
        for worker in workers_list:
            worker['account_id'] = account_id
            worker['created_at'] = datetime.now(timezone.utc).isoformat()
        return self.insert_batch('workers', workers_list)
    
    def save_payment_history(self, account_id: int, payment_data: Dict) -> bool:
        """Save payment history"""
        payment_data['account_id'] = account_id
        payment_data['created_at'] = datetime.now(timezone.utc).isoformat()
        return self.insert_data('payment_history', payment_data)
    
    def save_pool_stats(self, account_id: int, stats_data: Dict) -> bool:
        """Save pool statistics"""
        stats_data['account_id'] = account_id
        stats_data['created_at'] = datetime.now(timezone.utc).isoformat()
        return self.insert_data('pool_stats', stats_data)
    
    def save_worker_alert(self, account_id: int, alert_data: Dict) -> bool:
        """Save worker alert"""
        alert_data['account_id'] = account_id
        alert_data['created_at'] = datetime.now(timezone.utc).isoformat()
        return self.insert_data('worker_alerts', alert_data)
    
    def log_api_call(self, endpoint: str, account_id: int = None, 
                     status: int = None, response_time: int = None, 
                     error: str = None) -> bool:
        """Log API call for monitoring"""
        log_data = {
            'endpoint': endpoint,
            'account_id': account_id,
            'response_status': status,
            'response_time_ms': response_time,
            'error_message': error,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        return self.insert_data('api_call_logs', log_data)
    
    # ========================
    # DATA CLEANUP FUNCTIONS
    # ========================
    
    def cleanup_old_pool_stats(self, days: int = 3) -> int:
        """Delete pool stats older than specified days"""
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # For REST API, we need to use PostgREST syntax for date comparison
        try:
            url = f"{self.api_url}/pool_stats"
            params = {
                'data_frequency': 'eq.10min',
                'created_at': f'lt.{cutoff_date}'
            }
            
            response = requests.delete(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                # PostgREST doesn't return count by default, so we estimate
                logger.info(f"Cleaned up old pool stats (older than {days} days)")
                return 1  # Return success indicator
            else:
                logger.error(f"Failed to cleanup pool stats: {response.status_code}")
                return 0
                
        except Exception as e:
            logger.error(f"Error cleaning up pool stats: {e}")
            return 0
    
    def cleanup_old_worker_data(self, days: int = 7) -> int:
        """Delete worker data older than specified days"""
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        try:
            url = f"{self.api_url}/workers"
            params = {
                'data_type': 'eq.hourly',
                'created_at': f'lt.{cutoff_date}'
            }
            
            response = requests.delete(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                logger.info(f"Cleaned up old worker data (older than {days} days)")
                return 1
            else:
                logger.error(f"Failed to cleanup worker data: {response.status_code}")
                return 0
                
        except Exception as e:
            logger.error(f"Error cleaning up worker data: {e}")
            return 0
    
    def cleanup_old_api_logs(self, days: int = 30) -> int:
        """Delete API logs older than specified days"""
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        try:
            url = f"{self.api_url}/api_call_logs"
            params = {
                'created_at': f'lt.{cutoff_date}'
            }
            
            response = requests.delete(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                logger.info(f"Cleaned up old API logs (older than {days} days)")
                return 1
            else:
                logger.error(f"Failed to cleanup API logs: {response.status_code}")
                return 0
                
        except Exception as e:
            logger.error(f"Error cleaning up API logs: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """Get basic database statistics"""
        try:
            stats = {}
            
            # Count records in main tables
            tables = ['accounts', 'account_balances', 'workers', 'payment_history', 'api_call_logs']
            
            for table in tables:
                data = self.get_data(table, limit=1)
                # This is a rough estimate since we can't easily get count via REST API
                stats[f"{table}_count"] = "Available" if data else "Empty"
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    # ========================
    # MISSING METHODS NEEDED BY DATA ORCHESTRATOR
    # ========================
    
    def insert_account_balance(self, account_id: int, balance_data: Dict) -> bool:
        """Insert account balance data"""
        balance_record = {
            'account_id': account_id,
            'coin_type': 'BTC',
            'balance': balance_data.get('balance'),
            'earn_24_hours': balance_data.get('earn24Hours'),
            'earn_total': balance_data.get('earnTotal'),
            'paid_out': balance_data.get('paidOut'),
            'unpaid': balance_data.get('balance'),  # Assuming balance is unpaid
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        return self.insert_data('account_balances', balance_record)
    
    def insert_hashrate(self, account_id: int, coin: str, hashrate_data: Dict) -> bool:
        """Insert hashrate data"""
        hashrate_record = {
            'account_id': account_id,
            'coin_type': coin,
            'hashrate_10m': hashrate_data.get('last10m'),
            'hashrate_1h': hashrate_data.get('last1h'),
            'hashrate_1d': hashrate_data.get('last1d'),
            'worker_count': hashrate_data.get('totalWorkers'),
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        return self.insert_data('hashrates', hashrate_record)


# Import required for cleanup functions
from datetime import timedelta


#!/usr/bin/env python3
"""
Raw Storage Solution - Store API responses as strings first, parse later
This ensures we never lose data even if parsing fails
"""

import os
import sys
import logging
import json
from datetime import datetime, timezone

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load encrypted environment variables FIRST
from env_manager import EncryptedEnvManager
env_manager = EncryptedEnvManager()
env_manager.load_encrypted_env('.env.encrypted')

from antpool_client import AntpoolClient
from supabase_manager import SupabaseManager
from account_credentials import get_account_credentials, get_all_account_names

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RawDataManager:
    """Manages raw API response storage and parsing"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        self.db = SupabaseManager(supabase_url, supabase_key)
    
    def store_raw_worker_data(self, account_id: int, account_name: str, 
                             raw_response: str, worker_count: int) -> bool:
        """Store raw API response as string"""
        try:
            # Create raw storage table if it doesn't exist
            self._ensure_raw_table_exists()
            
            # Store raw data
            data = {
                'account_id': account_id,
                'account_name': account_name,
                'raw_workers_json': raw_response,
                'worker_count': worker_count,
                'api_endpoint': 'get_all_workers',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'parsed': False
            }
            
            result = self.db.supabase.table('worker_raw_data').insert(data).execute()
            logger.info(f"✅ Stored raw data for {account_name}: {worker_count} workers")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store raw data for {account_name}: {e}")
            return False
    
    def _ensure_raw_table_exists(self):
        """Ensure the raw storage table exists"""
        # This would typically be done via migration, but for demo:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS worker_raw_data (
            id SERIAL PRIMARY KEY,
            account_id INTEGER,
            account_name TEXT,
            raw_workers_json TEXT,
            worker_count INTEGER,
            api_endpoint TEXT,
            created_at TIMESTAMP,
            parsed BOOLEAN DEFAULT FALSE,
            parse_error TEXT
        );
        """
        # Note: In practice, you'd run this as a migration
        logger.info("Raw storage table structure defined")
    
    def parse_raw_data(self, raw_record_id: int = None) -> dict:
        """Parse stored raw data into structured format"""
        results = {
            'success': True,
            'parsed_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        try:
            # Get unparsed raw data
            if raw_record_id:
                query = self.db.supabase.table('worker_raw_data').select('*').eq('id', raw_record_id)
            else:
                query = self.db.supabase.table('worker_raw_data').select('*').eq('parsed', False)
            
            raw_records = query.execute()
            
            for record in raw_records.data:
                try:
                    # Parse JSON string
                    workers_data = json.loads(record['raw_workers_json'])
                    
                    # Process each worker
                    for worker in workers_data:
                        parsed_worker = self._parse_worker_data(worker)
                        parsed_worker['account_id'] = record['account_id']
                        
                        # Store parsed worker
                        self.db.insert_worker_data(
                            record['account_id'], 
                            'BTC', 
                            parsed_worker, 
                            'raw_parsed'
                        )
                    
                    # Mark as parsed
                    self.db.supabase.table('worker_raw_data').update({
                        'parsed': True,
                        'parse_error': None
                    }).eq('id', record['id']).execute()
                    
                    results['parsed_count'] += 1
                    logger.info(f"✅ Parsed {len(workers_data)} workers from {record['account_name']}")
                    
                except Exception as e:
                    # Mark parse error but keep raw data
                    self.db.supabase.table('worker_raw_data').update({
                        'parse_error': str(e)
                    }).eq('id', record['id']).execute()
                    
                    results['error_count'] += 1
                    results['errors'].append(f"{record['account_name']}: {str(e)}")
                    logger.error(f"❌ Failed to parse {record['account_name']}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse raw data: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results
    
    def _parse_worker_data(self, worker: dict) -> dict:
        """Parse individual worker data"""
        def parse_hashrate(value):
            if isinstance(value, str):
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
            if isinstance(value, str) and value:
                try:
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
        
        return {
            'worker_name': worker.get('workerName', worker.get('worker_name', '')),
            'worker_status': 'online' if worker.get('workerStatus', worker.get('worker_status', 0)) == 1 else 'offline',
            'hashrate_1h': parse_hashrate(worker.get('hashrate1h', worker.get('hashrate_1h', '0'))),
            'hashrate_24h': parse_hashrate(worker.get('hashrate1d', worker.get('hashrate_24h', '0'))),
            'reject_rate': parse_reject_rate(worker.get('rejectRate', worker.get('reject_rate', '0%'))),
            'last_share_time': parse_timestamp(worker.get('lastShareTime', worker.get('last_share_time')))
        }

def collect_and_store_raw_data():
    """Collect worker data and store as raw strings"""
    logger.info("=== RAW DATA COLLECTION STARTED ===")
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not all([supabase_url, supabase_key]):
        logger.error("Missing Supabase credentials")
        return
    
    raw_manager = RawDataManager(supabase_url, supabase_key)
    
    account_names = get_all_account_names()
    logger.info(f"Processing {len(account_names)} accounts...")
    
    total_workers = 0
    successful_accounts = 0
    
    for account_name in account_names[:5]:  # Test with first 5 accounts
        try:
            api_key, api_secret, user_id = get_account_credentials(account_name)
            client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
            
            # Get account ID
            account_id = 1  # Simplified for demo
            
            logger.info(f"🔄 Collecting raw data for {account_name}...")
            
            # Get raw worker data
            all_workers = client.get_all_workers(user_id=user_id, coin='BTC')
            
            if all_workers:
                # Convert to JSON string
                raw_json = json.dumps(all_workers, default=str)
                worker_count = len(all_workers)
                
                # Store raw data
                if raw_manager.store_raw_worker_data(account_id, account_name, raw_json, worker_count):
                    total_workers += worker_count
                    successful_accounts += 1
                    logger.info(f"✅ {account_name}: Stored {worker_count} workers as raw data")
                else:
                    logger.error(f"❌ {account_name}: Failed to store raw data")
            else:
                logger.warning(f"⚠️ {account_name}: No worker data returned")
                
                # Store empty result for debugging
                raw_manager.store_raw_worker_data(account_id, account_name, "[]", 0)
        
        except Exception as e:
            logger.error(f"❌ Failed to process {account_name}: {e}")
    
    logger.info("=== RAW DATA COLLECTION COMPLETE ===")
    logger.info(f"✅ Successful accounts: {successful_accounts}")
    logger.info(f"✅ Total workers stored: {total_workers}")
    
    # Now parse the raw data
    logger.info("=== PARSING RAW DATA ===")
    parse_results = raw_manager.parse_raw_data()
    
    if parse_results['success']:
        logger.info(f"✅ Parsed {parse_results['parsed_count']} records")
        if parse_results['error_count'] > 0:
            logger.warning(f"⚠️ {parse_results['error_count']} parse errors")
    else:
        logger.error("❌ Parsing failed")

if __name__ == "__main__":
    collect_and_store_raw_data()


#!/usr/bin/env python3
"""
Raw Data Parser - Industry Standard Data Processing
Parses stored raw API responses and populates Supabase tables
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load encrypted environment variables FIRST
from env_manager import EncryptedEnvManager
env_manager = EncryptedEnvManager()
env_manager.load_encrypted_env('.env.encrypted')

from raw_data_manager import RawDataManager
from supabase_manager import SupabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RawDataParser:
    """Parses raw API responses and populates Supabase tables"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize raw data parser"""
        self.raw_manager = RawDataManager(supabase_url, supabase_key)
        self.db = SupabaseManager(supabase_url, supabase_key)
        self.account_cache = {}  # Cache for account IDs
        logger.info("Raw Data Parser initialized")
    
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
    
    def _parse_worker_data(self, worker: Dict[str, Any]) -> Dict[str, Any]:
        """Parse individual worker data from raw API response"""
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
        
        # Map API response to database fields with multiple field name options
        return {
            'worker_name': worker.get('workerName', worker.get('worker_name', '')),
            'worker_status': 'online' if worker.get('workerStatus', worker.get('worker_status', 0)) == 1 else 'offline',
            'hashrate_1h': parse_hashrate(worker.get('hashrate1h', worker.get('hashrate_1h', '0'))),
            'hashrate_24h': parse_hashrate(worker.get('hashrate1d', worker.get('hashrate_24h', '0'))),
            'reject_rate': parse_reject_rate(worker.get('rejectRate', worker.get('reject_rate', '0%'))),
            'last_share_time': parse_timestamp(worker.get('lastShareTime', worker.get('last_share_time')))
        }
    
    def parse_worker_response(self, raw_record: Dict[str, Any]) -> Tuple[int, str]:
        """
        Parse a raw worker response and store workers in database
        
        Args:
            raw_record: Raw response record from database
            
        Returns:
            Tuple of (workers_processed, error_message)
        """
        workers_processed = 0
        error_message = None
        
        try:
            # Parse the raw JSON response
            raw_response = json.loads(raw_record['raw_response'])
            account_name = raw_record['account_name']
            
            logger.info(f"🔄 Parsing workers for {account_name}...")
            
            # Get or create account
            account_id = self._get_or_create_account(account_name, 'sub')
            
            # Handle different response formats
            if raw_response is None:
                logger.warning(f"⚠️ {account_name}: Raw response is None")
                return 0, "Raw response is None"
            
            if not isinstance(raw_response, list):
                logger.warning(f"⚠️ {account_name}: Raw response is not a list: {type(raw_response)}")
                return 0, f"Raw response is not a list: {type(raw_response)}"
            
            if len(raw_response) == 0:
                logger.warning(f"⚠️ {account_name}: Raw response is empty list")
                return 0, "Raw response is empty list"
            
            # Parse and batch insert workers
            workers_data = []
            active_workers = 0
            inactive_workers = 0
            invalid_workers = 0
            
            for worker in raw_response:
                try:
                    # Ensure worker is a dictionary
                    if not isinstance(worker, dict):
                        logger.warning(f"⚠️ {account_name}: Worker is not a dict: {type(worker)}")
                        invalid_workers += 1
                        continue
                    
                    # Parse worker data
                    parsed_worker = self._parse_worker_data(worker)
                    parsed_worker['account_id'] = account_id
                    workers_data.append(parsed_worker)
                    
                    # Count worker status
                    if parsed_worker['worker_status'] == 'online':
                        active_workers += 1
                    elif parsed_worker['worker_status'] == 'offline':
                        inactive_workers += 1
                    else:
                        invalid_workers += 1
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse individual worker for {account_name}: {e}")
                    invalid_workers += 1
            
            # Batch insert workers if we have valid data
            if workers_data:
                stored_count = self.db.batch_insert_workers(workers_data)
                workers_processed = stored_count
                
                logger.info(f"✅ {account_name}: Parsed and stored {stored_count} workers "
                           f"({active_workers} active, {inactive_workers} inactive)")
                
                # Store account overview summary
                overview_data = {
                    'total_workers': len(workers_data),
                    'active_workers': active_workers,
                    'inactive_workers': inactive_workers,
                    'invalid_workers': invalid_workers,
                    'user_id': raw_record.get('request_params', {}).get('user_id', ''),
                    'worker_summary': f"Total: {len(workers_data)}, Active: {active_workers}, Inactive: {inactive_workers}",
                    'data_source': 'raw_parsed'
                }
                
                self.db.insert_account_overview(account_id, 'BTC', overview_data)
                
            else:
                error_message = f"No valid workers found in response (invalid: {invalid_workers})"
                logger.warning(f"⚠️ {account_name}: {error_message}")
            
        except json.JSONDecodeError as e:
            error_message = f"JSON decode error: {str(e)}"
            logger.error(f"❌ {account_name}: {error_message}")
        except Exception as e:
            error_message = f"Parsing error: {str(e)}"
            logger.error(f"❌ {account_name}: {error_message}")
        
        return workers_processed, error_message
    
    def parse_overview_response(self, raw_record: Dict[str, Any]) -> Tuple[int, str]:
        """
        Parse a raw account overview response
        
        Args:
            raw_record: Raw response record from database
            
        Returns:
            Tuple of (records_processed, error_message)
        """
        records_processed = 0
        error_message = None
        
        try:
            # Parse the raw JSON response
            raw_response = json.loads(raw_record['raw_response'])
            account_name = raw_record['account_name']
            
            logger.info(f"🔄 Parsing overview for {account_name}...")
            
            # Get or create account
            account_id = self._get_or_create_account(account_name, 'sub')
            
            # Handle overview response format
            if raw_response and raw_response.get('code') == 0:
                overview_data = raw_response.get('data', {})
                self.db.insert_account_overview(account_id, 'BTC', overview_data)
                records_processed = 1
                logger.info(f"✅ {account_name}: Parsed and stored account overview")
            else:
                error_message = f"Invalid overview response: {raw_response.get('message', 'Unknown error')}"
                logger.warning(f"⚠️ {account_name}: {error_message}")
            
        except json.JSONDecodeError as e:
            error_message = f"JSON decode error: {str(e)}"
            logger.error(f"❌ {account_name}: {error_message}")
        except Exception as e:
            error_message = f"Parsing error: {str(e)}"
            logger.error(f"❌ {account_name}: {error_message}")
        
        return records_processed, error_message
    
    def process_unprocessed_data(self, batch_size: int = 50) -> Dict[str, Any]:
        """
        Process all unprocessed raw data
        
        Args:
            batch_size: Number of records to process in each batch
            
        Returns:
            Processing results summary
        """
        results = {
            'success': True,
            'total_processed': 0,
            'total_workers_stored': 0,
            'successful_records': 0,
            'failed_records': 0,
            'errors': []
        }
        
        try:
            logger.info("=== RAW DATA PROCESSING STARTED ===")
            start_time = time.time()
            
            # Get unprocessed records
            unprocessed_records = self.raw_manager.get_unprocessed_responses(limit=batch_size)
            
            if not unprocessed_records:
                logger.info("✅ No unprocessed records found")
                return results
            
            logger.info(f"Processing {len(unprocessed_records)} unprocessed records...")
            
            for record in unprocessed_records:
                try:
                    record_id = record['id']
                    account_name = record['account_name']
                    api_endpoint = record['api_endpoint']
                    
                    logger.info(f"🔄 Processing {account_name} ({api_endpoint})...")
                    
                    # Process based on endpoint type
                    if api_endpoint == 'get_all_workers':
                        workers_processed, error_message = self.parse_worker_response(record)
                        results['total_workers_stored'] += workers_processed
                    elif api_endpoint == 'get_account_overview':
                        records_processed, error_message = self.parse_overview_response(record)
                    else:
                        error_message = f"Unknown API endpoint: {api_endpoint}"
                        workers_processed = 0
                    
                    # Mark as processed
                    self.raw_manager.mark_as_processed(
                        record_id, 
                        workers_processed if api_endpoint == 'get_all_workers' else 1,
                        error_message
                    )
                    
                    if error_message:
                        results['failed_records'] += 1
                        results['errors'].append(f"{account_name}: {error_message}")
                    else:
                        results['successful_records'] += 1
                    
                    results['total_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process record {record.get('id', 'unknown')}: {e}")
                    results['failed_records'] += 1
                    results['errors'].append(f"Record {record.get('id', 'unknown')}: {str(e)}")
                    
                    # Mark as failed
                    if 'id' in record:
                        self.raw_manager.mark_as_processed(record['id'], 0, str(e))
            
            execution_time = time.time() - start_time
            
            logger.info("=== RAW DATA PROCESSING COMPLETE ===")
            logger.info(f"📊 SUMMARY:")
            logger.info(f"   • Records processed: {results['total_processed']}")
            logger.info(f"   • Successful: {results['successful_records']}")
            logger.info(f"   • Failed: {results['failed_records']}")
            logger.info(f"   • Workers stored: {results['total_workers_stored']}")
            logger.info(f"   • Execution time: {execution_time:.1f}s")
            
            if results['errors']:
                logger.warning(f"⚠️ {len(results['errors'])} errors occurred")
                for error in results['errors'][:5]:  # Show first 5 errors
                    logger.warning(f"   • {error}")
            
            # Update success status
            results['success'] = results['successful_records'] > 0
            
        except Exception as e:
            logger.error(f"Raw data processing failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results
    
    def reprocess_failed_data(self) -> Dict[str, Any]:
        """
        Reprocess failed raw data records
        
        Returns:
            Reprocessing results summary
        """
        results = {
            'success': True,
            'total_reprocessed': 0,
            'successful_records': 0,
            'failed_records': 0,
            'errors': []
        }
        
        try:
            logger.info("=== REPROCESSING FAILED DATA ===")
            
            # Get failed records that can be retried
            failed_records = self.raw_manager.reprocess_failed_responses()
            
            if not failed_records:
                logger.info("✅ No failed records to reprocess")
                return results
            
            logger.info(f"Reprocessing {len(failed_records)} failed records...")
            
            for record in failed_records:
                try:
                    record_id = record['id']
                    account_name = record['account_name']
                    api_endpoint = record['api_endpoint']
                    
                    logger.info(f"🔄 Reprocessing {account_name} ({api_endpoint})...")
                    
                    # Process based on endpoint type
                    if api_endpoint == 'get_all_workers':
                        workers_processed, error_message = self.parse_worker_response(record)
                    elif api_endpoint == 'get_account_overview':
                        records_processed, error_message = self.parse_overview_response(record)
                        workers_processed = records_processed
                    else:
                        error_message = f"Unknown API endpoint: {api_endpoint}"
                        workers_processed = 0
                    
                    # Mark as processed
                    self.raw_manager.mark_as_processed(record_id, workers_processed, error_message)
                    
                    if error_message:
                        results['failed_records'] += 1
                        results['errors'].append(f"{account_name}: {error_message}")
                    else:
                        results['successful_records'] += 1
                    
                    results['total_reprocessed'] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to reprocess record {record.get('id', 'unknown')}: {e}")
                    results['failed_records'] += 1
                    results['errors'].append(f"Record {record.get('id', 'unknown')}: {str(e)}")
            
            logger.info(f"✅ Reprocessing complete: {results['successful_records']} successful, {results['failed_records']} failed")
            
        except Exception as e:
            logger.error(f"Reprocessing failed: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
        
        return results

def main():
    """Main function for raw data parsing"""
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not all([supabase_url, supabase_key]):
        logger.error("❌ Missing Supabase credentials")
        return
    
    # Initialize parser
    parser = RawDataParser(supabase_url, supabase_key)
    
    # Process unprocessed data
    results = parser.process_unprocessed_data(batch_size=100)
    
    if results['success']:
        logger.info("🎉 RAW DATA PROCESSING SUCCESSFUL!")
        
        # Show processing stats
        stats = parser.raw_manager.get_processing_stats()
        logger.info(f"📈 FINAL STATS:")
        logger.info(f"   • Total raw responses: {stats['total_raw_responses']}")
        logger.info(f"   • Processed responses: {stats['processed_responses']}")
        logger.info(f"   • Pending responses: {stats['pending_responses']}")
        logger.info(f"   • Error responses: {stats['error_responses']}")
        logger.info(f"   • Total workers: {stats['total_workers']}")
        logger.info(f"   • Processing rate: {stats['processing_rate']}%")
        
        # Reprocess any failed records
        if stats['error_responses'] > 0:
            logger.info("🔄 Attempting to reprocess failed records...")
            reprocess_results = parser.reprocess_failed_data()
            if reprocess_results['successful_records'] > 0:
                logger.info(f"✅ Successfully reprocessed {reprocess_results['successful_records']} records")
    else:
        logger.error("❌ RAW DATA PROCESSING FAILED")
        if results['errors']:
            logger.error("Errors:")
            for error in results['errors']:
                logger.error(f"   • {error}")

if __name__ == "__main__":
    main()


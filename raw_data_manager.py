"""
Raw Data Manager - Industry Standard API Response Storage
Stores raw API responses as strings for later parsing
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from supabase_manager import SupabaseManager

logger = logging.getLogger(__name__)

@dataclass
class RawApiResponse:
    """Data class for raw API response"""
    account_id: int
    account_name: str
    api_endpoint: str
    request_params: Dict[str, Any]
    raw_response: str
    response_size: int
    worker_count: int
    api_call_duration_ms: int

class RawDataManager:
    """Manages raw API response storage and retrieval"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize raw data manager"""
        self.db = SupabaseManager(supabase_url, supabase_key)
        logger.info("Raw Data Manager initialized")
    
    def store_raw_response(self, response_data: RawApiResponse) -> Optional[int]:
        """
        Store raw API response in database
        
        Args:
            response_data: Raw API response data
            
        Returns:
            ID of stored record or None if failed
        """
        try:
            # Prepare data for storage
            data = {
                'account_id': response_data.account_id,
                'account_name': response_data.account_name,
                'api_endpoint': response_data.api_endpoint,
                'request_params': response_data.request_params,
                'raw_response': response_data.raw_response,
                'response_size': response_data.response_size,
                'worker_count': response_data.worker_count,
                'api_call_duration_ms': response_data.api_call_duration_ms,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'processed': False
            }
            
            # Store in database
            result = self.db.supabase.table('raw_api_responses').insert(data).execute()
            
            if result.data:
                record_id = result.data[0]['id']
                logger.info(f"✅ Stored raw response for {response_data.account_name}: "
                           f"{response_data.worker_count} workers, {response_data.response_size} bytes")
                return record_id
            else:
                logger.error(f"❌ Failed to store raw response for {response_data.account_name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error storing raw response for {response_data.account_name}: {e}")
            return None
    
    def get_unprocessed_responses(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get unprocessed raw responses
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of unprocessed raw response records
        """
        try:
            result = self.db.supabase.table('raw_api_responses')\
                .select('*')\
                .eq('processed', False)\
                .is_('processing_error', 'null')\
                .order('created_at')\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"❌ Error getting unprocessed responses: {e}")
            return []
    
    def get_failed_responses(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get responses that failed processing
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of failed response records
        """
        try:
            result = self.db.supabase.table('raw_api_responses')\
                .select('*')\
                .not_.is_('processing_error', 'null')\
                .lt('retry_count', 3)\
                .order('created_at')\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"❌ Error getting failed responses: {e}")
            return []
    
    def mark_as_processed(self, record_id: int, records_processed: int = 0, 
                         error_message: str = None) -> bool:
        """
        Mark raw response as processed
        
        Args:
            record_id: ID of raw response record
            records_processed: Number of records successfully processed
            error_message: Error message if processing failed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                'processed': error_message is None,
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'processing_error': error_message
            }
            
            if error_message:
                # Increment retry count for failed processing
                current_record = self.db.supabase.table('raw_api_responses')\
                    .select('retry_count')\
                    .eq('id', record_id)\
                    .execute()
                
                if current_record.data:
                    retry_count = current_record.data[0].get('retry_count', 0) + 1
                    update_data['retry_count'] = retry_count
            
            result = self.db.supabase.table('raw_api_responses')\
                .update(update_data)\
                .eq('id', record_id)\
                .execute()
            
            # Log processing result
            self._log_processing_result(record_id, records_processed, error_message)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error marking record {record_id} as processed: {e}")
            return False
    
    def _log_processing_result(self, record_id: int, records_processed: int, 
                              error_message: str = None):
        """Log processing result"""
        try:
            log_data = {
                'raw_response_id': record_id,
                'processing_step': 'parse_workers',
                'status': 'completed' if error_message is None else 'failed',
                'records_processed': records_processed,
                'error_message': error_message,
                'processing_time_ms': 0,  # Could be enhanced to track actual time
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            self.db.supabase.table('raw_data_processing_log').insert(log_data).execute()
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to log processing result: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics
        
        Returns:
            Dictionary with processing statistics
        """
        try:
            # Get overall stats
            result = self.db.supabase.rpc('get_processing_stats').execute()
            
            if result.data and len(result.data) > 0:
                stats = result.data[0]
            else:
                stats = {
                    'total_raw_responses': 0,
                    'processed_responses': 0,
                    'pending_responses': 0,
                    'error_responses': 0,
                    'total_workers': 0,
                    'processing_rate': 0
                }
            
            # Get account breakdown
            account_stats = self.db.supabase.from_('raw_data_stats').select('*').execute()
            stats['account_breakdown'] = account_stats.data if account_stats.data else []
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting processing stats: {e}")
            return {
                'total_raw_responses': 0,
                'processed_responses': 0,
                'pending_responses': 0,
                'error_responses': 0,
                'total_workers': 0,
                'processing_rate': 0,
                'account_breakdown': []
            }
    
    def cleanup_old_raw_data(self, days_old: int = 30) -> int:
        """
        Clean up old processed raw data
        
        Args:
            days_old: Delete processed records older than this many days
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=days_old)
            
            result = self.db.supabase.table('raw_api_responses')\
                .delete()\
                .eq('processed', True)\
                .lt('created_at', cutoff_date.isoformat())\
                .execute()
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"🧹 Cleaned up {deleted_count} old raw data records")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old raw data: {e}")
            return 0
    
    def get_raw_response_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        Get specific raw response by ID
        
        Args:
            record_id: ID of the raw response record
            
        Returns:
            Raw response record or None if not found
        """
        try:
            result = self.db.supabase.table('raw_api_responses')\
                .select('*')\
                .eq('id', record_id)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"❌ Error getting raw response {record_id}: {e}")
            return None
    
    def reprocess_failed_responses(self) -> List[Dict[str, Any]]:
        """
        Get failed responses that can be retried
        
        Returns:
            List of failed responses ready for retry
        """
        try:
            result = self.db.supabase.table('raw_api_responses')\
                .select('*')\
                .eq('processed', False)\
                .not_.is_('processing_error', 'null')\
                .lt('retry_count', 3)\
                .order('created_at')\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"❌ Error getting failed responses for retry: {e}")
            return []


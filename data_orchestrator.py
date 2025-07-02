"""
Antpool Data Extraction Orchestrator
Coordinates data collection across multiple tiers with individual account credentials
"""

import logging
from typing import Dict, Any, List
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
        logger.info("Data Extraction Orchestrator initialized")
    
    def _get_or_create_account(self, account_name: str, account_type: str = 'sub') -> int:
        """Get or create account in database and return account_id"""
        if account_name in self.account_cache:
            return self.account_cache[account_name]
        
        # Try to get existing account
        account_id = self.db.get_account_id(account_name)
        if account_id:
            logger.info(f"Found existing account: {account_name}")
        else:
            # Create new account
            account_id = self.db.upsert_account(account_name, account_type)
            logger.info(f"Created new account: {account_name}")
        
        self.account_cache[account_name] = account_id
        return account_id
    
    def collect_tier1_data(self, coin: str = 'BTC') -> Dict[str, Any]:
        """
        Tier 1: Dashboard Essentials (Every 10 minutes)
        - All sub-account balances and hashrates using individual credentials
        - Simple and focused data collection
        API Usage: ~66 calls (33 accounts + 33 hashrates)
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
            
            # Get all account names
            account_names = get_all_account_names()
            logger.info(f"Processing {len(account_names)} sub-accounts...")
            
            for account_name in account_names:
                try:
                    # Get credentials for this specific account
                    api_key, api_secret, user_id = get_account_credentials(account_name)
                    
                    # Create client with this account's credentials
                    client = AntpoolClient(api_key=api_key, api_secret=api_secret, user_id=user_id)
                    
                    # Create/get account in database
                    account_id = self._get_or_create_account(account_name, 'sub')
                    
                    # Get account balance
                    logger.info(f"Collecting balance for {account_name}...")
                    balance_data = client.get_account_balance(user_id=user_id, coin=coin)
                    if balance_data:
                        self.db.insert_account_balance(account_id, balance_data)
                        results['data_collected'].append(f'{account_name}_balance')
                    results['api_calls_made'] += 1
                    
                    # Get hashrate data
                    logger.info(f"Collecting hashrate for {account_name}...")
                    hashrate_data = client.get_hashrate(user_id=user_id, coin=coin)
                    if hashrate_data:
                        self.db.insert_hashrate(account_id, coin, hashrate_data)
                        results['data_collected'].append(f'{account_name}_hashrate')
                        
                        # Check for offline workers
                        if hashrate_data.get('activeWorkers', 0) == 0 and hashrate_data.get('totalWorkers', 0) > 0:
                            results['offline_devices'].append({
                                'account': account_name,
                                'total_workers': hashrate_data.get('totalWorkers', 0),
                                'active_workers': 0
                            })
                    results['api_calls_made'] += 1
                    
                    results['sub_accounts_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process {account_name}: {e}")
                    results['errors'].append(f"{account_name}: {e}")
            
            results['success'] = len(results['errors']) == 0
            logger.info(f"Tier 1 complete: {results['sub_accounts_processed']} accounts, {results['api_calls_made']} API calls")
            
        except Exception as e:
            logger.error(f"Tier 1 collection failed: {e}")
            results['success'] = False
            results['errors'].append(str(e))
        
        return results


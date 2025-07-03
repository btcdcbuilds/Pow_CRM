"""
Antpool API Client
Implements all Antpool API endpoints with error handling and rate limiting
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import json
from antpool_auth import AntpoolAuth, AntpoolConfig

logger = logging.getLogger(__name__)

class AntpoolAPIError(Exception):
    """Custom exception for Antpool API errors"""
    pass

class AntpoolClient:
    """Main client for Antpool API operations"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, 
                 user_id: str = None, email: str = None):
        """
        Initialize Antpool API client
        
        Args:
            api_key: Antpool API key
            api_secret: Antpool API secret  
            user_id: Main account user ID
            email: Account email for sub-account operations
        """
        self.auth = AntpoolAuth(api_key, api_secret, user_id)
        self.email = email
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AntpoolDataExtractor/1.0',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        # Rate limiting tracking
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()
        
        logger.info("Antpool API client initialized")
    
    def _rate_limit_check(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        
        # Reset counter every 10 minutes
        if current_time - self.request_window_start > 600:  # 10 minutes
            self.request_count = 0
            self.request_window_start = current_time
        
        # Check if we're approaching the limit
        if self.request_count >= AntpoolConfig.MAX_REQUESTS_PER_10_MIN - 10:
            wait_time = 600 - (current_time - self.request_window_start)
            if wait_time > 0:
                logger.warning(f"Rate limit approaching, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
                self.request_count = 0
                self.request_window_start = time.time()
        
        # Ensure minimum 1 second between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _make_request(self, endpoint: str, params: Dict, retries: int = 3) -> Dict:
        """
        Make authenticated API request with error handling
        
        Args:
            endpoint: API endpoint name
            params: Request parameters
            retries: Number of retry attempts
            
        Returns:
            API response data
        """
        self._rate_limit_check()
        
        url = AntpoolConfig.get_endpoint_url(endpoint)
        
        for attempt in range(retries + 1):
            try:
                start_time = time.time()
                response = self.session.post(
                    url, 
                    data=params, 
                    timeout=AntpoolConfig.REQUEST_TIMEOUT
                )
                response_time = int((time.time() - start_time) * 1000)
                
                # Log the API call
                logger.debug(f"API call: {endpoint}, Status: {response.status_code}, Time: {response_time}ms")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('code') == 0:
                            return data.get('data', {})
                        else:
                            error_msg = data.get('message', 'Unknown API error')
                            raise AntpoolAPIError(f"API error: {error_msg}")
                    except json.JSONDecodeError:
                        raise AntpoolAPIError("Invalid JSON response")
                else:
                    raise AntpoolAPIError(f"HTTP error: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                if attempt < retries:
                    wait_time = AntpoolConfig.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise AntpoolAPIError(f"Request failed after {retries + 1} attempts: {e}")
    
    def get_pool_stats(self, coin: str = 'BTC') -> Dict:
        """
        Get pool statistics
        
        Args:
            coin: Coin type (BTC, LTC, ETH, ZEC)
            
        Returns:
            Pool statistics data
        """
        params = self.auth.get_auth_params(coin=coin)
        return self._make_request('pool_stats', params)
    
    def get_account_balance(self, user_id: str = None, coin: str = 'BTC') -> Dict:
        """
        Get account balance and earnings
        
        Args:
            user_id: User ID (defaults to main account)
            coin: Coin type
            
        Returns:
            Account balance data
        """
        params = self.auth.get_auth_params(user_id=user_id, coin=coin)
        return self._make_request('account', params)
    
    def get_hashrate(self, user_id: str = None, coin: str = 'BTC') -> Dict:
        """
        Get overall hashrate information
        
        Args:
            user_id: User ID (defaults to main account)
            coin: Coin type
            
        Returns:
            Hashrate data
        """
        params = self.auth.get_auth_params(user_id=user_id, coin=coin)
        return self._make_request('hashrate', params)
    
    def get_workers(self, user_id: str = None, coin: str = 'BTC', 
                   group_id: str = 'All', page: int = 1, page_size: int = 50) -> Dict:
        """
        Get workers' hashrate information
        
        Args:
            user_id: User ID
            coin: Coin type
            group_id: Group ID (default 'All')
            page: Page number
            page_size: Records per page
            
        Returns:
            Workers data
        """
        additional_params = {
            'groupId': group_id,
            'pageEnable': 1,
            'page': page,
            'pageSize': page_size
        }
        params = self.auth.get_auth_params(user_id=user_id, coin=coin, 
                                         additional_params=additional_params)
        return self._make_request('workers', params)
    
    def get_all_workers(self, user_id: str = None, coin: str = 'BTC') -> List[Dict]:
        """
        Get all workers by paginating through results
        
        Args:
            user_id: User ID
            coin: Coin type
            
        Returns:
            List of all workers
        """
        all_workers = []
        page = 1
        
        while True:
            result = self.get_workers(user_id=user_id, coin=coin, page=page, page_size=50)
            
            if 'rows' in result and result['rows']:
                all_workers.extend(result['rows'])
                
                # Check if we have more pages
                if page >= result.get('totalPage', 1):
                    break
                page += 1
            else:
                break
        
        logger.info(f"Retrieved {len(all_workers)} workers for user {user_id or 'main'}")
        return all_workers
    
    def get_payment_history(self, coin: str = 'BTC', payment_type: str = 'payout',
                           page: int = 1, page_size: int = 50) -> Dict:
        """
        Get payment history
        
        Args:
            coin: Coin type
            payment_type: 'payout' or 'recv' (earnings)
            page: Page number
            page_size: Records per page
            
        Returns:
            Payment history data
        """
        additional_params = {
            'pageEnable': 1,
            'type': payment_type,
            'page': page,
            'pageSize': page_size
        }
        params = self.auth.get_auth_params(coin=coin, additional_params=additional_params)
        return self._make_request('payment_history', params)
    
    def get_account_overview(self, user_id: str, coin: str = 'BTC') -> Dict:
        """
        Get account overview for sub-account
        
        Args:
            user_id: Sub-account user ID
            coin: Coin type
            
        Returns:
            Account overview data
        """
        params = self.auth.get_auth_params(user_id=user_id, coin=coin)
        return self._make_request('account_overview', params)
    
    def get_worker_list(self, user_id: str, coin: str = 'BTC', 
                       worker_status: int = 0, page: int = 1, page_size: int = 50) -> Dict:
        """
        Get detailed worker list
        
        Args:
            user_id: User ID
            coin: Coin type
            worker_status: 0=All, 1=online, 2=offline, 3=invalid
            page: Page number
            page_size: Records per page
            
        Returns:
            Worker list data
        """
        additional_params = {
            'workerStatus': worker_status,
            'page': page,
            'pageSize': page_size
        }
        params = self.auth.get_auth_params(user_id=user_id, coin=coin,
                                         additional_params=additional_params)
        return self._make_request('worker_list', params)
    
    def get_all_workers(self, user_id: str, coin: str = 'BTC', worker_status: int = 0) -> Dict:
        """
        Get ALL workers across all pages (handles pagination automatically)
        
        Args:
            user_id: User ID
            coin: Coin type
            worker_status: 0=All, 1=online, 2=offline, 3=invalid
            
        Returns:
            Complete worker data with all workers from all pages
        """
        all_workers = []
        page = 1
        total_pages = 1
        total_records = 0
        api_calls_made = 0
        
        logger.info(f"Starting to fetch ALL workers for {user_id}...")
        
        while page <= total_pages:
            try:
                logger.debug(f"Fetching page {page} for {user_id}")
                response = self.get_worker_list(user_id, coin, worker_status, page, 50)
                api_calls_made += 1
                
                # Check if response has the expected structure
                if not response or 'result' not in response:
                    logger.warning(f"No result data in response for {user_id} page {page}")
                    break
                
                result = response['result']
                if 'rows' not in result:
                    logger.warning(f"No rows in result for {user_id} page {page}")
                    break
                
                # Add workers from this page
                page_workers = result.get('rows', [])
                all_workers.extend(page_workers)
                
                # Update pagination info from first response
                if page == 1:
                    total_pages = result.get('totalPage', 1)
                    total_records = result.get('totalRecord', 0)
                    logger.info(f"Found {total_records} total workers across {total_pages} pages for {user_id}")
                
                logger.debug(f"Page {page}: Got {len(page_workers)} workers")
                page += 1
                
                # Small delay between pages to be respectful to API
                if page <= total_pages:
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error fetching page {page} for {user_id}: {e}")
                break
        
        result = {
            'workers': all_workers,
            'total_workers': len(all_workers),
            'total_pages_fetched': page - 1,
            'total_records_expected': total_records,
            'api_calls_made': api_calls_made,
            'user_id': user_id,
            'coin': coin
        }
        
        logger.info(f"✅ Completed fetching workers for {user_id}: {len(all_workers)}/{total_records} workers from {page-1}/{total_pages} pages")
        return result
    
    def get_hashrate_chart(self, user_id: str = None, worker_id: str = None,
                          coin: str = 'BTC', chart_type: int = 1, 
                          start_date: str = None) -> Dict:
        """
        Get hashrate chart data
        
        Args:
            user_id: User ID
            worker_id: Worker ID (optional)
            coin: Coin type
            chart_type: 1=minutes, 2=hourly, 3=daily
            start_date: Start date (yyyy-MM-dd HH:mm:ss)
            
        Returns:
            Hashrate chart data
        """
        additional_params = {
            'type': chart_type
        }
        if worker_id:
            additional_params['userWorkerId'] = worker_id
        if start_date:
            additional_params['date'] = start_date
            
        params = self.auth.get_auth_params(user_id=user_id, coin=coin,
                                         additional_params=additional_params)
        return self._make_request('hashrate_chart', params)
    
    def get_sub_accounts(self, coin: str = 'BTC') -> Dict:
        """
        Get list of sub-accounts
        
        Args:
            coin: Coin type
            
        Returns:
            Sub-account list data
        """
        additional_params = {}
        if self.email:
            additional_params['Email'] = self.email
            
        params = self.auth.get_auth_params(coin=coin, additional_params=additional_params)
        return self._make_request('sub_account', params)
    
    def get_account_overview_by_email(self, coin: str = 'BTC', 
                                    page: int = 1, page_size: int = 50) -> Dict:
        """
        Get account overview for all sub-accounts by email
        
        Args:
            coin: Coin type
            page: Page number
            page_size: Records per page
            
        Returns:
            Batch account overview data
        """
        if not self.email:
            raise ValueError("Email is required for this endpoint")
            
        additional_params = {
            'Email': self.email,
            'pageEnable': 1,
            'page': page,
            'pageSize': page_size
        }
        params = self.auth.get_auth_params(coin=coin, additional_params=additional_params)
        return self._make_request('account_overview_by_email', params)
    
    def get_all_sub_account_overviews(self, coin: str = 'BTC') -> List[Dict]:
        """
        Get all sub-account overviews by paginating through results
        
        Args:
            coin: Coin type
            
        Returns:
            List of all sub-account overviews
        """
        all_overviews = []
        page = 1
        
        while True:
            result = self.get_account_overview_by_email(coin=coin, page=page, page_size=50)
            
            if 'accountOverviewBeanList' in result and result['accountOverviewBeanList']:
                all_overviews.extend(result['accountOverviewBeanList'])
                
                # Check if we have more pages
                if page >= result.get('totalPage', 1):
                    break
                page += 1
            else:
                break
        
        logger.info(f"Retrieved {len(all_overviews)} sub-account overviews")
        return all_overviews
    
    def change_mining_coin(self, coin: str) -> Dict:
        """
        Change mining coin (BTC or BCH only)
        
        Args:
            coin: Target coin (BTC or BCH)
            
        Returns:
            Operation result
        """
        if coin not in ['BTC', 'BCH']:
            raise ValueError("Only BTC and BCH are supported for coin switching")
            
        params = self.auth.get_auth_params(coin=coin)
        return self._make_request('change_coin', params)
    
    def get_coin_calculator(self, coin: str = 'BTC', hash_input: int = 1000000000000,
                           network_diff: int = None, fee_percent: float = None) -> Dict:
        """
        Get mining calculator results
        
        Args:
            coin: Coin type
            hash_input: Input hashrate (1000000000000 = 1TH/s)
            network_diff: Network difficulty (optional)
            fee_percent: Pool fees (optional)
            
        Returns:
            Calculator results
        """
        additional_params = {
            'hashInput': hash_input
        }
        if network_diff:
            additional_params['networkDiff'] = network_diff
        if fee_percent:
            additional_params['feePercent'] = fee_percent
            
        params = self.auth.get_auth_params(coin=coin, additional_params=additional_params)
        return self._make_request('coin_calculator', params)
    
    def get_rate_limit_status(self) -> Dict:
        """
        Get current rate limiting status
        
        Returns:
            Rate limit information
        """
        current_time = time.time()
        window_elapsed = current_time - self.request_window_start
        
        return {
            'requests_made': self.request_count,
            'requests_remaining': max(0, AntpoolConfig.MAX_REQUESTS_PER_10_MIN - self.request_count),
            'window_elapsed_seconds': window_elapsed,
            'window_remaining_seconds': max(0, 600 - window_elapsed),
            'last_request_seconds_ago': current_time - self.last_request_time
        }

# Example usage
if __name__ == "__main__":
    print("Antpool API Client")
    print("Set environment variables: ANTPOOL_API_KEY, ANTPOOL_API_SECRET, ANTPOOL_USER_ID")
    
    try:
        client = AntpoolClient()
        print("Client initialized successfully!")
        
        # Test rate limit status
        status = client.get_rate_limit_status()
        print(f"Rate limit status: {status}")
        
    except Exception as e:
        print(f"Client initialization failed: {e}")


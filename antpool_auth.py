"""
Antpool API Authentication Module
Handles API key management and HMAC-SHA256 signature generation
"""

import hmac
import hashlib
import time
import logging
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)

class AntpoolAuth:
    """Handles Antpool API authentication"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, user_id: str = None):
        """
        Initialize authentication with API credentials
        
        Args:
            api_key: Antpool API key
            api_secret: Antpool API secret
            user_id: Main account user ID
        """
        self.api_key = api_key or os.getenv('ANTPOOL_ACCESS_KEY')
        self.api_secret = api_secret or os.getenv('ANTPOOL_SECRET_KEY')
        self.user_id = user_id or os.getenv('ANTPOOL_USER_ID')
        
        if not all([self.api_key, self.api_secret, self.user_id]):
            raise ValueError("API key, secret, and user ID are required. Set environment variables or pass as parameters.")
        
        logger.info(f"Initialized Antpool authentication for user: {self.user_id}")
    
    def generate_signature(self, user_id: str = None, nonce: str = None) -> Dict[str, str]:
        """
        Generate HMAC-SHA256 signature for API authentication
        
        Args:
            user_id: User ID (defaults to main user_id)
            nonce: Nonce value (defaults to current timestamp)
            
        Returns:
            Dictionary containing authentication parameters
        """
        user_id = user_id or self.user_id
        nonce = nonce or str(int(time.time() * 1000))
        
        # Create message: userid + api_key + nonce
        message = user_id + self.api_key + nonce
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        
        auth_params = {
            'key': self.api_key,
            'nonce': nonce,
            'signature': signature
        }
        
        logger.debug(f"Generated signature for user: {user_id}")
        return auth_params
    
    def get_auth_params(self, user_id: str = None, coin: str = 'BTC', 
                       additional_params: Dict = None) -> Dict[str, str]:
        """
        Get complete authentication parameters for API request
        
        Args:
            user_id: User ID for the request
            coin: Coin type (BTC, LTC, ETH, ZEC)
            additional_params: Additional parameters to include
            
        Returns:
            Complete parameter dictionary for API request
        """
        auth_params = self.generate_signature(user_id)
        auth_params['coin'] = coin
        
        if user_id and user_id != self.user_id:
            auth_params['userId'] = user_id
            auth_params['clientUserId'] = user_id
        
        if additional_params:
            auth_params.update(additional_params)
        
        return auth_params
    
    def verify_signature(self, user_id: str, nonce: str, signature: str) -> bool:
        """
        Verify a signature (for testing purposes)
        
        Args:
            user_id: User ID used in signature
            nonce: Nonce used in signature
            signature: Signature to verify
            
        Returns:
            True if signature is valid
        """
        expected_auth = self.generate_signature(user_id, nonce)
        return expected_auth['signature'] == signature

class AntpoolConfig:
    """Configuration management for Antpool API"""
    
    # API endpoints
    BASE_URL = "https://antpool.com/api"
    
    ENDPOINTS = {
        'pool_stats': '/poolStats.htm',
        'account': '/account.htm',
        'hashrate': '/hashrate.htm',
        'workers': '/workers.htm',
        'payment_history': '/paymentHistoryV2.htm',
        'change_coin': '/changeMiningCoin.htm',
        'account_overview': '/accountOverview.htm',
        'worker_list': '/userWorkerList.htm',
        'coin_calculator': '/coinCalculator.htm',
        'hashrate_chart': '/userHashrateChart.htm',
        'sub_account': '/subAccount.htm',
        'account_overview_by_email': '/accountOverviewListByEmail.htm'
    }
    
    # Supported coin types
    SUPPORTED_COINS = ['BTC', 'LTC', 'ETH', 'ZEC']
    
    # Rate limiting
    MAX_REQUESTS_PER_10_MIN = 600
    MAX_REQUESTS_PER_MINUTE = 60
    
    # Request timeouts
    REQUEST_TIMEOUT = 30
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    @classmethod
    def get_endpoint_url(cls, endpoint_name: str) -> str:
        """Get full URL for an endpoint"""
        if endpoint_name not in cls.ENDPOINTS:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")
        return cls.BASE_URL + cls.ENDPOINTS[endpoint_name]
    
    @classmethod
    def validate_coin_type(cls, coin: str) -> bool:
        """Validate coin type"""
        return coin.upper() in cls.SUPPORTED_COINS

# Example usage and testing
if __name__ == "__main__":
    # Example configuration - set these as environment variables
    print("Antpool Authentication Module")
    print("Required environment variables:")
    print("- ANTPOOL_API_KEY")
    print("- ANTPOOL_API_SECRET") 
    print("- ANTPOOL_USER_ID")
    print()
    
    # Test signature generation if credentials are available
    try:
        auth = AntpoolAuth()
        test_params = auth.get_auth_params()
        print("Authentication test successful!")
        print(f"Sample auth params: {list(test_params.keys())}")
    except ValueError as e:
        print(f"Authentication setup required: {e}")
    
    # Show available endpoints
    print(f"\nAvailable endpoints: {list(AntpoolConfig.ENDPOINTS.keys())}")
    print(f"Supported coins: {AntpoolConfig.SUPPORTED_COINS}")

